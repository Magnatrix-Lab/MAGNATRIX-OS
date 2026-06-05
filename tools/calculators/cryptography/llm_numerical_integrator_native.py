"""Numerical Integrator — trapezoidal, Simpson, Monte Carlo, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Tuple
from enum import Enum, auto
import math
import random

class IntegrationMethod(Enum):
    TRAPEZOIDAL = auto()
    SIMPSON = auto()
    MONTE_CARLO = auto()
    MIDPOINT = auto()

class NumericalIntegrator:
    def __init__(self, method: IntegrationMethod = IntegrationMethod.SIMPSON):
        self.method = method
        self.results: List[Dict] = []

    def integrate(self, f: Callable[[float], float], a: float, b: float, n: int = 1000) -> float:
        if self.method == IntegrationMethod.TRAPEZOIDAL:
            return self._trapezoidal(f, a, b, n)
        elif self.method == IntegrationMethod.SIMPSON:
            return self._simpson(f, a, b, n)
        elif self.method == IntegrationMethod.MONTE_CARLO:
            return self._monte_carlo(f, a, b, n)
        elif self.method == IntegrationMethod.MIDPOINT:
            return self._midpoint(f, a, b, n)
        return 0.0

    def _trapezoidal(self, f, a, b, n):
        h = (b - a) / n
        s = 0.5 * (f(a) + f(b))
        for i in range(1, n):
            s += f(a + i * h)
        return s * h

    def _simpson(self, f, a, b, n):
        if n % 2 == 1:
            n += 1
        h = (b - a) / n
        s = f(a) + f(b)
        for i in range(1, n):
            if i % 2 == 0:
                s += 2 * f(a + i * h)
            else:
                s += 4 * f(a + i * h)
        return s * h / 3

    def _monte_carlo(self, f, a, b, n):
        total = 0.0
        for _ in range(n):
            x = random.uniform(a, b)
            total += f(x)
        return (b - a) * total / n

    def _midpoint(self, f, a, b, n):
        h = (b - a) / n
        total = 0.0
        for i in range(n):
            x = a + (i + 0.5) * h
            total += f(x)
        return total * h

    def integrate_2d(self, f: Callable[[float, float], float], x0: float, x1: float, y0: float, y1: float, nx: int = 100, ny: int = 100) -> float:
        dx = (x1 - x0) / nx
        dy = (y1 - y0) / ny
        total = 0.0
        for i in range(nx):
            for j in range(ny):
                x = x0 + (i + 0.5) * dx
                y = y0 + (j + 0.5) * dy
                total += f(x, y)
        return total * dx * dy

    def stats(self) -> Dict:
        return {"method": self.method.name, "results": len(self.results)}

def run():
    integrator = NumericalIntegrator(IntegrationMethod.SIMPSON)
    result = integrator.integrate(lambda x: x ** 2, 0, 1, 100)
    print("Integral of x^2 from 0 to 1:", result)
    print("Monte Carlo:", NumericalIntegrator(IntegrationMethod.MONTE_CARLO).integrate(lambda x: math.sin(x), 0, math.pi, 10000))
    print(integrator.stats())

if __name__ == "__main__":
    run()
