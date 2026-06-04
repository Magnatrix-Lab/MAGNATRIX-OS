"""Wavelet Transform — Haar wavelet, decomposition, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class WaveletTransform:
    def __init__(self, levels: int = 3):
        self.levels = levels

    def _haar_step(self, data: List[float]) -> Tuple[List[float], List[float]]:
        approx = []
        detail = []
        for i in range(0, len(data) - 1, 2):
            a = (data[i] + data[i + 1]) / math.sqrt(2)
            d = (data[i] - data[i + 1]) / math.sqrt(2)
            approx.append(a)
            detail.append(d)
        if len(data) % 2 == 1:
            approx.append(data[-1] / math.sqrt(2))
            detail.append(data[-1] / math.sqrt(2))
        return approx, detail

    def decompose(self, data: List[float]) -> List[Dict]:
        coeffs = []
        current = data[:]
        for level in range(self.levels):
            if len(current) < 2:
                break
            approx, detail = self._haar_step(current)
            coeffs.append({"level": level + 1, "approximation": approx, "detail": detail})
            current = approx
        return coeffs

    def reconstruct(self, coeffs: List[Dict]) -> List[float]:
        if not coeffs:
            return []
        approx = coeffs[-1]["approximation"][:]
        for level in reversed(range(len(coeffs) - 1)):
            detail = coeffs[level]["detail"]
            reconstructed = []
            for i in range(len(approx)):
                reconstructed.append((approx[i] + detail[i]) / math.sqrt(2))
                reconstructed.append((approx[i] - detail[i]) / math.sqrt(2))
            approx = reconstructed
        return approx

    def stats(self) -> Dict:
        return {"levels": self.levels, "wavelet": "Haar"}

def run():
    wt = WaveletTransform(2)
    data = [10, 20, 30, 40, 50, 60, 70, 80]
    coeffs = wt.decompose(data)
    print("Decomposed levels:", len(coeffs))
    rec = wt.reconstruct(coeffs)
    print("Reconstructed:", [round(r, 2) for r in rec])
    print(wt.stats())

if __name__ == "__main__":
    run()
