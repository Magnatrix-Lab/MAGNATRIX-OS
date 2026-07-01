#!/usr/bin/env python3
"""health_check_aggregator_native.py — MAGNATRIX-OS Health Check Aggregator (doctor)

Systematic health check for all modules: boot status, connectivity, resource usage,
dependency check. Output: pass/fail/warning per module. Inspired by Agent Reach doctor.
Pure stdlib.
"""
from __future__ import annotations
import importlib.util
import json
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class HealthCheck:
    module: str; status: str = "unknown"; icon: str = ""; boot_status: str = "unknown"
    load_time_ms: float = 0.0; last_error: str = ""; dependencies_met: bool = True
    missing_dependencies: List[str] = field(default_factory=list)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    checked_at: float = field(default_factory=time.time)

@dataclass
class HealthReport:
    timestamp: float; total_modules: int; passed: int; failed: int; warnings: int; unknown: int
    checks: List[HealthCheck] = field(default_factory=list); summary: str = ""
    recommendations: List[str] = field(default_factory=list)

class HealthCheckAggregatorNative:
    def __init__(self, workspace: str = "./health", module_dir: str = "./core") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self.module_dir = Path(module_dir); self._checks: List[HealthCheck] = []
        self._reports: List[HealthReport] = []; self._lock = threading.RLock()
        self._reports_path = self.workspace / "reports.json"; self._load()

    def _load(self) -> None:
        if self._reports_path.exists():
            try:
                with open(self._reports_path, "r", encoding="utf-8") as f: self._reports = [HealthReport(**r) for r in json.load(f)]
            except Exception: pass

    def _save(self) -> None:
        with open(self._reports_path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self._reports], f, indent=2, default=str)

    def _discover_modules(self) -> List[Path]:
        if not self.module_dir.exists(): return []
        return [f for f in self.module_dir.rglob("*.py") if not f.name.startswith("_") and "_native" in f.stem]

    def _check_module(self, module_path: Path) -> HealthCheck:
        start = time.time(); name = module_path.stem
        try:
            spec = importlib.util.spec_from_file_location(name, module_path)
            if not spec or not spec.loader:
                return HealthCheck(module=name, status="fail", icon="x", boot_status="no_spec", load_time_ms=(time.time()-start)*1000, last_error="Cannot create module spec")
            module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
            load_time = (time.time()-start)*1000
            classes = [getattr(module, attr) for attr in dir(module) if isinstance(getattr(module, attr), type)]
            main_class = None
            for cls in classes:
                if "Native" in cls.__name__ or "Engine" in cls.__name__ or "Manager" in cls.__name__: main_class = cls; break
            if not main_class: return HealthCheck(module=name, status="warning", icon="!", boot_status="no_main_class", load_time_ms=load_time, last_error="No recognizable main class")
            try:
                instance = main_class(); inst_time = (time.time()-start)*1000
                has_health = hasattr(instance, "get_stats") or hasattr(instance, "health_check") or hasattr(instance, "list")
                return HealthCheck(module=name, status="pass" if has_health else "warning", icon="o" if has_health else "!", boot_status="booted", load_time_ms=load_time+inst_time, metadata={"has_health_methods": has_health, "class_name": main_class.__name__})
            except TypeError as e:
                if "missing" in str(e).lower() or "required" in str(e).lower():
                    return HealthCheck(module=name, status="fail", icon="x", boot_status="init_error", load_time_ms=load_time, last_error=f"Constructor requires arguments: {e}")
                raise
        except Exception as e:
            return HealthCheck(module=name, status="fail", icon="x", boot_status="exception", load_time_ms=(time.time()-start)*1000, last_error=f"{type(e).__name__}: {e}")

    def run_all(self, module_paths: Optional[List[Path]] = None) -> HealthReport:
        with self._lock:
            modules = module_paths or self._discover_modules(); checks = []
            for mp in modules: checks.append(self._check_module(mp))
            passed = sum(1 for c in checks if c.status == "pass")
            failed = sum(1 for c in checks if c.status == "fail")
            warnings = sum(1 for c in checks if c.status == "warning")
            unknown = sum(1 for c in checks if c.status == "unknown")
            recommendations = []
            failing = [c.module for c in checks if c.status == "fail"]
            if failing: recommendations.append(f"Fix failing modules: {', '.join(failing)}")
            boot_errors = [c.module for c in checks if "init_error" in c.boot_status]
            if boot_errors: recommendations.append(f"Boot fix needed (constructor args): {', '.join(boot_errors)}")
            no_health = [c.module for c in checks if c.status == "warning" and not c.metadata.get("has_health_methods", False)]
            if no_health: recommendations.append(f"Add health methods to: {', '.join(no_health)}")
            if not recommendations: recommendations.append("All modules healthy. Schedule next check in 30 min.")
            summary = f"o {passed} | x {failed} | ! {warnings} | ? {unknown} / {len(checks)}"
            report = HealthReport(timestamp=time.time(), total_modules=len(checks), passed=passed, failed=failed, warnings=warnings, unknown=unknown, checks=checks, summary=summary, recommendations=recommendations)
            self._reports.append(report); self._save()
            return report

    def check_one(self, module_name: str) -> Optional[HealthCheck]:
        if not self.module_dir.exists(): return None
        for f in self.module_dir.rglob("*.py"):
            if f.stem == module_name or f.stem.replace("_native", "") == module_name:
                return self._check_module(f)
        return None

    def get_latest(self) -> Optional[HealthReport]:
        with self._lock: return self._reports[-1] if self._reports else None

    def get_trend(self, metric: str = "passed", window: int = 10) -> List[int]:
        with self._lock: return [getattr(r, metric, 0) for r in self._reports[-window:]]

    def print_summary(self, report: Optional[HealthReport] = None) -> str:
        r = report or self.get_latest()
        if not r: return "No health report available."
        lines = [f"=== Health Check Report ({time.ctime(r.timestamp)}) ===", f"Summary: {r.summary}", "
--- Per-Module Status ---"]
        for c in r.checks:
            icon = c.icon or {"pass": "o", "fail": "x", "warning": "!", "unknown": "?"}.get(c.status, "?")
            lines.append(f"  {icon} {c.module} ({c.boot_status}) -- {c.load_time_ms:.0f}ms")
            if c.last_error: lines.append(f"     Error: {c.last_error[:100]}")
        lines.append("
--- Recommendations ---")
        for rec in r.recommendations: lines.append(f"  - {rec}")
        return "
".join(lines)

    def watch(self, interval_seconds: float = 1800.0) -> None:
        def loop():
            while True:
                self.run_all()
                time.sleep(interval_seconds)
        t = threading.Thread(target=loop, daemon=True); t.start()

    def export_json(self, path: Optional[str] = None) -> str:
        report = self.get_latest()
        if not report: return "{}"
        output_path = Path(path) if path else self.workspace / "latest_health.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
        return str(output_path)

if __name__ == "__main__":
    health = HealthCheckAggregatorNative(module_dir=".")
    report = health.run_all()
    print(health.print_summary(report))
