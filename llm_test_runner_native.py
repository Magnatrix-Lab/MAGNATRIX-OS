"""Test Runner Engine — unit test execution, assertions, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Any
from enum import Enum, auto
import time
import traceback

class TestResult(Enum):
    PASS = auto()
    FAIL = auto()
    SKIP = auto()
    ERROR = auto()

@dataclass
class TestCase:
    test_id: str
    name: str
    func: Callable
    result: TestResult = TestResult.SKIP
    duration_ms: float = 0.0
    error_message: str = ""

class TestRunner:
    def __init__(self):
        self.tests: List[TestCase] = []
        self.setup_fn: Optional[Callable] = None
        self.teardown_fn: Optional[Callable] = None
        self.results: List[TestCase] = []

    def add_test(self, test_id: str, name: str, func: Callable):
        self.tests.append(TestCase(test_id, name, func))

    def set_setup(self, func: Callable):
        self.setup_fn = func

    def set_teardown(self, func: Callable):
        self.teardown_fn = func

    def run(self, test_id: Optional[str] = None) -> List[TestCase]:
        to_run = [t for t in self.tests if test_id is None or t.test_id == test_id]
        for t in to_run:
            start = time.time()
            try:
                if self.setup_fn:
                    self.setup_fn()
                t.func()
                t.result = TestResult.PASS
                t.duration_ms = (time.time() - start) * 1000
            except AssertionError as e:
                t.result = TestResult.FAIL
                t.duration_ms = (time.time() - start) * 1000
                t.error_message = str(e)
            except Exception as e:
                t.result = TestResult.ERROR
                t.duration_ms = (time.time() - start) * 1000
                t.error_message = traceback.format_exc()
            finally:
                if self.teardown_fn:
                    try:
                        self.teardown_fn()
                    except:
                        pass
            self.results.append(t)
        return self.results

    def assert_equal(self, a: Any, b: Any, msg: str = ""):
        if a != b:
            raise AssertionError(f"{msg} Expected {b}, got {a}")

    def assert_true(self, a: bool, msg: str = ""):
        if not a:
            raise AssertionError(msg)

    def assert_in(self, a: Any, b: list, msg: str = ""):
        if a not in b:
            raise AssertionError(f"{msg} {a} not in {b}")

    def summary(self) -> Dict:
        counts = {}
        for r in self.results:
            counts[r.result.name] = counts.get(r.result.name, 0) + 1
        return {"total": len(self.results), **counts, "duration_ms": sum(r.duration_ms for r in self.results)}

    def stats(self) -> Dict:
        return self.summary()

def run():
    runner = TestRunner()
    def test_pass():
        runner.assert_equal(1 + 1, 2)
    def test_fail():
        runner.assert_equal(1 + 1, 3)
    runner.add_test("t1", "addition", test_pass)
    runner.add_test("t2", "wrong", test_fail)
    runner.run()
    print(runner.summary())

if __name__ == "__main__":
    run()
