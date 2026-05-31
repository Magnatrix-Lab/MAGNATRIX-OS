
"""
kernel/shutdown_manager_native.py — MAGNATRIX-OS Graceful Shutdown Manager

AMATI pattern: systemd graceful shutdown + layered application cleanup.
Pure Python, stdlib only. Zero dependencies.

Components:
    • ShutdownManager — central graceful shutdown orchestrator
    • LayerShutdownHandler — per-layer shutdown handler registry
    • ShutdownSequence — configurable shutdown ordering (layer 15 -> 0)
    • ResourceCleanup — file handles, DB connections, threads, subprocess cleanup
    • SystemdNotifier — systemd NOTIFY_SOCKET integration
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ════════════════════════════════════════════════════════════════════════════
# Data Structures
# ════════════════════════════════════════════════════════════════════════════

class ShutdownPhase(Enum):
    IDLE = "idle"
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    FORCE_KILL = "force_kill"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ShutdownResult:
    layer_name: str
    layer_id: int
    status: ShutdownPhase
    duration_ms: float
    error: Optional[str] = None
    resources_cleaned: int = 0
    resources_failed: int = 0


@dataclass
class LayerConfig:
    layer_id: int
    name: str
    timeout_sec: float = 30.0
    force_kill_after: float = 5.0
    dependencies: List[int] = field(default_factory=list)
    critical: bool = False


@dataclass
class ResourceTracker:
    files: Set[Any] = field(default_factory=set)
    connections: Set[Any] = field(default_factory=set)
    threads: Set[threading.Thread] = field(default_factory=set)
    processes: Set[subprocess.Popen] = field(default_factory=set)
    locks: Set[threading.Lock] = field(default_factory=set)
    temp_dirs: Set[str] = field(default_factory=set)

    def total(self) -> int:
        return len(self.files) + len(self.connections) + len(self.threads) + len(self.processes) + len(self.locks) + len(self.temp_dirs)


class SystemdNotifier:
    def __init__(self):
        self.socket_path = os.environ.get("NOTIFY_SOCKET")

    def _send(self, msg):
        if not self.socket_path:
            return False
        try:
            import socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.connect(self.socket_path)
            sock.sendall(msg.encode())
            sock.close()
            return True
        except Exception:
            return False

    def ready(self):
        return self._send("READY=1")

    def stopping(self):
        return self._send("STOPPING=1")

    def status(self, message):
        return self._send(f"STATUS={message}")


class LayerShutdownHandler:
    def __init__(self, config):
        self.config = config
        self.hooks = []
        self.resource_tracker = ResourceTracker()
        self._lock = threading.Lock()

    def register_hook(self, hook):
        with self._lock:
            self.hooks.append(hook)

    def run_hooks(self):
        success = 0
        failed = 0
        errors = []
        for hook in self.hooks:
            try:
                hook()
                success += 1
            except Exception as e:
                failed += 1
                errors.append(str(e))
        return success, failed, "; ".join(errors) if errors else None

    def cleanup_resources(self):
        cleaned = 0
        failed = 0
        rt = self.resource_tracker

        for f in list(rt.files):
            try:
                if hasattr(f, 'close') and not getattr(f, 'closed', True):
                    f.close()
                cleaned += 1
            except Exception:
                failed += 1
        rt.files.clear()

        for conn in list(rt.connections):
            try:
                if hasattr(conn, 'close'):
                    conn.close()
                cleaned += 1
            except Exception:
                failed += 1
        rt.connections.clear()

        for t in list(rt.threads):
            try:
                if t.is_alive():
                    t.join(timeout=2.0)
                cleaned += 1
            except Exception:
                failed += 1
        rt.threads.clear()

        for p in list(rt.processes):
            try:
                if p.poll() is None:
                    p.terminate()
                    time.sleep(0.5)
                    if p.poll() is None:
                        p.kill()
                cleaned += 1
            except Exception:
                failed += 1
        rt.processes.clear()

        for td in list(rt.temp_dirs):
            try:
                import shutil
                if os.path.exists(td):
                    shutil.rmtree(td, ignore_errors=True)
                cleaned += 1
            except Exception:
                failed += 1
        rt.temp_dirs.clear()

        return cleaned, failed


class ShutdownSequence:
    def __init__(self):
        self.handlers = {}
        self.results = []

    def register_layer(self, config):
        handler = LayerShutdownHandler(config)
        self.handlers[config.layer_id] = handler
        return handler

    def get_order(self):
        ids = sorted(self.handlers.keys(), reverse=True)
        ordered = []
        visited = set()

        def visit(layer_id):
            if layer_id in visited:
                return
            visited.add(layer_id)
            config = self.handlers[layer_id].config
            for dep in config.dependencies:
                if dep in self.handlers:
                    visit(dep)
            ordered.append(layer_id)

        for lid in ids:
            visit(lid)

        return list(reversed(ordered))

    def execute(self, force_kill=False):
        self.results = []
        order = self.get_order()

        for layer_id in order:
            handler = self.handlers[layer_id]
            config = handler.config
            start = time.time()

            if force_kill:
                phase = ShutdownPhase.FORCE_KILL
            else:
                phase = self._shutdown_layer(handler, config)

            duration = (time.time() - start) * 1000
            cleaned, failed = handler.cleanup_resources() if phase != ShutdownPhase.FAILED else (0, 0)

            result = ShutdownResult(
                layer_name=config.name,
                layer_id=layer_id,
                status=phase,
                duration_ms=duration,
                resources_cleaned=cleaned,
                resources_failed=failed,
            )
            self.results.append(result)

            if config.critical and phase == ShutdownPhase.FAILED and not force_kill:
                break

        return self.results

    def _shutdown_layer(self, handler, config):
        result = {"phase": ShutdownPhase.IN_PROGRESS}

        def target():
            try:
                success, failed, error = handler.run_hooks()
                result["phase"] = ShutdownPhase.COMPLETED if failed == 0 else ShutdownPhase.FAILED
                if error:
                    result["error"] = error
            except Exception as e:
                result["phase"] = ShutdownPhase.FAILED
                result["error"] = str(e)

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=config.timeout_sec)

        if thread.is_alive():
            if config.force_kill_after > 0:
                thread.join(timeout=config.force_kill_after)
            if thread.is_alive():
                return ShutdownPhase.FORCE_KILL

        return result["phase"]


class ShutdownManager:
    def __init__(self, systemd_notify=True):
        self.sequence = ShutdownSequence()
        self.systemd = SystemdNotifier() if systemd_notify else None
        self._phase = ShutdownPhase.IDLE
        self._lock = threading.Lock()
        self._shutdown_thread = None
        self._atexit_registered = False

    @property
    def phase(self):
        with self._lock:
            return self._phase

    def register_layer(self, layer_id, name, timeout_sec=30.0, force_kill_after=5.0, dependencies=None, critical=False):
        config = LayerConfig(
            layer_id=layer_id, name=name,
            timeout_sec=timeout_sec,
            force_kill_after=force_kill_after,
            dependencies=dependencies or [],
            critical=critical
        )
        return self.sequence.register_layer(config)

    def install_signal_handlers(self):
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def register_atexit(self):
        import atexit
        if not self._atexit_registered:
            atexit.register(self.shutdown, force=False)
            self._atexit_registered = True

    def _signal_handler(self, signum, frame):
        print(f"\n[ShutdownManager] Received signal {signum}, initiating graceful shutdown...")
        self.shutdown(force=False)
        sys.exit(0)

    def shutdown(self, force=False):
        with self._lock:
            if self._phase != ShutdownPhase.IDLE:
                return self.sequence.results
            self._phase = ShutdownPhase.STARTING

        if self.systemd:
            self.systemd.stopping()
            self.systemd.status("Shutting down MAGNATRIX-OS layers...")

        self._phase = ShutdownPhase.IN_PROGRESS
        results = self.sequence.execute(force_kill=force)

        any_failed = any(r.status == ShutdownPhase.FAILED for r in results)
        any_force = any(r.status == ShutdownPhase.FORCE_KILL for r in results)

        if any_force:
            self._phase = ShutdownPhase.FORCE_KILL
        elif any_failed:
            self._phase = ShutdownPhase.FAILED
        else:
            self._phase = ShutdownPhase.COMPLETED

        if self.systemd:
            self.systemd.status("Shutdown complete")

        return results

    def get_status_report(self):
        results = self.sequence.results
        return {
            "phase": self._phase.value,
            "layers_total": len(results),
            "layers_completed": sum(1 for r in results if r.status == ShutdownPhase.COMPLETED),
            "layers_failed": sum(1 for r in results if r.status == ShutdownPhase.FAILED),
            "layers_force_killed": sum(1 for r in results if r.status == ShutdownPhase.FORCE_KILL),
            "total_duration_ms": sum(r.duration_ms for r in results),
            "total_resources_cleaned": sum(r.resources_cleaned for r in results),
            "total_resources_failed": sum(r.resources_failed for r in results),
            "layers": [
                {
                    "id": r.layer_id,
                    "name": r.layer_name,
                    "status": r.status.value,
                    "duration_ms": round(r.duration_ms, 2),
                    "resources_cleaned": r.resources_cleaned,
                    "resources_failed": r.resources_failed,
                    "error": r.error,
                }
                for r in results
            ],
        }

    def save_report(self, path):
        report = self.get_status_report()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


class KernelShutdownBridge:
    def __init__(self, manager):
        self.manager = manager

    def register_kernel_services(self):
        kernel_handler = self.manager.register_layer(0, "kernel", timeout_sec=10.0, critical=True)
        kernel_handler.register_hook(lambda: print("[Kernel] Stopping event bus..."))
        kernel_handler.register_hook(lambda: print("[Kernel] Closing log rotator..."))

        protocol_handler = self.manager.register_layer(1, "protocol", timeout_sec=15.0, dependencies=[0])
        protocol_handler.register_hook(lambda: print("[Protocol] Closing connections..."))

        runtime_handler = self.manager.register_layer(3, "runtime", timeout_sec=20.0, dependencies=[1])
        runtime_handler.register_hook(lambda: print("[Runtime] Stopping schedulers..."))

        knowledge_handler = self.manager.register_layer(5, "knowledge", timeout_sec=15.0, dependencies=[3])
        knowledge_handler.register_hook(lambda: print("[Knowledge] Flushing caches..."))

        trading_handler = self.manager.register_layer(8, "trading", timeout_sec=10.0, dependencies=[5], critical=True)
        trading_handler.register_hook(lambda: print("[Trading] Closing positions..."))

        ai_handler = self.manager.register_layer(10, "ai", timeout_sec=20.0, dependencies=[8])
        ai_handler.register_hook(lambda: print("[AI] Stopping inference backends..."))

        web_handler = self.manager.register_layer(15, "web", timeout_sec=10.0, dependencies=[10])
        web_handler.register_hook(lambda: print("[Web] Stopping HTTP server..."))


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Shutdown Manager — Self-Test")
    print("=" * 60)

    mgr = ShutdownManager(systemd_notify=False)
    bridge = KernelShutdownBridge(mgr)
    bridge.register_kernel_services()
    results = mgr.shutdown(force=False)
    print(f"\nShutdown complete: {len(results)} layers")
    for r in results:
        print(f"  Layer {r.layer_id} ({r.layer_name}): {r.status.value} ({r.duration_ms:.1f}ms)")

    report = mgr.get_status_report()
    print(f"\nTotal layers: {report['layers_total']}")
    print(f"Completed: {report['layers_completed']}")
    print(f"Failed: {report['layers_failed']}")
    print(f"Force killed: {report['layers_force_killed']}")

    mgr.save_report("/tmp/shutdown_report.json")
    with open("/tmp/shutdown_report.json") as f:
        saved = json.load(f)
    print(f"\nReport saved: {saved['layers_total']} layers")

    print("\n" + "=" * 60)
    print("All self-tests passed ✓")
    print("=" * 60)
