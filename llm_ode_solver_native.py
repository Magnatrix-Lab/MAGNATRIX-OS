"""ODE Solver — Euler, Runge-Kutta, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Tuple, Optional
from enum import Enum, auto
import math

class ODESolverType(Enum):
    EULER = auto()
    RK2 = auto()
    RK4 = auto()

@dataclass
class ODEResult:
    t_values: List[float]
    y_values: List[float]
    steps: int

class ODESolver:
    def __init__(self, solver_type: ODESolverType = ODESolverType.RK4):
        self.solver_type = solver_type

    def solve(self, f: Callable[[float, float], float], y0: float, t0: float, t_end: float, h: float) -> ODEResult:
        t = t0
        y = y0
        t_values = [t]
        y_values = [y]
        steps = 0
        while t < t_end:
            if self.solver_type == ODESolverType.EULER:
                y = y + h * f(t, y)
            elif self.solver_type == ODESolverType.RK2:
                k1 = h * f(t, y)
                k2 = h * f(t + h, y + k1)
                y = y + 0.5 * (k1 + k2)
            elif self.solver_type == ODESolverType.RK4:
                k1 = h * f(t, y)
                k2 = h * f(t + h / 2, y + k1 / 2)
                k3 = h * f(t + h / 2, y + k2 / 2)
                k4 = h * f(t + h, y + k3)
                y = y + (k1 + 2 * k2 + 2 * k3 + k4) / 6
            t += h
            t_values.append(t)
            y_values.append(y)
            steps += 1
        return ODEResult(t_values, y_values, steps)

    def solve_system(self, f: Callable[[float, List[float]], List[float]], y0: List[float], t0: float, t_end: float, h: float) -> Tuple[List[float], List[List[float]]]:
        t = t0
        y = list(y0)
        t_values = [t]
        y_values = [list(y)]
        while t < t_end:
            k1 = [h * fi for fi in f(t, y)]
            k2 = [h * fi for fi in f(t + h / 2, [yi + ki / 2 for yi, ki in zip(y, k1)])]
            k3 = [h * fi for fi in f(t + h / 2, [yi + ki / 2 for yi, ki in zip(y, k2)])]
            k4 = [h * fi for fi in f(t + h, [yi + ki for yi, ki in zip(y, k3)])]
            y = [yi + (k1i + 2 * k2i + 2 * k3i + k4i) / 6 for yi, k1i, k2i, k3i, k4i in zip(y, k1, k2, k3, k4)]
            t += h
            t_values.append(t)
            y_values.append(list(y))
        return t_values, y_values

    def stats(self) -> Dict:
        return {"solver": self.solver_type.name, "methods": ["Euler", "RK2", "RK4"]}

def run():
    solver = ODESolver(ODESolverType.RK4)
    result = solver.solve(lambda t, y: -0.5 * y, 1.0, 0.0, 10.0, 0.1)
    print("Final:", result.y_values[-1])
    print("Steps:", result.steps)
    print(solver.stats())

if __name__ == "__main__":
    run()
