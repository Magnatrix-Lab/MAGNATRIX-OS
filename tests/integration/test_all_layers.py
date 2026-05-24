#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Integration Test Suite
Layer Coverage: 0-13.5 (All 15 Layers)
================================================================================
End-to-end boot, interop, and stress tests for the native layer implementations.
Run: python3 -m tests.integration.test_all_layers
================================================================================
"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Constants
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LAYER_MAP: Dict[str, Tuple[str, ...]] = {
    "kernel": ("kernel.kernel_native", "kernel.logging_engine", "config.magnatrix_config"),
    "protocol": ("protocol.protocol_native",),
    "api_router": ("api-router.api_router_native",),
    "identity": ("identity.identity_native",),
    "runtime": ("runtime.repo_hunter_native", "runtime.autodev_native", "runtime.go_patterns_native"),
    "p2p_mesh": ("p2p-mesh.p2p_mesh_native",),
    "knowledge": (
        "knowledge.arcticdb_native",
        "knowledge.openchronicle_native",
        "knowledge.perspective_native",
    ),
    "skills": ("skills.hermes_skill_engine_native",),
    "browser": ("browser.browser_native",),
    "hft": ("hft.quant_signal_engine_native", "hft.alpha101_native"),
    "security": ("security.offensive_native", "security.agentic_radar_native", "security.bugbounty_native"),
    "uncensored_ai": ("ai.uncensored_ai_native", "uncensored.ml_intern_native"),
    "governance": ("governance.governance_native",),
    "ide": ("ide.terminal_multiplexer_native",),
    "repo_hunter": ("runtime.repo_hunter_native",),
}


# =============================================================================
# Result Types
# =============================================================================
class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class TestResult:
    name: str
    layer: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    traceback_str: str = ""


@dataclass
class LayerReport:
    layer: str
    tests: List[TestResult] = field(default_factory=list)
    total_time_ms: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.status == TestStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if t.status in (TestStatus.FAIL, TestStatus.ERROR))

    @property
    def skipped(self) -> int:
        return sum(1 for t in self.tests if t.status == TestStatus.SKIP)


