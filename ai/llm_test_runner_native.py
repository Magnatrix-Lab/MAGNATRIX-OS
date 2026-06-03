"""LLM Test Runner — Native Python (stdlib only)."""
from __future__ import annotations
import time, traceback
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class TestStatus(Enum):
    PASSED = auto()
    FAILED = auto()
    SKIPPED = auto()
    ERROR = auto()

@dataclass
class TestResult:
    id: str
    name: str
    status: TestStatus
    duration: float = 0.0
    message: str = ""
    traceback: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class TestRunner:
    def __init__(self) -> None:
        self._tests: Dict[str, Callable[[], None]] = {}
        self._results: List[TestResult] = []

    def add_test(self, test_id: str, name: str, test_fn: Callable[[], None]) -> None:
        self._tests[test_id] = (name, test_fn)

    def run(self, test_id: str) -> TestResult:
        name, test_fn = self._tests.get(test_id, ("unknown", lambda: None))
        start = time.time()
        try:
            test_fn()
            result = TestResult(test_id, name, TestStatus.PASSED, time.time() - start)
        except AssertionError as ex:
            result = TestResult(test_id, name, TestStatus.FAILED, time.time() - start, str(ex))
        except Exception as ex:
            result = TestResult(test_id, name, TestStatus.ERROR, time.time() - start, str(ex), traceback.format_exc())
        self._results.append(result)
        return result

    def run_all(self) -> List[TestResult]:
        for test_id in self._tests:
            self.run(test_id)
        return self._results

    def get_passed(self) -> List[TestResult]:
        return [r for r in self._results if r.status == TestStatus.PASSED]

    def get_failed(self) -> List[TestResult]:
        return [r for r in self._results if r.status in (TestStatus.FAILED, TestStatus.ERROR)]

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for r in self._results:
            counts[r.status.name] = counts.get(r.status.name, 0) + 1
        total = sum(r.duration for r in self._results)
        return {"total": len(self._results), "by_status": counts, "duration": total, "pass_rate": len(self.get_passed()) / len(self._results) if self._results else 0.0}

def run() -> None:
    print("Test Runner test")
    e = TestRunner()
    e.add_test("t1", "addition", lambda: assertEqual(1 + 1, 2))
    e.add_test("t2", "subtraction", lambda: assertEqual(5 - 3, 2))
    e.add_test("t3", "fail_test", lambda: assertEqual(1, 2))
    results = e.run_all()
    for r in results:
        print("  " + r.name + ": " + r.status.name + (" (" + r.message + ")" if r.message else ""))
    print("  Stats: " + str(e.get_stats()))
    print("Test Runner test complete.")

def assertEqual(a, b):
    if a != b:
        raise AssertionError(str(a) + " != " + str(b))

if __name__ == "__main__":
    run()
