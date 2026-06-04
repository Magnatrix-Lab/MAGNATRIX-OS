"""Differential Solver - ODE solver for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

class SolverType(Enum):
    EULER = auto(); RK4 = auto()

@dataclass
class DifferentialSolver:
    method: SolverType = SolverType.RK4
    h: float = 0.1

    def solve(self, f: callable, y0: float, t0: float, t1: float) -> List[Tuple[float, float]]:
        t = t0; y = y0; result = [(t, y)]
        if self.method == SolverType.EULER:
            while t < t1:
                y += self.h * f(t, y)
                t += self.h
                result.append((round(t, 4), round(y, 4)))
        elif self.method == SolverType.RK4:
            while t < t1:
                k1 = f(t, y)
                k2 = f(t + self.h/2, y + self.h*k1/2)
                k3 = f(t + self.h/2, y + self.h*k2/2)
                k4 = f(t + self.h, y + self.h*k3)
                y += self.h/6 * (k1 + 2*k2 + 2*k3 + k4)
                t += self.h
                result.append((round(t, 4), round(y, 4)))
        return result

    def stats(self, f: callable, y0: float, t0: float, t1: float) -> dict:
        result = self.solve(f, y0, t0, t1)
        return {"method": self.method.name, "steps": len(result), "final": round(result[-1][1], 4) if result else 0}

def run():
    ds = DifferentialSolver(SolverType.RK4, 0.1)
    # dy/dt = -y, solution y = e^(-t)
    result = ds.solve(lambda t, y: -y, 1.0, 0.0, 1.0)
    print("Final value:", round(result[-1][1], 4))
    print("Stats:", ds.stats(lambda t, y: -y, 1.0, 0.0, 1.0))

if __name__ == "__main__": run()
