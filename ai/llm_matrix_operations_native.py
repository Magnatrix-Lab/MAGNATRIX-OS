"""Matrix Operations - Linear algebra for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import math

@dataclass
class MatrixOperations:

    def add(self, a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        return [[a[i][j]+b[i][j] for j in range(len(a[0]))] for i in range(len(a))]

    def multiply(self, a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        return [[sum(a[i][k]*b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]

    def transpose(self, a: List[List[float]]) -> List[List[float]]:
        return [[a[j][i] for j in range(len(a))] for i in range(len(a[0]))]

    def determinant(self, a: List[List[float]]) -> float:
        n = len(a)
        if n == 1: return a[0][0]
        if n == 2: return a[0][0]*a[1][1] - a[0][1]*a[1][0]
        det = 0
        for j in range(n):
            minor = [[a[i][k] for k in range(n) if k!=j] for i in range(1,n)]
            det += ((-1)**j) * a[0][j] * self.determinant(minor)
        return det

    def stats(self, a: List[List[float]]) -> dict:
        return {"shape": f"{len(a)}x{len(a[0])}", "det": round(self.determinant(a),4) if len(a)==len(a[0]) else None}

def run():
    mo = MatrixOperations()
    a = [[1,2],[3,4]]; b = [[5,6],[7,8]]
    print("Mul:", mo.multiply(a,b))
    print("Det:", mo.determinant(a))
    print("Stats:", mo.stats(a))

if __name__ == "__main__": run()
