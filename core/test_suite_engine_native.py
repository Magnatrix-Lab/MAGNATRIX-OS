#!/usr/bin/env python3
"""
Test Suite Engine — MAGNATRIX-OS Comprehensive Test Framework
============================================================
Test runner, module contract tests, integration tests, coverage reporter,
regression guard. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


@dataclass
class TestResult:
    """Result of a single test case."""
    name: str
    module: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    stack_trace: Optional[str] = None


@dataclass
class TestSuiteResult:
    """Result of a test suite run."""
    suite_name: str
    tests: List[TestResult] = field(default_factory=list)
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    duration_ms: float = 0.0

    def add(self, result: TestResult) -> None:
        self.tests.append(result)
        self.total += 1
        if result.passed:
            self.passed += 1
        elif result.error and "error" in result.error.lower():
            self.errors += 1
        else:
            self.failed += 1


class TestRunner:
    """
    Core test discovery and execution.
    
    Discovers modules, runs tests, tracks results.
    """

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
        self._results: List[TestSuiteResult] = []
        self._lock = threading.Lock()

    def discover(self, module_glob: str = "core/*_native.py") -> List[str]:
        """Discover testable modules."""
        core_dir = Path(self.repo_root) / "core"
        if not core_dir.exists():
            return []
        files = list(core_dir.glob("*_native.py"))
        return [f.stem for f in files]

    def run(self, test_cases: List[Callable[[], Any]], suite_name: str = "suite") -> TestSuiteResult:
        """Run a list of test cases."""
        result = TestSuiteResult(suite_name=suite_name)
        start = time.time()
        for test_fn in test_cases:
            name = getattr(test_fn, "__name__", str(test_fn))
            t0 = time.time()
            try:
                test_fn()
                result.add(TestResult(name=name, module=suite_name, passed=True, duration_ms=(time.time()-t0)*1000))
            except AssertionError as e:
                result.add(TestResult(name=name, module=suite_name, passed=False, duration_ms=(time.time()-t0)*1000, error=str(e), stack_trace=traceback.format_exc()))
            except Exception as e:
                result.add(TestResult(name=name, module=suite_name, passed=False, duration_ms=(time.time()-t0)*1000, error=str(e), stack_trace=traceback.format_exc()))
        result.duration_ms = (time.time() - start) * 1000
        with self._lock:
            self._results.append(result)
        return result

    def run_module(self, module_name: str) -> TestSuiteResult:
        """Run tests for a specific module."""
        suite = ModuleTestCase(module_name, self.repo_root)
        return suite.run_all()

    def run_all(self, modules: Optional[List[str]] = None) -> List[TestSuiteResult]:
        """Run tests for all discovered modules."""
        if modules is None:
            modules = self.discover()
        results = []
        for mod in modules:
            result = self.run_module(mod)
            results.append(result)
        return results

    def get_results(self) -> List[TestSuiteResult]:
        with self._lock:
            return list(self._results)

    def generate_report(self, results: Optional[List[TestSuiteResult]] = None) -> str:
        """Generate a text report."""
        if results is None:
            results = self._results
        lines = ["=" * 60, "MAGNATRIX-OS Test Report", "=" * 60, ""]
        total_tests = 0
        total_passed = 0
        total_failed = 0
        for suite in results:
            lines.append(f"Suite: {suite.suite_name}")
            lines.append(f"  Total: {suite.total} | Passed: {suite.passed} | Failed: {suite.failed} | Errors: {suite.errors}")
            lines.append(f"  Duration: {suite.duration_ms:.1f}ms")
            for test in suite.tests:
                status = "PASS" if test.passed else "FAIL"
                lines.append(f"    [{status}] {test.name} ({test.duration_ms:.1f}ms)")
                if test.error:
                    lines.append(f"      Error: {test.error}")
            lines.append("")
            total_tests += suite.total
            total_passed += suite.passed
            total_failed += suite.failed + suite.errors
        lines.append("-" * 60)
        lines.append(f"OVERALL: {total_tests} tests, {total_passed} passed, {total_failed} failed")
        lines.append(f"Success rate: {(total_passed/total_tests*100) if total_tests > 0 else 0:.1f}%")
        return "\n".join(lines)


class ModuleTestCase:
    """
    Contract tests for individual modules.
    
    Tests: can_load, can_instantiate, methods_exist, returns_expected_types.
    """

    def __init__(self, module_name: str, repo_root: str = "."):
        self.module_name = module_name
        self.repo_root = repo_root
        self._instance: Optional[Any] = None
        self._module: Optional[Any] = None

    def _load(self) -> Any:
        """Load the module."""
        import_path = f"core.{self.module_name}"
        try:
            self._module = importlib.import_module(import_path)
            return self._module
        except Exception as e:
            raise ImportError(f"Cannot load {import_path}: {e}")

    def _find_class(self) -> type:
        """Find the main class in the module."""
        if not self._module:
            self._load()
        # Find the first class with the right naming convention
        candidates = []
        for name in dir(self._module):
            obj = getattr(self._module, name)
            if isinstance(obj, type) and not name.startswith("_") and name not in ("dataclass", "Enum", "field"):
                candidates.append(obj)
        if not candidates:
            raise ValueError(f"No class found in {self.module_name}")
        # Prefer class with name matching module
        for c in candidates:
            # Map module name to expected class name
            expected = self._module_to_class(self.module_name)
            if c.__name__ == expected or c.__name__.lower() == expected.lower():
                return c
        return candidates[0]

    def _module_to_class(self, module_name: str) -> str:
        """Convert module name to expected class name."""
        parts = module_name.replace("_native", "").split("_")
        return "".join(p.capitalize() for p in parts if p)

    def _instantiate(self, cls: type) -> Any:
        """Instantiate the class with safe defaults."""
        try:
            sig = inspect.signature(cls.__init__)
            kwargs = {}
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                if param_name in ("repo_root", "root"):
                    kwargs[param_name] = self.repo_root
                elif param_name in ("store_dir", "data_dir"):
                    kwargs[param_name] = os.path.join(self.repo_root, "data")
                elif param.default is not inspect.Parameter.empty:
                    kwargs[param_name] = param.default
                else:
                    kwargs[param_name] = None
            return cls(**kwargs)
        except Exception as e:
            # Try no args
            try:
                return cls()
            except Exception:
                raise RuntimeError(f"Cannot instantiate {cls.__name__}: {e}")

    def test_load(self) -> None:
        """Test that module can be loaded."""
        self._load()
        assert self._module is not None, "Module not loaded"

    def test_instantiate(self) -> None:
        """Test that class can be instantiated."""
        cls = self._find_class()
        self._instance = self._instantiate(cls)
        assert self._instance is not None, "Instance not created"

    def test_methods(self) -> None:
        """Test that expected methods exist."""
        if not self._instance:
            cls = self._find_class()
            self._instance = self._instantiate(cls)
        expected_methods = ["handle_message", "on_event"]
        for method in expected_methods:
            assert hasattr(self._instance, method), f"Missing method: {method}"
            assert callable(getattr(self._instance, method)), f"Not callable: {method}"

    def test_integrity(self) -> None:
        """Test module integrity: no import errors, classes exist."""
        module = self._load()
        classes = [name for name in dir(module) if isinstance(getattr(module, name), type)]
        assert len(classes) > 0, "No classes found in module"

    def run_all(self) -> TestSuiteResult:
        """Run all tests for this module."""
        result = TestSuiteResult(suite_name=self.module_name)
        tests = [self.test_load, self.test_instantiate, self.test_methods, self.test_integrity]
        for test_fn in tests:
            t0 = time.time()
            try:
                test_fn()
                result.add(TestResult(name=test_fn.__name__, module=self.module_name, passed=True, duration_ms=(time.time()-t0)*1000))
            except Exception as e:
                result.add(TestResult(name=test_fn.__name__, module=self.module_name, passed=False, duration_ms=(time.time()-t0)*1000, error=str(e), stack_trace=traceback.format_exc()))
        return result


class IntegrationTestSuite:
    """
    Cross-module integration tests.
    """

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root

    def test_event_bus_wiring(self) -> None:
        """Test that EventBus can be instantiated and wired."""
        from core.integration_layer_native import EventBus, ModuleConnector, MessageRouter
        bus = EventBus()
        router = MessageRouter()
        connector = ModuleConnector(bus, router)
        assert bus is not None
        assert router is not None
        assert connector is not None

    def test_module_interaction(self) -> None:
        """Test that modules can send messages to each other."""
        from core.integration_layer_native import MessageRouter
        router = MessageRouter()
        def handler(msg):
            return {"received": True}
        router.register_handler("test", handler)
        result = router.send("test", {"action": "ping"})
        assert result is not None
        assert result.get("received") is True

    def test_data_flow(self) -> None:
        """Test data flow through the system."""
        from core.integration_layer_native import EventBus
        bus = EventBus()
        received = []
        def handler(event):
            received.append(event.topic)
        bus.subscribe("test.flow", handler)
        bus.publish("test.flow", {"data": 123})
        assert len(received) > 0

    def test_error_propagation(self) -> None:
        """Test that errors don't crash the system."""
        from core.integration_layer_native import EventBus
        bus = EventBus()
        def bad_handler(event):
            raise ValueError("Test error")
        def good_handler(event):
            return True
        bus.subscribe("test.error", bad_handler)
        bus.subscribe("test.error", good_handler)
        bus.publish("test.error", {})  # Should not crash

    def run_all(self) -> TestSuiteResult:
        result = TestSuiteResult(suite_name="integration")
        tests = [self.test_event_bus_wiring, self.test_module_interaction, self.test_data_flow, self.test_error_propagation]
        for test_fn in tests:
            t0 = time.time()
            try:
                test_fn()
                result.add(TestResult(name=test_fn.__name__, module="integration", passed=True, duration_ms=(time.time()-t0)*1000))
            except Exception as e:
                result.add(TestResult(name=test_fn.__name__, module="integration", passed=False, duration_ms=(time.time()-t0)*1000, error=str(e), stack_trace=traceback.format_exc()))
        return result


