
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

import atexit
import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
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
    critical: bool = False  # If True, shutdown fails if this layer fails


@dataclass
class ResourceTracker:
    """Tracks open resources for cleanup."""
    files: Set[Any] = field(default_factory=set)
    connections: Set[Any] = field(default_factory=set)
    threads: Set[threading.Thread] = field(default_factory=set)
    processes: Set[subprocess.Popen] = field(default_factory=set)
    locks: Set[threading.Lock] = field(default_factory=set)
    temp_dirs: Set[str] = field(default_factory=set)

    def add_file(self, f: Any) -> None:
        self.files.add(f)

    def add_connection(self, conn: Any) -> None:
        self.connections.add(conn)

    def add_thread(self, t: threading.Thread) -> None:
        self.threads.add(t)

    def add_process(self, p: subprocess.Popen) -> None:
        self.processes.add(p)

    def add_lock(self, lock: threading.Lock) -> None:
        self.locks.add(lock)

    def add_temp_dir(self, path: str) -> None:
        self.temp_dirs.add(path)

    def remove_file(self, f: Any) -> None:
        self.files.discard(f)

    def total(self) -> int:
        return (
            len(self.files) + len(self.connections) + len(self.threads) +
            len(self.processes) + len(self.locks) + len(self.temp_dirs)
        )


# ════════════════════════════════════════════════════════════════════════════
# SystemdNotifier
# ════════════════════════════════════════════════════════════════════════════

class SystemdNotifier:
    """Send readiness and stopping notifications to systemd."""

    def __init__(self) -> None:
        self.socket_path = os.environ.get("NOTIFY_SOCKET")
        self._ready_sent = False

    def _send(self, msg: str) -> bool:
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

    def ready(self) -> bool:
        if not self._ready_sent:
            self._ready_sent = True
            return self._send("READY=1")
        return True

    def stopping(self) -> bool:
        return self._send("STOPPING=1")

    def status(self, message: str) -> bool:
        return self._send(f"STATUS={message}")

    def watchdog(self) -> bool:
        return self._send("WATCHDOG=1")


# ════════════════════════════════════════════════════════════════════════════
# LayerShutdownHandler
# ════════════════════════════════════════════════════════════════════════════

class LayerShutdownHandler:
    """
    Per-layer shutdown handler registry.
    Each layer registers cleanup callbacks that run during shutdown.
    """

    def __init__(self, config: LayerConfig) -> None:
        self.config = config
        self.hooks: List[Callable[[], None]] = []
        self.resource_tracker = ResourceTracker()
        self._lock = threading.Lock()

    def register_hook(self, hook: Callable[[], None]) -> None:
        """Register a cleanup callback for this layer."""
        with self._lock:
            self.hooks.append(hook)

    def run_hooks(self) -> Tuple[int, int, Optional[str]]:
        """
        Execute all registered hooks.
        Returns: (success_count, fail_count, error_message)
        """
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
                traceback.print_exc()
        error_str = "; ".join(errors) if errors else None
        return success, failed, error_str

    def cleanup_resources(self) -> Tuple[int, int]:
        """
        Cleanup tracked resources.
        Returns: (cleaned, failed)
        """
        cleaned = 0
        failed = 0
        rt = self.resource_tracker

        # Close files
        for f in list(rt.files):
            try:
                if hasattr(f, 'close') and not getattr(f, 'closed', True):
                    f.close()
                cleaned += 1
            except Exception:
                failed += 1
        rt.files.clear()

        # Close connections
        for conn in list(rt.connections):
            try:
                if hasattr(conn, 'close'):
                    conn.close()
                cleaned += 1
            except Exception:
                failed += 1
        rt.connections.clear()

        # Join threads (with timeout)
        for t in list(rt.threads):
            try:
                if t.is_alive():
                    t.join(timeout=2.0)
                cleaned += 1
            except Exception:
                failed += 1
        rt.threads.clear()

        # Kill subprocesses
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

        # Remove temp dirs
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


# ════════════════════════════════════════════════════════════════════════════
# ShutdownSequence
# ════════════════════════════════════════════════════════════════════════════

