"""DCT Engine — Discrete Cosine Transform, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class DCTEngine:
    def __init__(self, n: int = 8):
        self.n = n
        self._compute_table()

    def _compute_table(self):
        self.table = []
        for k in range(self.n):
            row = []
            for i in range(self.n):
                row.append(math.cos(math.pi * k * (i + 0.5) / self.n))
            self.table.append(row)

    def dct(self, data: List[float]) -> List[float]:
        result = []
        for k in range(self.n):
            s = 0.0
            for i in range(self.n):
                s += data[i] * self.table[k][i]
            alpha = math.sqrt(2 / self.n) if k > 0 else math.sqrt(1 / self.n)
            result.append(s * alpha)
        return result

    def idct(self, coeffs: List[float]) -> List[float]:
        result = []
        for i in range(self.n):
            s = 0.0
            for k in range(self.n):
                alpha = math.sqrt(2 / self.n) if k > 0 else math.sqrt(1 / self.n)
                s += coeffs[k] * alpha * self.table[k][i]
            result.append(s)
        return result

    def stats(self) -> Dict:
        return {"n": self.n}

def run():
    dct = DCTEngine(8)
    data = [10, 20, 30, 40, 50, 60, 70, 80]
    coeffs = dct.dct(data)
    print("DCT:", [round(c, 2) for c in coeffs])
    rec = dct.idct(coeffs)
    print("Reconstructed:", [round(r, 2) for r in rec])
    print(dct.stats())

if __name__ == "__main__":
    run()
