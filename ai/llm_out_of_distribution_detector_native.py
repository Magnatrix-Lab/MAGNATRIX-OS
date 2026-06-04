"""OOD Detector - Out-of-distribution detection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto
import math

class OODMethod(Enum):
    MAHALANOBIS = auto(); ENERGY = auto(); MSP = auto()

@dataclass
class OODDetector:
    method: OODMethod = OODMethod.MSP
    threshold: float = 0.5
    class_centroids: Dict[int, List[float]] = field(default_factory=dict)

    def fit(self, features: List[List[float]], labels: List[int]) -> None:
        for label in set(labels):
            class_features = [f for f, l in zip(features, labels) if l == label]
            centroid = [sum(f[i] for f in class_features)/len(class_features) for i in range(len(class_features[0]))]
            self.class_centroids[label] = centroid

    def detect(self, feature: List[float]) -> bool:
        if self.method == OODMethod.MSP:
            max_prob = max(feature) if feature else 0
            return max_prob < self.threshold
        elif self.method == OODMethod.ENERGY:
            energy = -sum(math.exp(v) for v in feature)
            return energy > self.threshold
        return False

    def stats(self, features: List[List[float]]) -> dict:
        ood_count = sum(1 for f in features if self.detect(f))
        return {"method": self.method.name, "ood_count": ood_count, "total": len(features)}

def run():
    ood = OODDetector(OODMethod.MSP, 0.7)
    features = [[0.9, 0.1, 0.0], [0.2, 0.3, 0.5], [0.8, 0.1, 0.1]]
    print("OOD detected:", [ood.detect(f) for f in features])
    print("Stats:", ood.stats(features))

if __name__ == "__main__": run()