class CoverageReporter:
    """
    Line-level coverage tracking using sys.settrace.
    """

    def __init__(self):
        self._coverage: Dict[str, set] = {}  # file -> set of executed lines
        self._started = False

    def start(self) -> None:
        """Start coverage tracking."""
        self._coverage = {}
        self._started = True
        sys.settrace(self._trace)

    def stop(self) -> None:
        """Stop coverage tracking."""
        sys.settrace(None)
        self._started = False

    def _trace(self, frame, event, arg):
        if not self._started:
            return None
        filename = frame.f_code.co_filename
        if "MAGNATRIX-OS" in filename and filename.endswith(".py"):
            if filename not in self._coverage:
                self._coverage[filename] = set()
            if event == "line":
                self._coverage[filename].add(frame.f_lineno)
        return self._trace

    def report(self) -> Dict[str, Any]:
        """Generate coverage report."""
        report = {}
        total_lines = 0
        covered_lines = 0
        for filename, lines in self._coverage.items():
            try:
                with open(filename) as f:
                    file_lines = f.readlines()
                total = len(file_lines)
                covered = len(lines)
                total_lines += total
                covered_lines += covered
                report[filename] = {
                    "total_lines": total,
                    "covered_lines": covered,
                    "coverage_pct": (covered / total * 100) if total > 0 else 0,
                }
            except Exception:
                pass
        overall_pct = (covered_lines / total_lines * 100) if total_lines > 0 else 0
        return {
            "overall_coverage": overall_pct,
            "files": report,
        }

    def html_report(self) -> str:
        """Generate HTML coverage report."""
        report = self.report()
        lines = [
            "<!DOCTYPE html><html><head><title>MAGNATRIX-OS Coverage</title>",
            "<style>body{font-family:monospace;background:#1a1a2e;color:#eee;padding:20px}",
            ".file{margin:10px 0;padding:10px;background:#16213e;border-radius:4px}",
            ".pct{font-weight:bold;color:#4CAF50}</style></head><body>",
            f"<h1>MAGNATRIX-OS Coverage: {report['overall_coverage']:.1f}%</h1>",
        ]
        for filename, data in report.get("files", {}).items():
            short = filename.split("/")[-1]
            lines.append(f'<div class="file">{short}: <span class="pct">{data["coverage_pct"]:.1f}%</span> ({data["covered_lines"]}/{data["total_lines"]})</div>')
        lines.append("</body></html>")
        return "\n".join(lines)


