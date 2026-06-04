"""Constraint Solver - CSP solver for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum, auto

@dataclass
class Constraint:
    variables: List[str]
    check: callable

@dataclass
class ConstraintSolver:
    variables: Dict[str, List[int]] = field(default_factory=dict)
    constraints: List[Constraint] = field(default_factory=list)
    assignment: Dict[str, int] = field(default_factory=dict)

    def add_variable(self, name: str, domain: List[int]) -> None:
        self.variables[name] = domain

    def add_constraint(self, constraint: Constraint) -> None:
        self.constraints.append(constraint)

    def solve(self) -> Optional[Dict[str, int]]:
        return self._backtrack({})

    def _backtrack(self, assignment: Dict[str, int]) -> Optional[Dict[str, int]]:
        if len(assignment) == len(self.variables): return assignment
        var = next(v for v in self.variables if v not in assignment)
        for value in self.variables[var]:
            new_assignment = assignment.copy()
            new_assignment[var] = value
            if self._consistent(new_assignment):
                result = self._backtrack(new_assignment)
                if result: return result
        return None

    def _consistent(self, assignment: Dict[str, int]) -> bool:
        for c in self.constraints:
            if all(v in assignment for v in c.variables):
                if not c.check(assignment): return False
        return True

    def stats(self) -> dict:
        return {"variables": len(self.variables), "constraints": len(self.constraints)}

def run():
    cs = ConstraintSolver()
    cs.add_variable("x", [1, 2, 3])
    cs.add_variable("y", [1, 2, 3])
    def diff(assignment): return assignment.get("x") != assignment.get("y")
    cs.add_constraint(Constraint(["x", "y"], diff))
    print("Solution:", cs.solve())
    print("Stats:", cs.stats())

if __name__ == "__main__": run()
