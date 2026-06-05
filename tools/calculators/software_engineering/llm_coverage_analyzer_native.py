"""Coverage Analyzer — line/branch coverage tracking, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Callable
from enum import Enum, auto
import inspect
import ast

class CoverageType(Enum):
    LINE = auto()
    BRANCH = auto()
    FUNCTION = auto()

@dataclass
class CoverageReport:
    target_name: str
    lines_total: int
    lines_covered: Set[int]
    branches_total: int
    branches_covered: int
    functions_total: int
    functions_covered: int

class CoverageAnalyzer:
    def __init__(self):
        self.targets: Dict[str, Dict] = {}
        self.covered_lines: Dict[str, Set[int]] = {}
        self.covered_branches: Dict[str, Set[int]] = {}
        self.covered_functions: Dict[str, Set[str]] = {}

    def register(self, name: str, source_code: str):
        try:
            tree = ast.parse(source_code)
            lines = set()
            branches = 0
            functions = set()
            for node in ast.walk(tree):
                if hasattr(node, 'lineno'):
                    lines.add(node.lineno)
                if isinstance(node, (ast.If, ast.While, ast.For)):
                    branches += 1
                if isinstance(node, ast.FunctionDef):
                    functions.add(node.name)
            self.targets[name] = {"lines": lines, "branches": branches, "functions": functions}
            self.covered_lines[name] = set()
            self.covered_branches[name] = set()
            self.covered_functions[name] = set()
        except:
            pass

    def cover_line(self, target: str, line: int):
        if target in self.covered_lines:
            self.covered_lines[target].add(line)

    def cover_branch(self, target: str, branch_id: int):
        if target in self.covered_branches:
            self.covered_branches[target].add(branch_id)

    def cover_function(self, target: str, func_name: str):
        if target in self.covered_functions:
            self.covered_functions[target].add(func_name)

    def report(self, target: Optional[str] = None) -> List[CoverageReport]:
        reports = []
        for name in self.targets if target is None else ([target] if target in self.targets else []):
            t = self.targets[name]
            reports.append(CoverageReport(
                name, len(t["lines"]), self.covered_lines[name],
                t["branches"], len(self.covered_branches[name]),
                len(t["functions"]), len(self.covered_functions[name])
            ))
        return reports

    def line_coverage(self, target: str) -> float:
        t = self.targets.get(target)
        if not t or not t["lines"]:
            return 0.0
        return len(self.covered_lines[target]) / len(t["lines"])

    def stats(self) -> Dict:
        total_lines = sum(len(t["lines"]) for t in self.targets.values())
        covered_lines = sum(len(self.covered_lines.get(k, set())) for k in self.targets)
        return {"targets": len(self.targets), "line_coverage": covered_lines / total_lines if total_lines else 0, "total_lines": total_lines, "covered_lines": covered_lines}

def run():
    analyzer = CoverageAnalyzer()
    code = """
def foo(x):
    if x > 0:
        return x
    else:
        return -x
"""
    analyzer.register("module1", code)
    analyzer.cover_line("module1", 2)
    analyzer.cover_line("module1", 3)
    analyzer.cover_function("module1", "foo")
    print(analyzer.report("module1")[0])
    print(analyzer.stats())

if __name__ == "__main__":
    run()
