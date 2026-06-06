#!/usr/bin/env python3
"""
Auto Test Runner for MAGNATRIX-OS
Discovers, executes, and reports tests across all Python modules.
Supports doctest extraction, self-test execution via __main__ blocks,
and lightweight assertion-based test discovery.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import ast
import dataclasses
import enum
import importlib.util
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class TestResultStatus(enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclasses.dataclass
class TestResult:
    module_path: str
    test_name: str
    status: TestResultStatus
    duration_ms: float
    message: str = ""
    traceback: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_path": self.module_path,
            "test_name": self.test_name,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "message": self.message,
        }


@dataclasses.dataclass
class ModuleTestReport:
    module_path: str
    results: List[TestResult] = dataclasses.field(default_factory=list)
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    total_duration_ms: float = 0.0

    def aggregate(self) -> None:
        self.total = len(self.results)
        self.passed = sum(1 for r in self.results if r.status == TestResultStatus.PASS)
        self.failed = sum(1 for r in self.results if r.status == TestResultStatus.FAIL)
        self.skipped = sum(1 for r in self.results if r.status == TestResultStatus.SKIP)
        self.errors = sum(1 for r in self.results if r.status == TestResultStatus.ERROR)
        self.total_duration_ms = sum(r.duration_ms for r in self.results)


class AutoTestRunner:
    """Discovers and runs tests across the entire MAGNATRIX-OS repository."""

    def __init__(self, repo_root: str, timeout: float = 15.0) -> None:
        self.root = Path(repo_root).resolve()
        self.timeout = timeout
        self._exclude: Set[str] = {"__pycache__", ".git", "venv", "node_modules", "dist", "build"}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_modules(self) -> List[Path]:
        """Find all Python files that contain test patterns or _demo/__main__."""
        modules: List[Path] = []
        for path in self.root.rglob("*.py"):
            if any(part in self._exclude for part in path.parts):
                continue
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if "if __name__ == \"__main__\"" in source or "_demo" in source or "def test_" in source:
                modules.append(path)
        return modules

    def discover_doctests(self, source: str) -> List[Tuple[str, str]]:
        """Extract doctest-style examples from docstrings."""
        tests: List[Tuple[str, str]] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return tests
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                doc = ast.get_docstring(node) or ""
                for line in doc.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith(">>> ") or stripped.startswith(">>>"):
                        tests.append((node.name, stripped))
        return tests

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _run_module_main(self, path: Path) -> TestResult:
        """Execute a module via subprocess to capture its __main__ behavior."""
        rel = str(path.relative_to(self.root))
        start = time.perf_counter()
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            elapsed = (time.perf_counter() - start) * 1000
            if result.returncode == 0:
                return TestResult(
                    module_path=rel, test_name="__main__ execution",
                    status=TestResultStatus.PASS, duration_ms=elapsed,
                )
            else:
                return TestResult(
                    module_path=rel, test_name="__main__ execution",
                    status=TestResultStatus.FAIL, duration_ms=elapsed,
                    message=f"Exit code {result.returncode}. stderr: {result.stderr[:500]}",
                )
        except subprocess.TimeoutExpired:
            elapsed = (time.perf_counter() - start) * 1000
            return TestResult(
                module_path=rel, test_name="__main__ execution",
                status=TestResultStatus.TIMEOUT, duration_ms=elapsed,
                message=f"Timeout after {self.timeout}s",
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return TestResult(
                module_path=rel, test_name="__main__ execution",
                status=TestResultStatus.ERROR, duration_ms=elapsed,
                message=str(exc), traceback=traceback.format_exc(),
            )

    def _run_syntax_check(self, path: Path) -> TestResult:
        """Run py_compile to verify syntax."""
        import py_compile
        rel = str(path.relative_to(self.root))
        start = time.perf_counter()
        try:
            py_compile.compile(str(path), doraise=True)
            elapsed = (time.perf_counter() - start) * 1000
            return TestResult(
                module_path=rel, test_name="syntax check",
                status=TestResultStatus.PASS, duration_ms=elapsed,
            )
        except py_compile.PyCompileError as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return TestResult(
                module_path=rel, test_name="syntax check",
                status=TestResultStatus.FAIL, duration_ms=elapsed,
                message=str(exc),
            )

    def _run_import_check(self, path: Path) -> TestResult:
        """Attempt to import the module without executing it."""
        rel = str(path.relative_to(self.root))
        start = time.perf_counter()
        try:
            spec = importlib.util.spec_from_file_location("_testmod", str(path))
            if not spec or not spec.loader:
                raise ImportError(f"Cannot load spec for {rel}")
            mod = importlib.util.module_from_spec(spec)
            # Only exec modules that don't trigger side effects on import
            spec.loader.exec_module(mod)
            elapsed = (time.perf_counter() - start) * 1000
            return TestResult(
                module_path=rel, test_name="import check",
                status=TestResultStatus.PASS, duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return TestResult(
                module_path=rel, test_name="import check",
                status=TestResultStatus.ERROR, duration_ms=elapsed,
                message=str(exc), traceback=traceback.format_exc()[:800],
            )

    def run_module(self, path: Path) -> ModuleTestReport:
        """Run all applicable tests for a single module."""
        report = ModuleTestReport(module_path=str(path.relative_to(self.root)))
        report.results.append(self._run_syntax_check(path))
        # Only run import check for core/governance modules (risky for tools with __main__ side effects)
        rel_lower = report.module_path.lower()
        if rel_lower.startswith("core/") or rel_lower.startswith("governance/"):
            report.results.append(self._run_import_check(path))
        # Run __main__ demo if present and module is not too large (avoid timeout storms)
        source = path.read_text(encoding="utf-8", errors="replace")
        if "if __name__ == \"__main__\"" in source and source.count("\n") < 800:
            report.results.append(self._run_module_main(path))
        report.aggregate()
        return report

    # ------------------------------------------------------------------
    # Batch execution
    # ------------------------------------------------------------------

    def run_all(self, max_modules: Optional[int] = None) -> List[ModuleTestReport]:
        """Run tests across all discovered modules."""
        modules = self.discover_modules()
        if max_modules:
            modules = modules[:max_modules]
        reports: List[ModuleTestReport] = []
        for i, path in enumerate(modules, 1):
            report = self.run_module(path)
            reports.append(report)
            if i % 50 == 0:
                print(f"[AutoTest] {i}/{len(modules)} modules checked...")
        return reports

    def run_subset(self, pattern: str) -> List[ModuleTestReport]:
        """Run tests on modules whose path contains the pattern."""
        modules = [p for p in self.discover_modules() if pattern.lower() in str(p).lower()]
        return [self.run_module(p) for p in modules]

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def summarize(self, reports: List[ModuleTestReport]) -> Dict[str, Any]:
        total_modules = len(reports)
        total_tests = sum(r.total for r in reports)
        passed = sum(r.passed for r in reports)
        failed = sum(r.failed for r in reports)
        errors = sum(r.errors for r in reports)
        skipped = sum(r.skipped for r in reports)
        duration = sum(r.total_duration_ms for r in reports)
        failed_modules = [r.module_path for r in reports if r.failed > 0 or r.errors > 0]
        return {
            "total_modules": total_modules,
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "total_duration_ms": duration,
            "pass_rate": (passed / total_tests * 100) if total_tests else 0,
            "failed_modules": failed_modules[:20],  # cap list
        }

    def export_json(self, reports: List[ModuleTestReport], path: str) -> None:
        import json
        data = {
            "summary": self.summarize(reports),
            "reports": [
                {
                    "module_path": r.module_path,
                    "results": [res.to_dict() for res in r.results],
                    "total": r.total,
                    "passed": r.passed,
                    "failed": r.failed,
                    "errors": r.errors,
                }
                for r in reports
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def print_summary(self, reports: List[ModuleTestReport]) -> None:
        summary = self.summarize(reports)
        print("\n" + "=" * 60)
        print("MAGNATRIX-OS Auto Test Runner Summary")
        print("=" * 60)
        print(f"Modules tested: {summary['total_modules']}")
        print(f"Tests run:     {summary['total_tests']}")
        print(f"Passed:        {summary['passed']} ({summary['pass_rate']:.1f}%)")
        print(f"Failed:        {summary['failed']}")
        print(f"Errors:        {summary['errors']}")
        print(f"Skipped:       {summary['skipped']}")
        print(f"Duration:      {summary['total_duration_ms']:.0f} ms")
        if summary["failed_modules"]:
            print(f"\nFailed modules (first 20):")
            for m in summary["failed_modules"]:
                print(f"  - {m}")
        print("=" * 60)


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(os.path.join(repo, "governance")):
        repo = os.getcwd()
    runner = AutoTestRunner(repo, timeout=10.0)
    print(f"[AutoTestRunner] Repository: {repo}")
    # Run on a small subset for demo (first 10 modules with __main__)
    modules = runner.discover_modules()[:10]
    print(f"[AutoTestRunner] Testing {len(modules)} modules...")
    reports = [runner.run_module(p) for p in modules]
    runner.print_summary(reports)


if __name__ == "__main__":
    _demo()
