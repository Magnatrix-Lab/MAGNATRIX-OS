"""Convolution Engine — 1D/2D convolution, kernels, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class ConvolutionEngine:
    def __init__(self):
        self.kernels: Dict[str, List[List[float]]] = {}

    def add_kernel(self, name: str, kernel: List[List[float]]):
        self.kernels[name] = kernel

    def convolve_1d(self, signal: List[float], kernel: List[float]) -> List[float]:
        k = len(kernel)
        n = len(signal)
        result = []
        for i in range(n - k + 1):
            s = sum(signal[i + j] * kernel[j] for j in range(k))
            result.append(s)
        return result

    def convolve_2d(self, matrix: List[List[float]], kernel: List[List[float]]) -> List[List[float]]:
        kh = len(kernel)
        kw = len(kernel[0]) if kernel else 0
        mh = len(matrix)
        mw = len(matrix[0]) if matrix else 0
        result = []
        for i in range(mh - kh + 1):
            row = []
            for j in range(mw - kw + 1):
                s = 0.0
                for ki in range(kh):
                    for kj in range(kw):
                        s += matrix[i + ki][j + kj] * kernel[ki][kj]
                row.append(s)
            result.append(row)
        return result

    def gaussian_kernel_1d(self, size: int, sigma: float = 1.0) -> List[float]:
        import math
        center = size // 2
        kernel = [math.exp(-((i - center) ** 2) / (2 * sigma ** 2)) for i in range(size)]
        total = sum(kernel)
        return [k / total for k in kernel]

    def gaussian_kernel_2d(self, size: int, sigma: float = 1.0) -> List[List[float]]:
        k1d = self.gaussian_kernel_1d(size, sigma)
        return [[k1d[i] * k1d[j] for j in range(size)] for i in range(size)]

    def stats(self) -> Dict:
        return {"kernels": len(self.kernels)}

def run():
    ce = ConvolutionEngine()
    signal = [1, 2, 3, 4, 5]
    kernel = [1, 0, -1]
    print(ce.convolve_1d(signal, kernel))
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    edge = [[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]]
    print(ce.convolve_2d(matrix, edge))
    print(ce.stats())

if __name__ == "__main__":
    run()
