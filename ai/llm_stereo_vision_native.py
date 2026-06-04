"""Stereo Vision - Depth from stereo for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class StereoVision:
    baseline: float = 0.1
    focal_length: float = 1.0

    def disparity_to_depth(self, disparity: float) -> float:
        if disparity <= 0: return float('inf')
        return self.baseline * self.focal_length / disparity

    def compute_disparity(self, left_x: float, right_x: float) -> float:
        return left_x - right_x

    def compute_depth_map(self, left_coords: List[float], right_coords: List[float]) -> List[float]:
        return [self.disparity_to_depth(self.compute_disparity(l, r)) for l, r in zip(left_coords, right_coords)]

    def stats(self, left_coords: List[float], right_coords: List[float]) -> dict:
        depths = self.compute_depth_map(left_coords, right_coords)
        valid = [d for d in depths if d != float('inf')]
        return {"baseline": self.baseline, "avg_depth": round(sum(valid)/len(valid), 4) if valid else 0, "points": len(depths)}

def run():
    sv = StereoVision(0.12, 2.0)
    left = [10, 20, 30]
    right = [8, 18, 28]
    depths = sv.compute_depth_map(left, right)
    print("Depths:", [round(d, 4) for d in depths])
    print("Stats:", sv.stats(left, right))

if __name__ == "__main__": run()
