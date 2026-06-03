"""Hypothesis Tester - Statistical tests for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from enum import Enum, auto
import math

class TestType(Enum):
    TTEST = auto(); ZTEST = auto(); CHISQ = auto()

@dataclass
class HypothesisTester:
    test_type: TestType = TestType.TTEST
    alpha: float = 0.05

    def t_test(self, sample: List[float], pop_mean: float) -> float:
        n = len(sample); mean = sum(sample)/n
        var = sum((x-mean)**2 for x in sample)/(n-1) if n > 1 else 0
        se = math.sqrt(var/n) if n > 0 else 0
        return (mean - pop_mean) / se if se > 0 else 0

    def z_test(self, sample: List[float], pop_mean: float, pop_std: float) -> float:
        n = len(sample); mean = sum(sample)/n
        return (mean - pop_mean) / (pop_std / math.sqrt(n)) if pop_std > 0 and n > 0 else 0

    def chi_square(self, observed: List[int], expected: List[float]) -> float:
        return sum((o-e)**2/e for o, e in zip(observed, expected) if e > 0)

    def test(self, *args) -> float:
        if self.test_type == TestType.TTEST: return self.t_test(args[0], args[1])
        if self.test_type == TestType.ZTEST: return self.z_test(args[0], args[1], args[2])
        if self.test_type == TestType.CHISQ: return self.chi_square(args[0], args[1])
        return 0.0

    def stats(self, *args) -> dict:
        return {"test": self.test_type.name, "statistic": round(self.test(*args), 4), "alpha": self.alpha}

def run():
    ht = HypothesisTester(TestType.TTEST)
    sample = [1.2, 2.3, 1.9, 2.1, 2.5]
    print("t-stat:", round(ht.test(sample, 2.0), 4))
    print("Stats:", ht.stats(sample, 2.0))

if __name__ == "__main__": run()