class ShutdownSequence:
    """
    Manages the ordered shutdown sequence from layer 15 down to 0.
    Handles dependencies and critical layer failures.
    """

    def __init__(self) -> None:
        self.handlers: Dict[int, LayerShutdownHandler] = {}
        self.results: List[ShutdownResult] = []

    def register_layer(self, config: LayerConfig) -> LayerShutdownHandler:
        handler = LayerShutdownHandler(config)
        self.handlers[config.layer_id] = handler
        return handler

    def get_order(self) -> List[int]:
        """Return shutdown order: highest layer first, respecting dependencies."""
        ids = sorted(self.handlers.keys(), reverse=True)
        ordered: List[int] = []
        visited: Set[int] = set()

        def visit(layer_id: int) -> None:
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

    def execute(self, force_kill: bool = False) -> List[ShutdownResult]:
        """Execute shutdown sequence."""
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

            # Stop on critical failure (unless force_kill)
            if config.critical and phase == ShutdownPhase.FAILED and not force_kill:
                break

        return self.results

    def _shutdown_layer(self, handler: LayerShutdownHandler, config: LayerConfig) -> ShutdownPhase:
        """Shutdown a single layer with timeout."""
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

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=config.timeout_sec)

        if thread.is_alive():
            # Timeout exceeded — force kill
            if config.force_kill_after > 0:
                thread.join(timeout=config.force_kill_after)
            if thread.is_alive():
                return ShutdownPhase.FORCE_KILL

        return result["phase"]


# ════════════════════════════════════════════════════════════════════════════
# ShutdownManager
# ════════════════════════════════════════════════════════════════════════════

class ShutdownManager:
    """
    Central graceful shutdown orchestrator for MAGNATRIX-OS.

    Features:
        • SIGTERM/SIGINT handler registration
        • Layer-by-layer shutdown (15 -> 0)
        • Per-layer timeout and force-kill
        • Resource cleanup tracking
        • Systemd notify integration
        • Shutdown status reporting
        • Force-kill mode for emergency shutdown
    """

    def __init__(self, systemd_notify: bool = True) -> None:
        self.sequence = ShutdownSequence()
        self.systemd = SystemdNotifier() if systemd_notify else None
        self._phase = ShutdownPhase.IDLE
        self._lock = threading.Lock()
        self._shutdown_thread: Optional[threading.Thread] = None
        self._atexit_registered = False

    @property
    def phase(self) -> ShutdownPhase:
        with self._lock:
            return self._phase

    def register_layer(
        self, layer_id: int, name: str,
        timeout_sec: float = 30.0, force_kill_after: float = 5.0,
        dependencies: Optional[List[int]] = None,
        critical: bool = False
    ) -> LayerShutdownHandler:
        """Register a layer for managed shutdown."""
        config = LayerConfig(
            layer_id=layer_id, name=name,
            timeout_sec=timeout_sec,
            force_kill_after=force_kill_after,
            dependencies=dependencies or [],
            critical=critical
        )
        return self.sequence.register_layer(config)

    def install_signal_handlers(self) -> None:
        """Install SIGTERM and SIGINT handlers."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def register_atexit(self) -> None:
        """Register shutdown with atexit."""
        if not self._atexit_registered:
            atexit.register(self.shutdown, force=False)
            self._atexit_registered = True

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        print(f"\\n[ShutdownManager] Received signal {signum}, initiating graceful shutdown...")
        self.shutdown(force=False)
        sys.exit(0)

    def shutdown(self, force: bool = False) -> List[ShutdownResult]:
        """
        Initiate graceful shutdown.
        If force=True, skip timeouts and force-kill immediately.
        """
        with self._lock:
            if self._phase != ShutdownPhase.IDLE:
                return self.sequence.results
            self._phase = ShutdownPhase.STARTING

        if self.systemd:
            self.systemd.stopping()
            self.systemd.status("Shutting down MAGNATRIX-OS layers...")

        self._phase = ShutdownPhase.IN_PROGRESS
        results = self.sequence.execute(force_kill=force)

        # Determine final phase
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

    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive shutdown status report."""
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

    def save_report(self, path: str) -> None:
        """Save shutdown report to JSON file."""
        report = self.get_status_report()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


# ════════════════════════════════════════════════════════════════════════════
# KernelShutdownBridge
# ════════════════════════════════════════════════════════════════════════════

