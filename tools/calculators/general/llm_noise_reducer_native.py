"""Noise Reducer — median, gaussian, mean, threshold, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class NoiseReducer:
    def median_filter(self, data: List[float], window: int = 3) -> List[float]:
        if window % 2 == 0:
            window += 1
        half = window // 2
        result = []
        for i in range(len(data)):
            start = max(0, i - half)
            end = min(len(data), i + half + 1)
            window_vals = sorted(data[start:end])
            result.append(window_vals[len(window_vals) // 2])
        return result

    def mean_filter(self, data: List[float], window: int = 3) -> List[float]:
        half = window // 2
        result = []
        for i in range(len(data)):
            start = max(0, i - half)
            end = min(len(data), i + half + 1)
            result.append(sum(data[start:end]) / (end - start))
        return result

    def gaussian_kernel(self, size: int, sigma: float = 1.0) -> List[float]:
        import math
        half = size // 2
        kernel = [math.exp(-(i**2) / (2 * sigma**2)) for i in range(-half, half + 1)]
        total = sum(kernel)
        return [k / total for k in kernel]

    def gaussian_filter(self, data: List[float], sigma: float = 1.0) -> List[float]:
        size = int(sigma * 6) + 1
        kernel = self.gaussian_kernel(size, sigma)
        half = size // 2
        result = []
        for i in range(len(data)):
            val = 0.0
            weight = 0.0
            for j, k in enumerate(kernel):
                idx = i + j - half
                if 0 <= idx < len(data):
                    val += data[idx] * k
                    weight += k
            result.append(val / weight if weight > 0 else data[i])
        return result

    def threshold_denoise(self, data: List[float], threshold: float) -> List[float]:
        return [0 if abs(v) < threshold else v for v in data]

    def stats(self, data: List[float]) -> Dict:
        if not data:
            return {}
        return {"mean": sum(data)/len(data), "min": min(data), "max": max(data)}

def run():
    nr = NoiseReducer()
    data = [10, 12, 50, 11, 13, 10, 12]
    print("Median:", nr.median_filter(data))
    print("Mean:", nr.mean_filter(data))
    print("Gaussian:", nr.gaussian_filter(data, 1.0))

if __name__ == "__main__":
    run()
