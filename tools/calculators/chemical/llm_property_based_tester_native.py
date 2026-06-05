"""Property-Based Testing — invariants, generators, shrinking, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Any, Tuple
from enum import Enum, auto
import random
import string

class PropertyResult(Enum):
    PASS = auto()
    FAIL = auto()
    SKIP = auto()

@dataclass
class PropertyTest:
    test_id: str
    name: str
    property_fn: Callable
    generator: Callable
    shrinker: Optional[Callable] = None
    result: PropertyResult = PropertyResult.SKIP
    counterexample: Any = None
    iterations: int = 100

class PropertyBasedTester:
    def __init__(self, default_iterations: int = 100):
        self.default_iterations = default_iterations
        self.tests: List[PropertyTest] = []
        self.results: List[PropertyTest] = []

    def add_property(self, test_id: str, name: str, property_fn: Callable, generator: Callable, shrinker: Optional[Callable] = None, iterations: int = None):
        self.tests.append(PropertyTest(test_id, name, property_fn, generator, shrinker, iterations=iterations or self.default_iterations))

    def int_generator(self, min_val: int = -1000, max_val: int = 1000) -> int:
        return random.randint(min_val, max_val)

    def string_generator(self, min_len: int = 0, max_len: int = 20) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=random.randint(min_len, max_len)))

    def list_generator(self, element_generator: Callable, min_len: int = 0, max_len: int = 10) -> list:
        return [element_generator() for _ in range(random.randint(min_len, max_len))]

    def run(self, test_id: Optional[str] = None) -> List[PropertyTest]:
        to_run = [t for t in self.tests if test_id is None or t.test_id == test_id]
        for t in to_run:
            t.result = PropertyResult.PASS
            for i in range(t.iterations):
                input_data = t.generator()
                try:
                    if not t.property_fn(input_data):
                        t.result = PropertyResult.FAIL
                        t.counterexample = input_data
                        if t.shrinker:
                            t.counterexample = t.shrinker(input_data)
                        break
                except Exception as e:
                    t.result = PropertyResult.FAIL
                    t.counterexample = input_data
                    break
            self.results.append(t)
        return self.results

    def shrink_int(self, value: int) -> int:
        return value // 2

    def shrink_list(self, value: list) -> list:
        return value[:max(len(value) // 2, 1)]

    def stats(self) -> Dict:
        counts = {}
        for r in self.results:
            counts[r.result.name] = counts.get(r.result.name, 0) + 1
        return {"total": len(self.results), **counts, "failed_with_counterexample": sum(1 for r in self.results if r.counterexample is not None)}

def run():
    tester = PropertyBasedTester(50)
    tester.add_property("p1", "reverse twice", lambda x: x == x[::-1][::-1], lambda: tester.list_generator(lambda: tester.int_generator(), 0, 10))
    tester.add_property("p2", "addition commutative", lambda x: x[0] + x[1] == x[1] + x[0], lambda: [tester.int_generator(), tester.int_generator()])
    tester.run()
    print(tester.stats())

if __name__ == "__main__":
    run()
