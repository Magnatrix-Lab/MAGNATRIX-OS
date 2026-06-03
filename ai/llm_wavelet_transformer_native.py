"""Wavelet Transformer - Haar wavelet for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import math

@dataclass
class WaveletTransformer:
    levels: int = 2

    def haar_step(self, data: List[float]) -> Tuple[List[float], List[float]]:
        n = len(data)//2
        approx = [(data[2*i]+data[2*i+1])/math.sqrt(2) for i in range(n)]
        detail = [(data[2*i]-data[2*i+1])/math.sqrt(2) for i in range(n)]
        return approx, detail

    def transform(self, data: List[float]) -> List[Tuple[List[float], List[float]]]:
        result = []
        current = data
        for _ in range(self.levels):
            if len(current) < 2: break
            a, d = self.haar_step(current)
            result.append((a,d))
            current = a
        return result

    def stats(self, data: List[float]) -> dict:
        result = self.transform(data)
        return {"levels": len(result), "original_len": len(data)}

def run():
    wt = WaveletTransformer(2)
    data = [8.0, 4.0, 2.0, 6.0, 3.0, 1.0, 5.0, 7.0]
    result = wt.transform(data)
    for i, (a,d) in enumerate(result):
        print(f"Level {i}: approx={[round(v,4) for v in a]}, detail={[round(v,4) for v in d]}")
    print("Stats:", wt.stats(data))

if __name__ == "__main__": run()
