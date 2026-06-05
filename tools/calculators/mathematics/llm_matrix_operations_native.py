"""Matrix Operations — linear algebra primitives, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import random

class MatrixOps:
    def __init__(self):
        pass

    def zeros(self, rows: int, cols: int) -> List[List[float]]:
        return [[0.0 for _ in range(cols)] for _ in range(rows)]

    def ones(self, rows: int, cols: int) -> List[List[float]]:
        return [[1.0 for _ in range(cols)] for _ in range(rows)]

    def identity(self, n: int) -> List[List[float]]:
        return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    def random_matrix(self, rows: int, cols: int, lo: float = -1, hi: float = 1) -> List[List[float]]:
        return [[random.uniform(lo, hi) for _ in range(cols)] for _ in range(rows)]

    def add(self, a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]

    def multiply(self, a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        rows_a = len(a)
        cols_a = len(a[0])
        cols_b = len(b[0])
        result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]
        for i in range(rows_a):
            for j in range(cols_b):
                for k in range(cols_a):
                    result[i][j] += a[i][k] * b[k][j]
        return result

    def transpose(self, a: List[List[float]]) -> List[List[float]]:
        return [[a[i][j] for i in range(len(a))] for j in range(len(a[0]))]

    def determinant(self, a: List[List[float]]) -> float:
        n = len(a)
        if n == 1:
            return a[0][0]
        if n == 2:
            return a[0][0] * a[1][1] - a[0][1] * a[1][0]
        det = 0.0
        for j in range(n):
            minor = [row[:j] + row[j+1:] for row in a[1:]]
            det += ((-1) ** j) * a[0][j] * self.determinant(minor)
        return det

    def trace(self, a: List[List[float]]) -> float:
        return sum(a[i][i] for i in range(len(a)))

    def power_iteration(self, a: List[List[float]], max_iter: int = 100) -> Tuple[float, List[float]]:
        n = len(a)
        b = [random.random() for _ in range(n)]
        norm = math.sqrt(sum(x ** 2 for x in b))
        b = [x / norm for x in b]
        for _ in range(max_iter):
            b_new = [sum(a[i][j] * b[j] for j in range(n)) for i in range(n)]
            norm = math.sqrt(sum(x ** 2 for x in b_new))
            b = [x / norm for x in b_new]
        eigenvalue = sum(b[i] * sum(a[i][j] * b[j] for j in range(n)) for i in range(n))
        return eigenvalue, b

    def stats(self) -> Dict:
        return {"operations": ["add", "multiply", "transpose", "determinant", "trace", "power_iteration"]}

def run():
    ops = MatrixOps()
    a = [[1, 2], [3, 4]]
    b = [[5, 6], [7, 8]]
    print("Add:", ops.add(a, b))
    print("Mul:", ops.multiply(a, b))
    print("Det:", ops.determinant(a))
    print("Trace:", ops.trace(a))
    print("Eigen:", ops.power_iteration(a, 50))
    print(ops.stats())

if __name__ == "__main__":
    run()
