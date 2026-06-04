"""Feature Matcher - SIFT-like feature matching for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class FeaturePoint:
    x: float; y: float; descriptor: List[float]

@dataclass
class FeatureMatcher:
    distance_threshold: float = 0.7

    def distance(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((a[i]-b[i])**2 for i in range(len(a))))

    def match(self, features1: List[FeaturePoint], features2: List[FeaturePoint]) -> List[Tuple[int, int, float]]:
        matches = []
        for i, f1 in enumerate(features1):
            distances = [(j, self.distance(f1.descriptor, f2.descriptor)) for j, f2 in enumerate(features2)]
            distances.sort(key=lambda x: x[1])
            if len(distances) >= 2 and distances[0][1] < self.distance_threshold * distances[1][1]:
                matches.append((i, distances[0][0], distances[0][1]))
        return matches

    def stats(self, features1: List[FeaturePoint], features2: List[FeaturePoint]) -> dict:
        matches = self.match(features1, features2)
        return {"matches": len(matches), "f1_count": len(features1), "f2_count": len(features2)}

def run():
    fm = FeatureMatcher(0.8)
    f1 = [FeaturePoint(0, 0, [1,0,0]), FeaturePoint(1, 1, [0,1,0])]
    f2 = [FeaturePoint(0, 0, [1.1,0,0]), FeaturePoint(1, 1, [0,1.1,0]), FeaturePoint(2, 2, [0,0,1])]
    matches = fm.match(f1, f2)
    print("Matches:", matches)
    print("Stats:", fm.stats(f1, f2))

if __name__ == "__main__": run()
