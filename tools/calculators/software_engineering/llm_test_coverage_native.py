"""Native stdlib module: Test Coverage Analyzer
Calculates test coverage metrics by line, branch, and function coverage.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class TestCoverage:
    module_name: str
    total_lines: int
    covered_lines: int
    total_branches: int
    covered_branches: int
    total_functions: int
    covered_functions: int

    def line_coverage_pct(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return (self.covered_lines / self.total_lines) * 100

    def branch_coverage_pct(self) -> float:
        if self.total_branches == 0:
            return 0.0
        return (self.covered_branches / self.total_branches) * 100

    def function_coverage_pct(self) -> float:
        if self.total_functions == 0:
            return 0.0
        return (self.covered_functions / self.total_functions) * 100

    def overall_coverage(self) -> float:
        scores = [self.line_coverage_pct(), self.branch_coverage_pct(), self.function_coverage_pct()]
        return sum(scores) / len(scores)

    def stats(self) -> Dict[str, float]:
        return {
            "module": self.module_name,
            "line_coverage_pct": round(self.line_coverage_pct(), 1),
            "branch_coverage_pct": round(self.branch_coverage_pct(), 1),
            "function_coverage_pct": round(self.function_coverage_pct(), 1),
            "overall_coverage_pct": round(self.overall_coverage(), 1),
        }

def run():
    tc = TestCoverage(
        module_name="auth_service",
        total_lines=500,
        covered_lines=425,
        total_branches=80,
        covered_branches=60,
        total_functions=40,
        covered_functions=38
    )
    print(tc.stats())

if __name__ == "__main__":
    run()
