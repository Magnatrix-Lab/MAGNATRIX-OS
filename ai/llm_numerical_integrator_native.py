"""Numerical Integrator - Integration methods for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

class IntegratorType(Enum):
    RECTANGLE = auto(); TRAPEZOID = auto(); SIMPSON = auto()

@dataclass
class NumericalIntegrator:
    method: IntegratorType = IntegratorType.TRAPEZOID
    n: int = 100

    def integrate(self, f: callable, a: float, b: float) -> float:
        h = (b - a) / self.n
        if self.method == IntegratorType.RECTANGLE:
            return sum(f(a + i * h) * h for i in range(self.n))
        elif self.method == IntegratorType.TRAPEZOID:
            return h * (0.5 * f(a) + sum(f(a + i * h) for i in range(1, self.n)) + 0.5 * f(b))
        elif self.method == IntegratorType.SIMPSON:
            if self.n % 2 == 1: self.n += 1; h = (b - a) / self.n
            return h/3 * (f(a) + f(b) + 4 * sum(f(a + i*h) for i in range(1, self.n, 2)) + 2 * sum(f(a + i*h) for i in range(2, self.n, 2)))
        return 0.0

    def stats(self, f: callable, a: float, b: float) -> dict:
        return {"method": self.method.name, "n": self.n, "result": round(self.integrate(f, a, b), 6)}

def run():
    ni = NumericalIntegrator(IntegratorType.SIMPSON, 100)
    result = ni.integrate(lambda x: x**2, 0, 1)
    print("Integral x^2 from 0 to 1:", round(result, 6))
    print("Stats:", ni.stats(lambda x: x**2, 0, 1))

if __name__ == "__main__": run()