class KernelShutdownBridge:
    """
    Bridge between kernel and shutdown manager.
    Registers all kernel services for graceful shutdown.
    """

    def __init__(self, manager: ShutdownManager) -> None:
        self.manager = manager

    def register_kernel_services(self) -> None:
        """Register all kernel layer services."""
        # Layer 0: Kernel
        kernel_handler = self.manager.register_layer(
            0, "kernel", timeout_sec=10.0, critical=True
        )
        kernel_handler.register_hook(lambda: print("[Kernel] Stopping event bus..."))
        kernel_handler.register_hook(lambda: print("[Kernel] Closing log rotator..."))

        # Layer 1: Protocol
        protocol_handler = self.manager.register_layer(
            1, "protocol", timeout_sec=15.0, dependencies=[0]
        )
        protocol_handler.register_hook(lambda: print("[Protocol] Closing connections..."))

        # Layer 3: Runtime
        runtime_handler = self.manager.register_layer(
            3, "runtime", timeout_sec=20.0, dependencies=[1]
        )
        runtime_handler.register_hook(lambda: print("[Runtime] Stopping schedulers..."))

        # Layer 5: Knowledge
        knowledge_handler = self.manager.register_layer(
            5, "knowledge", timeout_sec=15.0, dependencies=[3]
        )
        knowledge_handler.register_hook(lambda: print("[Knowledge] Flushing caches..."))

        # Layer 8: Trading
        trading_handler = self.manager.register_layer(
            8, "trading", timeout_sec=10.0, dependencies=[5], critical=True
        )
        trading_handler.register_hook(lambda: print("[Trading] Closing positions..."))

        # Layer 10: AI
        ai_handler = self.manager.register_layer(
            10, "ai", timeout_sec=20.0, dependencies=[8]
        )
        ai_handler.register_hook(lambda: print("[AI] Stopping inference backends..."))

        # Layer 15: Web / GUI
        web_handler = self.manager.register_layer(
            15, "web", timeout_sec=10.0, dependencies=[10]
        )
        web_handler.register_hook(lambda: print("[Web] Stopping HTTP server..."))


# ════════════════════════════════════════════════════════════════════════════
# DEMO / SELF-TEST
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Shutdown Manager — Self-Test")
    print("=" * 60)

    # Test 1: Basic shutdown sequence
    print("\n[1] Basic 5-layer shutdown sequence")
    mgr = ShutdownManager(systemd_notify=False)
    bridge = KernelShutdownBridge(mgr)
    bridge.register_kernel_services()
    results = mgr.shutdown(force=False)
    print(f"  → Shutdown complete: {len(results)} layers")
    for r in results:
        print(f"      Layer {r.layer_id} ({r.layer_name}): {r.status.value} ({r.duration_ms:.1f}ms)")

    # Test 2: Status report
    print("\n[2] Status report")
    report = mgr.get_status_report()
    print(f"  → Total layers: {report['layers_total']}")
    print(f"  → Completed: {report['layers_completed']}")
    print(f"  → Failed: {report['layers_failed']}")
    print(f"  → Force killed: {report['layers_force_killed']}")
    print(f"  → Total duration: {report['total_duration_ms']:.1f}ms")
    print(f"  → Resources cleaned: {report['total_resources_cleaned']}")

    # Test 3: Layer ordering
    print("\n[3] Layer shutdown order")
    mgr2 = ShutdownManager(systemd_notify=False)
    seq = mgr2.sequence
    seq.register_layer(LayerConfig(15, "web", dependencies=[10]))
    seq.register_layer(LayerConfig(10, "ai", dependencies=[5]))
    seq.register_layer(LayerConfig(5, "knowledge", dependencies=[3]))
    seq.register_layer(LayerConfig(3, "runtime", dependencies=[1]))
    seq.register_layer(LayerConfig(1, "protocol", dependencies=[0]))
    seq.register_layer(LayerConfig(0, "kernel"))
    order = seq.get_order()
    print(f"  → Order: {order} (expected: [15, 10, 5, 3, 1, 0])")
    assert order == [15, 10, 5, 3, 1, 0], f"Unexpected order: {order}"
    print("  ✓ Order correct")

    # Test 4: Resource tracking
    print("\n[4] Resource tracking")
    handler = seq.handlers[0]
    handler.resource_tracker.add_temp_dir("/tmp/test_dir")
    cleaned, failed = handler.cleanup_resources()
    print(f"  → Cleaned: {cleaned}, Failed: {failed}")
    assert cleaned >= 1, "Expected at least 1 resource cleaned"
    print("  ✓ Resource tracking works")

    # Test 5: Systemd notifier (mock)
    print("\n[5] Systemd notifier (no socket)")
    sd = SystemdNotifier()
    assert not sd.ready(), "Should fail without NOTIFY_SOCKET"
    print("  ✓ Systemd notifier correctly detects missing socket")

    # Test 6: Signal handler installation
    print("\n[6] Signal handler installation")
    mgr3 = ShutdownManager(systemd_notify=False)
    mgr3.install_signal_handlers()
    print("  ✓ Signal handlers installed (SIGTERM, SIGINT)")

    # Test 7: Save report
    print("\n[7] Save report to JSON")
    mgr.save_report("/tmp/shutdown_report.json")
    with open("/tmp/shutdown_report.json") as f:
        saved = json.load(f)
    assert saved["layers_total"] > 0
    print(f"  ✓ Report saved: {saved['layers_total']} layers")

    print("\n" + "=" * 60)
    print("All self-tests passed ✓")
    print("=" * 60)
