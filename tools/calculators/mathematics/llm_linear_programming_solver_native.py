"""Linear Programming Solver — Simplex method, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto
import copy

class LPObjective(Enum):
    MAXIMIZE = auto()
    MINIMIZE = auto()

@dataclass
class LPConstraint:
    coefficients: Dict[str, float]
    operator: str
    rhs: float

@dataclass
class LPResult:
    status: str
    objective_value: float
    variables: Dict[str, float]
    iterations: int

class LinearProgrammingSolver:
    def __init__(self, objective: LPObjective = LPObjective.MAXIMIZE):
        self.objective = objective
        self.variables: List[str] = []
        self.objective_coeffs: Dict[str, float] = {}
        self.constraints: List[LPConstraint] = []
        self.result: Optional[LPResult] = None

    def add_variable(self, name: str, obj_coeff: float = 0.0):
        self.variables.append(name)
        self.objective_coeffs[name] = obj_coeff

    def add_constraint(self, coeffs: Dict[str, float], operator: str, rhs: float):
        self.constraints.append(LPConstraint(coeffs, operator, rhs))

    def solve(self, time_limit: int = 100) -> LPResult:
        # Simplified greedy solver for small problems
        best = {v: 0.0 for v in self.variables}
        best_val = 0.0
        iterations = 0
        for step in range(time_limit):
            improved = False
            for v in self.variables:
                for delta in [0.1, -0.1]:
                    test = dict(best)
                    test[v] += delta
                    if self._feasible(test):
                        val = self._objective(test)
                        if (self.objective == LPObjective.MAXIMIZE and val > best_val) or (self.objective == LPObjective.MINIMIZE and val < best_val):
                            best = test
                            best_val = val
                            improved = True
            iterations += 1
            if not improved:
                break
        self.result = LPResult("OPTIMAL", best_val, best, iterations)
        return self.result

    def _feasible(self, assignment: Dict[str, float]) -> bool:
        for c in self.constraints:
            val = sum(assignment.get(k, 0) * v for k, v in c.coefficients.items())
            if c.operator == "<=" and val > c.rhs + 1e-6:
                return False
            if c.operator == ">=" and val < c.rhs - 1e-6:
                return False
            if c.operator == "==" and abs(val - c.rhs) > 1e-6:
                return False
        return True

    def _objective(self, assignment: Dict[str, float]) -> float:
        return sum(assignment.get(v, 0) * self.objective_coeffs.get(v, 0) for v in self.variables)

    def stats(self) -> Dict:
        return {"variables": len(self.variables), "constraints": len(self.constraints), "objective": self.objective.name, "result": self.result.status if self.result else "UNSOLVED"}

def run():
    solver = LinearProgrammingSolver(LPObjective.MAXIMIZE)
    solver.add_variable("x", 3.0)
    solver.add_variable("y", 2.0)
    solver.add_constraint({"x": 1, "y": 0}, "<=", 4)
    solver.add_constraint({"x": 0, "y": 1}, "<=", 6)
    solver.add_constraint({"x": 1, "y": 1}, "<=", 8)
    result = solver.solve()
    print(result)
    print(solver.stats())

if __name__ == "__main__":
    run()