class RegressionGuard:
    """
    Compare test results against baseline.
    """

    def __init__(self, baseline_dir: str = "data/baselines"):
        self.baseline_dir = baseline_dir

    def save_baseline(self, results: List[TestSuiteResult], name: str = "baseline") -> str:
        """Save current results as baseline."""
        os.makedirs(self.baseline_dir, exist_ok=True)
        path = os.path.join(self.baseline_dir, f"{name}.json")
        data = {
            "timestamp": time.time(),
            "suites": [
                {
                    "name": s.suite_name,
                    "total": s.total,
                    "passed": s.passed,
                    "failed": s.failed,
                }
                for s in results
            ]
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path

    def compare_baseline(self, results: List[TestSuiteResult], name: str = "baseline") -> Dict[str, Any]:
        """Compare current results against baseline."""
        path = os.path.join(self.baseline_dir, f"{name}.json")
        if not os.path.exists(path):
            return {"error": "Baseline not found"}
        with open(path) as f:
            baseline = json.load(f)
        
        drift = []
        for suite in results:
            baseline_suite = next((s for s in baseline.get("suites", []) if s["name"] == suite.suite_name), None)
            if baseline_suite:
                if suite.passed < baseline_suite["passed"]:
                    drift.append({
                        "suite": suite.suite_name,
                        "type": "regression",
                        "before": baseline_suite["passed"],
                        "after": suite.passed,
                    })
                elif suite.passed > baseline_suite["passed"]:
                    drift.append({
                        "suite": suite.suite_name,
                        "type": "improvement",
                        "before": baseline_suite["passed"],
                        "after": suite.passed,
                    })
        return {"drift": drift, "regressions": len([d for d in drift if d["type"] == "regression"])}

    def report_drift(self, comparison: Dict[str, Any]) -> str:
        """Generate drift report."""
        if "error" in comparison:
            return comparison["error"]
        lines = ["Regression Report", "=" * 40]
        for d in comparison.get("drift", []):
            icon = "↓" if d["type"] == "regression" else "↑"
            lines.append(f"{icon} {d['suite']}: {d['before']} → {d['after']} ({d['type']})")
        lines.append(f"Total regressions: {comparison['regressions']}")
        return "\n".join(lines)


class TestSuiteEngine:
    """
    Top-level test orchestrator for MAGNATRIX-OS.
    """

    CAPABILITIES = ["testing", "quality", "coverage", "regression"]

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
        self._runner = TestRunner(repo_root)
        self._integration = IntegrationTestSuite(repo_root)
        self._coverage = CoverageReporter()
        self._regression = RegressionGuard(os.path.join(repo_root, "data", "baselines"))
        self._lock = threading.Lock()
        self._stats = {"runs": 0, "tests": 0, "passed": 0, "failed": 0}

    def run_all_tests(self, coverage: bool = False) -> Dict[str, Any]:
        """Run all unit and integration tests."""
        if coverage:
            self._coverage.start()

        unit_results = self._runner.run_all()
        integration_result = self._integration.run_all()

        if coverage:
            self._coverage.stop()

        all_results = unit_results + [integration_result]
        
        with self._lock:
            self._stats["runs"] += 1
            for r in all_results:
                self._stats["tests"] += r.total
                self._stats["passed"] += r.passed
                self._stats["failed"] += r.failed + r.errors

        return {
            "unit_tests": [{"name": r.suite_name, "total": r.total, "passed": r.passed, "failed": r.failed} for r in unit_results],
            "integration_tests": {"total": integration_result.total, "passed": integration_result.passed, "failed": integration_result.failed},
            "coverage": self._coverage.report() if coverage else None,
        }

    def run_unit_tests(self, modules: Optional[List[str]] = None) -> List[TestSuiteResult]:
        return self._runner.run_all(modules)

    def run_integration_tests(self) -> TestSuiteResult:
        return self._integration.run_all()

    def generate_report(self, results: Optional[List[TestSuiteResult]] = None) -> str:
        return self._runner.generate_report(results)

    def get_coverage(self) -> Dict[str, Any]:
        return self._coverage.report()

    def save_baseline(self, name: str = "baseline") -> str:
        results = self._runner.run_all()
        return self._regression.save_baseline(results, name)

    def compare_baseline(self, name: str = "baseline") -> Dict[str, Any]:
        results = self._runner.run_all()
        return self._regression.compare_baseline(results, name)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def handle_message(self, message: Dict[str, Any]) -> Any:
        action = message.get("action", "")
        if action == "run_all":
            return self.run_all_tests(message.get("coverage", False))
        elif action == "run_unit":
            return [{"name": r.suite_name, "total": r.total, "passed": r.passed} for r in self.run_unit_tests()]
        elif action == "run_integration":
            r = self.run_integration_tests()
            return {"total": r.total, "passed": r.passed, "failed": r.failed}
        elif action == "report":
            return self.generate_report()
        elif action == "coverage":
            return self.get_coverage()
        elif action == "save_baseline":
            return {"path": self.save_baseline(message.get("name", "baseline"))}
        elif action == "compare_baseline":
            return self.compare_baseline(message.get("name", "baseline"))
        elif action == "stats":
            return self.get_stats()
        return None

    def on_event(self, event) -> None:
        pass
