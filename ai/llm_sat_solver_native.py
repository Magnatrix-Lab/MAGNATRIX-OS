"""SAT Solver - DPLL for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum, auto
import random

@dataclass
class SATSolver:
    clauses: List[List[int]] = field(default_factory=list)
    num_vars: int = 0

    def add_clause(self, literals: List[int]) -> None:
        self.clauses.append(literals)
        self.num_vars = max(self.num_vars, max(abs(l) for l in literals) if literals else 0)

    def solve(self) -> Optional[Dict[int, bool]]:
        assignment = {}
        if self._dpll(assignment, list(range(1, self.num_vars + 1))):
            return assignment
        return None

    def _dpll(self, assignment: Dict[int, bool], unassigned: List[int]) -> bool:
        if all(self._satisfied(c, assignment) for c in self.clauses):
            return True
        if any(self._conflict(c, assignment) for c in self.clauses):
            return False
        if not unassigned: return False
        var = unassigned[0]
        for val in [True, False]:
            assignment[var] = val
            if self._dpll(assignment, unassigned[1:]):
                return True
            del assignment[var]
        return False

    def _satisfied(self, clause: List[int], assignment: Dict[int, bool]) -> bool:
        for l in clause:
            var = abs(l)
            if var in assignment:
                val = assignment[var] if l > 0 else not assignment[var]
                if val: return True
        return False

    def _conflict(self, clause: List[int], assignment: Dict[int, bool]) -> bool:
        for l in clause:
            var = abs(l)
            if var not in assignment: return False
            val = assignment[var] if l > 0 else not assignment[var]
            if val: return False
        return True

    def stats(self) -> dict:
        return {"clauses": len(self.clauses), "vars": self.num_vars, "satisfiable": self.solve() is not None}

def run():
    sat = SATSolver()
    sat.add_clause([1, 2])
    sat.add_clause([-1, 2])
    sat.add_clause([-2])
    print("Solution:", sat.solve())
    print("Stats:", sat.stats())

if __name__ == "__main__": run()
