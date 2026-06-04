"""Root Finder - Numerical root finding for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto
import math

class RootMethod(Enum):
    BISECTION = auto(); NEWTON = auto(); SECANT = auto()

@dataclass
class RootFinder:
    method: RootMethod = RootMethod.BISECTION
    tol: float = 1e-6
    max_iter: int = 100

    def find(self, f: Callable, a: float, b: float, df: Callable = None) -> Optional[float]:
        if self.method == RootMethod.BISECTION:
            return self._bisection(f, a, b)
        elif self.method == RootMethod.NEWTON and df:
            return self._newton(f, df, a)
        elif self.method == RootMethod.SECANT:
            return self._secant(f, a, b)
        return None

    def _bisection(self, f, a, b):
        fa, fb = f(a), f(b)
        if fa * fb > 0: return None
        for _ in range(self.max_iter):
            c = (a + b) / 2
            fc = f(c)
            if abs(fc) < self.tol or (b - a) / 2 < self.tol: return c
            if fa * fc < 0: b = c; fb = fc
            else: a = c; fa = fc
        return (a + b) / 2

    def _newton(self, f, df, x0):
        x = x0
        for _ in range(self.max_iter):
            fx = f(x)
            if abs(fx) < self.tol: return x
            dfx = df(x)
            if abs(dfx) < 1e-10: return None
            x -= fx / dfx
        return x

    def _secant(self, f, x0, x1):
        for _ in range(self.max_iter):
            fx0, fx1 = f(x0), f(x1)
            if abs(fx1) < self.tol: return x1
            if abs(fx1 - fx0) < 1e-10: return None
            x_new = x1 - fx1 * (x1 - x0) / (fx1 - fx0)
            x0, x1 = x1, x_new
        return x1

    def stats(self, f, a, b, df=None) -> dict:
        root = self.find(f, a, b, df)
        return {"method": self.method.name, "root": round(root, 6) if root else None, "iterations": self.max_iter}

def run():
    rf = RootFinder(RootMethod.BISECTION, 1e-6, 50)
    root = rf.find(lambda x: x**2 - 2, 0, 2)
    print("Root of x^2 - 2:", round(root, 6) if root else None)
    print("Stats:", rf.stats(lambda x: x**2 - 2, 0, 2))

if __name__ == "__main__": run()
