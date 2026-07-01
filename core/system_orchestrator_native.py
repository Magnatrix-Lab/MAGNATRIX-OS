#!/usr/bin/env python3
"""system_orchestrator_native.py -- MAGNATRIX-OS System Orchestrator

Central orchestrator: boot sequence, dependency resolution, module lifecycle
(start/stop/restart/recover), health monitoring loop. Pure stdlib.
"""
from __future__ import annotations
import importlib.util
import json
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class ModuleInstance:
    manifest_id: str; name: str; class_name: str; entry_point: str
    instance: Optional[Any] = None; status: str = "stopped"
    pid: Optional[int] = None; start_time: Optional[float] = None
    restart_count: int = 0; last_error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OrchestrationReport:
    timestamp: float; phase: str
    modules: Dict[str, str] = field(default_factory=dict)
    failed: List[str] = field(default_factory=list)
    recovered: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)

class SystemOrchestratorNative:
    def __init__(self, workspace: str = "./orchestrator", module_dir: str = "./core") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self.module_dir = Path(module_dir)
        self._instances: Dict[str, ModuleInstance] = {}
        self._reports: List[OrchestrationReport] = []
        self._lock = threading.RLock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._reports_path = self.workspace / "reports.json"
        self._load()

    def _load(self) -> None:
        if self._reports_path.exists():
            try:
                with open(self._reports_path, "r", encoding="utf-8") as f:
                    self._reports = [OrchestrationReport(**r) for r in json.load(f)]
            except Exception: pass

    def _save(self) -> None:
        with open(self._reports_path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self._reports], f, indent=2, default=str)

    def _discover_modules(self) -> List[Path]:
        if not self.module_dir.exists(): return []
        return [f for f in self.module_dir.rglob("*.py") if not f.name.startswith("_") and "_native" in f.stem]

    def _load_module_class(self, module_path: Path) -> Tuple[Optional[type], str]:
        try:
            name = module_path.stem
            spec = importlib.util.spec_from_file_location(name, module_path)
            if not spec or not spec.loader: return None, "No spec"
            module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
            classes = [getattr(module, attr) for attr in dir(module) if isinstance(getattr(module, attr), type)]
            for cls in classes:
                if "Native" in cls.__name__ or "Engine" in cls.__name__ or "Manager" in cls.__name__: return cls, ""
            return None, "No main class"
        except Exception as e: return None, f"{type(e).__name__}: {e}"

    def register_module(self, name: str, class_name: str, entry_point: str, manifest_id: str = "") -> ModuleInstance:
        with self._lock:
            inst = ModuleInstance(manifest_id=manifest_id or f"manifest_{name}", name=name, class_name=class_name, entry_point=entry_point)
            self._instances[name] = inst; return inst

    def scan_modules(self) -> int:
        count = 0
        for mp in self._discover_modules():
            cls, error = self._load_module_class(mp)
            if cls: self.register_module(mp.stem.replace("_native", ""), cls.__name__, str(mp)); count += 1
        return count

    def boot_module(self, name: str, **kwargs) -> bool:
        with self._lock:
            inst = self._instances.get(name)
            if not inst: return False
            if inst.status in ("active", "starting"): return True
            inst.status = "starting"
            try:
                cls, error = self._load_module_class(Path(inst.entry_point))
                if not cls: inst.status = "failed"; inst.last_error = error; return False
                instance = cls(**kwargs) if kwargs else cls()
                inst.instance = instance; inst.status = "active"; inst.start_time = time.time(); inst.pid = id(instance)
                return True
            except Exception as e:
                inst.status = "failed"; inst.last_error = f"{type(e).__name__}: {e}"; inst.restart_count += 1
                return False

    def boot_all(self, load_order: Optional[List[str]] = None, **kwargs) -> OrchestrationReport:
        with self._lock:
            report = OrchestrationReport(timestamp=time.time(), phase="boot", actions=[])
            if not self._instances: self.scan_modules()
            order = load_order or list(self._instances.keys())
            for name in order:
                if name not in self._instances: continue
                success = self.boot_module(name, **kwargs)
                report.modules[name] = self._instances[name].status
                if not success: report.failed.append(name); report.actions.append(f"Failed to boot {name}: {self._instances[name].last_error}")
                else: report.actions.append(f"Booted {name}")
            self._reports.append(report); self._save(); return report

    def stop_module(self, name: str) -> bool:
        with self._lock:
            inst = self._instances.get(name)
            if not inst: return False
            inst.status = "stopped"; inst.instance = None; inst.pid = None; inst.start_time = None
            return True

    def stop_all(self) -> OrchestrationReport:
        with self._lock:
            report = OrchestrationReport(timestamp=time.time(), phase="shutdown", actions=[])
            for name in list(self._instances.keys()): self.stop_module(name); report.modules[name] = "stopped"; report.actions.append(f"Stopped {name}")
            self._reports.append(report); self._save(); return report

    def restart_module(self, name: str, **kwargs) -> bool:
        self.stop_module(name); return self.boot_module(name, **kwargs)

    def recover_module(self, name: str, max_retries: int = 3, **kwargs) -> bool:
        for attempt in range(max_retries):
            if self.restart_module(name, **kwargs): return True
            time.sleep(2 ** attempt)
        return False

    def health_check(self) -> OrchestrationReport:
        with self._lock:
            report = OrchestrationReport(timestamp=time.time(), phase="health_check", actions=[])
            for name, inst in self._instances.items():
                if inst.status == "active":
                    healthy = inst.instance is not None
                    if not healthy:
                        report.failed.append(name); report.actions.append(f"Health fail on {name}, attempting recovery")
                        if self.recover_module(name): report.recovered.append(name); report.modules[name] = "active"
                        else: report.modules[name] = "failed"
                    else: report.modules[name] = "active"
                elif inst.status == "failed":
                    report.actions.append(f"Recovering failed module {name}")
                    if self.recover_module(name): report.recovered.append(name); report.modules[name] = "active"
                    else: report.modules[name] = "failed"
                else: report.modules[name] = inst.status
            self._reports.append(report); self._save(); return report

    def start_monitoring(self, interval: float = 60.0) -> None:
        self._running = True
        def monitor_loop():
            while self._running:
                self.health_check()
                time.sleep(interval)
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        self._running = False

    def get_module(self, name: str) -> Optional[ModuleInstance]:
        with self._lock: return self._instances.get(name)

    def get_status(self) -> Dict[str, str]:
        with self._lock: return {name: inst.status for name, inst in self._instances.items()}

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            statuses = {}
            for inst in self._instances.values(): statuses[inst.status] = statuses.get(inst.status, 0) + 1
            total_restarts = sum(inst.restart_count for inst in self._instances.values())
            return {"total_modules": len(self._instances), "statuses": statuses, "total_restarts": total_restarts, "monitoring": self._running, "active": statuses.get("active", 0)}

    def print_summary(self) -> str:
        stats = self.get_stats()
        lines = ["=== System Orchestrator ===", f"Monitoring: {'ON' if stats['monitoring'] else 'OFF'}", f"Active: {stats['active']} / {stats['total_modules']}", f"Total Restarts: {stats['total_restarts']}", "
--- Module Status ---"]
        for name, inst in self._instances.items():
            icon = {"active": "o", "failed": "x", "starting": "*", "recovering": "r", "stopped": "-"}.get(inst.status, "?")
            uptime = f"({time.time()-inst.start_time:.0f}s)" if inst.start_time else ""
            lines.append(f"  {icon} {name} [{inst.status}] {uptime}")
            if inst.last_error: lines.append(f"     Last error: {inst.last_error[:80]}")
        return "
".join(lines)

if __name__ == "__main__":
    orch = SystemOrchestratorNative(module_dir=".")
    orch.scan_modules()
    report = orch.boot_all()
    print(orch.print_summary())
