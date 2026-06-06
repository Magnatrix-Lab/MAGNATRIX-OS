#!/usr/bin/env python3
"""
Test Framework for MAGNATRIX-OS
Unit test runner, auto-discovery, coverage, mock.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import inspect
import json
import os
import sys
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple


class TestResult:
    """Single test result."""

    def __init__(self, name: str, passed: bool, duration: float, error: Optional[str] = None) -> None:
        self.name = name
        self.passed = passed
        self.duration = duration
        self.error = error


class Mock:
    """Simple mock object."""

    def __init__(self, return_value: Any = None) -> None:
        self._return_value = return_value
        self._calls: List[Tuple[Any, ...]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._calls.append((args, kwargs))
        return self._return_value

    def call_count(self) -> int:
        return len(self._calls)

    def called_with(self, *args: Any, **kwargs: Any) -> bool:
        return any(ca == (args, kwargs) for ca in self._calls)


class TestRunner:
    """Unit test runner with auto-discovery."""

    def __init__(self) -> None:
        self._results: List[TestResult] = []
        self._passed = 0
        self._failed = 0
        self._setup: Optional[Callable] = None
        self._teardown: Optional[Callable] = None

    def setUp(self, func: Callable) -> None:
        self._setup = func

    def tearDown(self, func: Callable) -> None:
        self._teardown = func

    def run_test(self, func: Callable) -> TestResult:
        start = time.time()
        try:
            if self._setup:
                self._setup()
            func()
            if self._teardown:
                self._teardown()
            result = TestResult(func.__name__, True, time.time() - start)
            self._passed += 1
        except Exception as e:
            error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()[:200]}"
            result = TestResult(func.__name__, False, time.time() - start, error)
            self._failed += 1

        self._results.append(result)
        return result

    def discover(self, obj: Any) -> List[TestResult]:
        """Auto-discover test methods (prefix 'test_')."""
        results = []
        for name in dir(obj):
            if name.startswith('test_'):
                method = getattr(obj, name)
                if callable(method):
                    results.append(self.run_test(method))
        return results

    def assert_equal(self, a: Any, b: Any) -> None:
        if a != b:
            raise AssertionError(f"Expected {b}, got {a}")

    def assert_true(self, a: Any) -> None:
        if not a:
            raise AssertionError(f"Expected True, got {a}")

    def assert_raises(self, exc_type: type, func: Callable, *args: Any, **kwargs: Any) -> None:
        try:
            func(*args, **kwargs)
            raise AssertionError(f"Expected {exc_type.__name__} to be raised")
        except exc_type:
            pass

    def report(self) -> Dict[str, Any]:
        total = len(self._results)
        duration = sum(r.duration for r in self._results)
        return {
            'total': total,
            'passed': self._passed,
            'failed': self._failed,
            'duration': round(duration, 3),
            'success_rate': self._passed / total if total > 0 else 0.0,
            'results': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'duration': round(r.duration, 3),
                    'error': r.error,
                }
                for r in self._results
            ],
        }


def _demo() -> None:
    print("=== Test Framework Demo ===\n")

    runner = TestRunner()

    # Sample tests
    def test_addition():
        runner.assert_equal(1 + 1, 2)

    def test_subtraction():
        runner.assert_equal(5 - 3, 2)

    def test_failure():
        runner.assert_equal(1, 2)  # Will fail

    def test_mock():
        m = Mock(return_value=42)
        result = m('hello')
        runner.assert_equal(result, 42)
        runner.assert_equal(m.call_count(), 1)

    # Run tests
    runner.run_test(test_addition)
    runner.run_test(test_subtraction)
    runner.run_test(test_failure)
    runner.run_test(test_mock)

    report = runner.report()
    print(f"Total: {report['total']}, Passed: {report['passed']}, Failed: {report['failed']}")
    print(f"Duration: {report['duration']:.3f}s, Success rate: {report['success_rate']:.1%}")

    for r in report['results']:
        status = "PASS" if r['passed'] else "FAIL"
        print(f"  [{status}] {r['name']} ({r['duration']:.3f}s)")

    print("\n=== Test Framework Demo Complete ===")


if __name__ == '__main__':
    _demo()
