"""Eigenvalue Solver - Power iteration for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import math

@dataclass
class EigenvalueSolver:
    max_iter: int = 100; tol: float = 1e-6

    def power_iteration(self, A: List[List[float]]) -> Tuple[float, List[float]]:
        n = len(A)
        b = [1.0]*n
        for _ in range(self.max_iter):
            Ab = [sum(A[i][j]*b[j] for j in range(n)) for i in range(n)]
            norm = math.sqrt(sum(x*x for x in Ab))
            if norm < 1e-10: break
            new_b = [x/norm for x in Ab]
            if math.sqrt(sum((new_b[i]-b[i])**2 for i in range(n))) < self.tol:
                b = new_b; break
            b = new_b
        eigenvalue = sum(b[i]*sum(A[i][j]*b[j] for j in range(n)) for i in range(n))
        return eigenvalue, b

    def stats(self, A: List[List[float]]) -> dict:
        ev, vec = self.power_iteration(A)
        return {"eigenvalue": round(ev,4), "dim": len(A)}

def run():
    es = EigenvalueSolver()
    A = [[4,1],[2,3]]
    ev, vec = es.power_iteration(A)
    print(f"Eigenvalue: {round(ev,4)}, vector: {[round(v,4) for v in vec]}")
    print("Stats:", es.stats(A))

if __name__ == "__main__": run()