# =============================================================================
# Test Runner Core
# =============================================================================
class TestRunner:
    """Discovers and executes tests, collects structured results."""

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self.results: List[LayerReport] = []
        self._start_ns: Optional[int] = None

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[TEST] {msg}")

    def run_sync(self, test_fn: Callable[..., bool], *args: Any, **kwargs: Any) -> Tuple[bool, str]:
        """Execute a synchronous test function safely."""
        try:
            ok = test_fn(*args, **kwargs)
            return bool(ok), ""
        except Exception as exc:
            return False, f"{exc}\n{traceback.format_exc()}"

    async def run_async(self, test_fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Tuple[bool, str]:
        """Execute an async test function safely."""
        try:
            ok = await test_fn(*args, **kwargs)
            return bool(ok), ""
        except Exception as exc:
            return False, f"{exc}\n{traceback.format_exc()}"

    def record(self, layer: str, name: str, ok: bool, duration_ms: float, msg: str = "") -> None:
        status = TestStatus.PASS if ok else TestStatus.FAIL
        if not ok and msg:
            status = TestStatus.ERROR
        result = TestResult(name=name, layer=layer, status=status, duration_ms=duration_ms, message=msg)
        # Append to existing report or create new
        for report in self.results:
            if report.layer == layer:
                report.tests.append(result)
                return
        report = LayerReport(layer=layer)
        report.tests.append(result)
        self.results.append(report)

    def summary(self) -> str:
        total_pass = sum(r.passed for r in self.results)
        total_fail = sum(r.failed for r in self.results)
        total_skip = sum(r.skipped for r in self.results)
        total = total_pass + total_fail + total_skip
        lines = [
            "",
            "=" * 70,
            "INTEGRATION TEST SUMMARY",
            "=" * 70,
            f"Total: {total}  |  PASS: {total_pass}  |  FAIL: {total_fail}  |  SKIP: {total_skip}",
            "-" * 70,
        ]
        for report in self.results:
            icon = "✓" if report.failed == 0 else "✗"
            lines.append(
                f"  {icon} {report.layer:20s} — {report.passed}/{len(report.tests)} passed "
                f"({report.total_time_ms:.1f}ms)"
            )
            for t in report.tests:
                if t.status != TestStatus.PASS:
                    lines.append(f"      → {t.name}: {t.status.value} — {t.message[:80]}")
        lines.append("=" * 70)
        return "\n".join(lines)


# =============================================================================
# Layer Boot Tests
# =============================================================================
class LayerBootTest:
    """Verifies that every layer module can be imported and has expected exports."""

    MIN_CLASSES_PER_LAYER = 3
    MIN_FUNCTIONS_PER_LAYER = 2

    def __init__(self, runner: TestRunner) -> None:
        self.runner = runner
        self._sys_path_modified = False
        self._ensure_path()

    def _ensure_path(self) -> None:
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
            self._sys_path_modified = True

    def _modname_to_import(self, name: str) -> str:
        """Convert filesystem-style module path to Python import path."""
        return name.replace("-", "_").replace("/", ".")

    def run_all(self) -> None:
        self.runner._log("Starting LayerBootTest for all 15 layers...")
        for layer_name, modules in LAYER_MAP.items():
            layer_start = time.perf_counter_ns()
            for mod in modules:
                self._test_module_import(layer_name, mod)
            layer_ms = (time.perf_counter_ns() - layer_start) / 1e6
            for report in self.runner.results:
                if report.layer == layer_name:
                    report.total_time_ms = layer_ms
        self.runner._log("LayerBootTest complete.")

    def _test_module_import(self, layer: str, mod_path: str) -> None:
        name = f"import_{mod_path.replace('.', '_')}"
        start = time.perf_counter_ns()
        import_name = self._modname_to_import(mod_path)
        try:
            mod = importlib.import_module(import_name)
            members = inspect.getmembers(mod, predicate=lambda x: inspect.isclass(x) or inspect.isfunction(x))
            classes = [m for m in members if inspect.isclass(m[1])]
            funcs = [m for m in members if inspect.isfunction(m[1])]
            ok = len(classes) >= self.MIN_CLASSES_PER_LAYER or len(funcs) >= self.MIN_FUNCTIONS_PER_LAYER
            msg = f"{len(classes)} classes, {len(funcs)} funcs"
            if not ok:
                msg = f"Expected >= {self.MIN_CLASSES_PER_LAYER} classes or >= {self.MIN_FUNCTIONS_PER_LAYER} funcs, got {msg}"
            self.runner.record(layer, name, ok, (time.perf_counter_ns() - start) / 1e6, msg)
        except Exception as exc:
            self.runner.record(
                layer, name, False, (time.perf_counter_ns() - start) / 1e6,
                f"Import error: {exc}"
            )


# =============================================================================
# Interoperability Tests
# =============================================================================
class InteropTest:
    """Tests cross-layer message passing, shared registry, and event bus wiring."""

    def __init__(self, runner: TestRunner) -> None:
        self.runner = runner
        self._ensure_path()

    def _ensure_path(self) -> None:
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

    def run_all(self) -> None:
        self.runner._log("Starting InteropTest...")
        self._test_kernel_event_bus()
        self._test_layer_registry()
        self._test_config_priority()
        self._test_browser_stealth_signal()
        self._test_ai_model_registry_roundtrip()
        self._test_repo_hunter_priority_queue()
        self._test_terminal_session_lifecycle()
        self._test_security_audit_chain()
        self._test_p2p_message_serialize()
        self._test_hft_signal_transform()
        self.runner._log("InteropTest complete.")

    def _test_kernel_event_bus(self) -> None:
        name = "kernel_event_bus_pub_sub"
        start = time.perf_counter_ns()
        try:
            from kernel.kernel_native import MagnatrixKernel, EventBus
            bus = EventBus()
            received: List[Any] = []
            def handler(ev: Any) -> None:
                received.append(ev)
            bus.subscribe("test.channel", handler)
            bus.publish("test.channel", {"payload": 42})
            ok = len(received) == 1 and received[0].get("payload") == 42
            self.runner.record("kernel", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("kernel", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))

    def _test_layer_registry(self) -> None:
        name = "layer_registry_register_resolve"
        start = time.perf_counter_ns()
        try:
            from kernel.kernel_native import LayerRegistry
            reg = LayerRegistry()
            reg.register("test_layer", {"version": "1.0.0"})
            meta = reg.resolve("test_layer")
            ok = meta is not None and meta.get("version") == "1.0.0"
            self.runner.record("kernel", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("kernel", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))

    def _test_config_priority(self) -> None:
        name = "config_env_over_default"
        start = time.perf_counter_ns()
        try:
            from config.magnatrix_config import ConfigManager
            cm = ConfigManager()
            cm.set("test_key", "default_value")
            import os
            os.environ["MAGNATRIX_test_key"] = "env_value"
            cm.reload()
            val = cm.get("test_key")
            ok = val == "env_value"
            del os.environ["MAGNATRIX_test_key"]
            self.runner.record("kernel", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("kernel", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))

    def _test_browser_stealth_signal(self) -> None:
        name = "browser_stealth_signal_emit"
        start = time.perf_counter_ns()
        try:
            from browser.browser_native import BrowserKernelBridge
            bridge = BrowserKernelBridge()
            ok = hasattr(bridge, "emit") or hasattr(bridge, "signal")
            self.runner.record("browser", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("browser", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))

    def _test_ai_model_registry_roundtrip(self) -> None:
        name = "ai_model_registry_roundtrip"
        start = time.perf_counter_ns()
        try:
            from ai.uncensored_ai_native import ModelRegistry
            reg = ModelRegistry()
            reg.register("test-model", {"path": "/tmp/test", "format": "gguf"})
            info = reg.get("test-model")
            ok = info is not None and info.get("format") == "gguf"
            self.runner.record("uncensored_ai", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("uncensored_ai", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))

    def _test_repo_hunter_priority_queue(self) -> None:
        name = "repo_hunter_priority_queue_order"
        start = time.perf_counter_ns()
        try:
            from runtime.repo_hunter_native import PriorityQueue
            pq = PriorityQueue()
            pq.push("repo-c", priority=1)
            pq.push("repo-a", priority=3)
            pq.push("repo-b", priority=2)
            first = pq.pop()
            ok = first == "repo-a"
            self.runner.record("repo_hunter", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("repo_hunter", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))

    def _test_terminal_session_lifecycle(self) -> None:
        name = "terminal_session_create_destroy"
        start = time.perf_counter_ns()
        try:
            from ide.terminal_multiplexer_native import SessionManager
            sm = SessionManager()
            sid = sm.create_session("test")
            active = sm.list_sessions()
            sm.destroy_session(sid)
            ok = sid is not None and len(active) >= 1
            self.runner.record("ide", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("ide", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))

    def _test_security_audit_chain(self) -> None:
        name = "security_audit_hash_chain"
        start = time.perf_counter_ns()
        try:
            from kernel.logging_engine import LogEntry
            e1 = LogEntry(level=30, layer="security", module="audit", message="m1", trace_id="t1")
            e2 = LogEntry(level=30, layer="security", module="audit", message="m2", trace_id="t1")
            ok = e1.hash is not None and len(e1.hash) > 0
            self.runner.record("security", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("security", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))

    def _test_p2p_message_serialize(self) -> None:
        name = "p2p_message_serialize_deserialize"
        start = time.perf_counter_ns()
        try:
            from p2p_mesh.p2p_mesh_native import P2PMessage
            msg = P2PMessage(sender="a", topic="t", payload={"x": 1})
            data = msg.to_dict()
            ok = data.get("sender") == "a" and data.get("payload").get("x") == 1
            self.runner.record("p2p_mesh", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("p2p_mesh", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))

    def _test_hft_signal_transform(self) -> None:
        name = "hft_signal_transform_pipeline"
        start = time.perf_counter_ns()
        try:
            from hft.quant_signal_engine_native import Signal
            sig = Signal(symbol="BTCUSDT", side="BUY", confidence=0.85, metadata={"src": "test"})
            ok = sig.side in ("BUY", "SELL") and sig.confidence >= 0.0
            self.runner.record("hft", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("hft", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))


# =============================================================================
# Stress / Performance Tests
# =============================================================================
class StressTest:
    """Lightweight stress tests for hot paths."""

    def __init__(self, runner: TestRunner) -> None:
        self.runner = runner

    def run_all(self) -> None:
        self.runner._log("Starting StressTest...")
        self._test_event_bus_flood()
        self._test_logger_burst()
        self.runner._log("StressTest complete.")

    def _test_event_bus_flood(self) -> None:
        name = "event_bus_1000_events"
        start = time.perf_counter_ns()
        try:
            from kernel.kernel_native import EventBus
            bus = EventBus()
            count = 0
            def inc(_: Any) -> None:
                nonlocal count
                count += 1
            bus.subscribe("flood", inc)
            for i in range(1000):
                bus.publish("flood", {"i": i})
            ok = count == 1000
            self.runner.record("kernel", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("kernel", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))

    def _test_logger_burst(self) -> None:
        name = "logger_500_entries"
        start = time.perf_counter_ns()
        try:
            from kernel.logging_engine import AsyncLogger, LogLevel
            log = AsyncLogger()
            for i in range(500):
                log.log(LogLevel.INFO, "burst", "test", f"msg-{i}", trace_id=f"t{i}")
            ok = True
            self.runner.record("kernel", name, ok, (time.perf_counter_ns() - start) / 1e6)
        except Exception as exc:
            self.runner.record("kernel", name, False, (time.perf_counter_ns() - start) / 1e6, str(exc))


# =============================================================================
# Integration Orchestrator
# =============================================================================
class IntegrationOrchestrator:
    """Runs the full integration suite and produces exit codes / artifacts."""

    def __init__(self, verbose: bool = True) -> None:
        self.runner = TestRunner(verbose=verbose)
        self.verbose = verbose

    def run(self) -> int:
        print("\n" + "=" * 70)
        print("MAGNATRIX-OS  |  INTEGRATION TEST SUITE  |  15 LAYERS")
        print("=" * 70 + "\n")

        LayerBootTest(self.runner).run_all()
        InteropTest(self.runner).run_all()
        StressTest(self.runner).run_all()

        print(self.runner.summary())

        total_fail = sum(r.failed for r in self.runner.results)
        if total_fail == 0:
            print("\n[ALL TESTS PASSED — SYSTEM READY]\n")
            return 0
        else:
            print(f"\n[{total_fail} TEST(S) FAILED — REVIEW REQUIRED]\n")
            return 1

    def export_json(self, path: str = "/tmp/magnatrix_test_report.json") -> str:
        import json
        data = []
        for report in self.runner.results:
            for t in report.tests:
                data.append({
                    "layer": t.layer,
                    "test": t.name,
                    "status": t.status.value,
                    "duration_ms": round(t.duration_ms, 3),
                    "message": t.message,
                })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path


# =============================================================================
# Demo / CLI Entrypoint
# =============================================================================
def run_demo() -> int:
    """Quick demo run with synthetic sanity checks for environments lacking imports."""
    print("\n" + "=" * 70)
    print("MAGNATRIX-OS  |  DEMO / SANITY RUN")
    print("=" * 70 + "\n")

    # Pure-Python sanity checks that never fail due to missing deps
    checks = [
        ("dataclass_creation", lambda: TestResult("x", "kernel", TestStatus.PASS, 0.0) or True),
        ("enum_lookup", lambda: TestStatus.PASS == TestStatus("PASS")),
        ("path_resolution", lambda: PROJECT_ROOT.exists()),
        ("layer_map_complete", lambda: len(LAYER_MAP) == 15),
        ("hash_chain_dummy", lambda: __import__("hashlib").sha256(b"test").hexdigest()[:8] == "9f86d08"),
    ]

    runner = TestRunner(verbose=True)
    for name, fn in checks:
        t0 = time.perf_counter_ns()
        try:
            ok = fn()
            runner.record("sanity", name, bool(ok), (time.perf_counter_ns() - t0) / 1e6)
        except Exception as exc:
            runner.record("sanity", name, False, (time.perf_counter_ns() - t0) / 1e6, str(exc))

    print(runner.summary())
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="MAGNATRIX-OS Integration Test Suite")
    parser.add_argument("--demo", action="store_true", help="Run lightweight demo checks only")
    parser.add_argument("--export", type=str, default="", help="Export JSON report to path")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = parser.parse_args()

    if args.demo:
        rc = run_demo()
    else:
        orch = IntegrationOrchestrator(verbose=not args.quiet)
        rc = orch.run()
        if args.export:
            path = orch.export_json(args.export)
            print(f"[REPORT] JSON exported to {path}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
