"""Size Recommender — measurements, fit, grading, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class SizeRecommender:
    size_chart: Dict[str, Dict[str, float]] = field(default_factory=dict)
    """size -> {chest, waist, hip}"""

    def add_size(self, size: str, chest: float, waist: float, hip: float):
        self.size_chart[size] = {"chest": chest, "waist": waist, "hip": hip}

    def recommend(self, measurements: Dict[str, float], tolerance: float = 2.0) -> Optional[str]:
        best = None
        best_score = float('inf')
        for size, dims in self.size_chart.items():
            score = sum(abs(measurements.get(k, 0) - v) for k, v in dims.items())
            if score < best_score and score <= tolerance * 3:
                best_score = score
                best = size
        return best

    def fit_score(self, size: str, measurements: Dict[str, float]) -> float:
        dims = self.size_chart.get(size, {})
        if not dims:
            return 0.0
        diffs = [abs(measurements.get(k, 0) - v) for k, v in dims.items()]
        return 1 - min(1, sum(diffs) / 30)

    def size_up(self, size: str) -> Optional[str]:
        sizes = list(self.size_chart.keys())
        if size in sizes:
            idx = sizes.index(size)
            return sizes[idx+1] if idx + 1 < len(sizes) else None
        return None

    def stats(self) -> Dict:
        return {"sizes": len(self.size_chart), "dimensions": list(next(iter(self.size_chart.values())).keys()) if self.size_chart else []}

def run():
    sr = SizeRecommender()
    sr.add_size("S", 90, 75, 95)
    sr.add_size("M", 100, 85, 105)
    sr.add_size("L", 110, 95, 115)
    print(sr.recommend({"chest": 102, "waist": 86, "hip": 106}))
    print(sr.stats())

if __name__ == "__main__":
    run()
