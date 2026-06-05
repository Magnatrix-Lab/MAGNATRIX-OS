"""Native stdlib module: Latent Fingerprint Calculator
Evaluates fingerprint match scores and minutiae comparison metrics.
"""
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class MinutiaePoint:
    x: int
    y: int
    type: str  # ridge_ending, bifurcation, etc.
    angle: float

@dataclass
class LatentFingerprintCalculator:
    query_minutiae: List[MinutiaePoint]
    template_minutiae: List[MinutiaePoint]
    tolerance_px: float = 15.0
    angle_tolerance_deg: float = 22.5

    def _match_minutiae(self, q: MinutiaePoint, t: MinutiaePoint) -> bool:
        dx = q.x - t.x
        dy = q.y - t.y
        dist = (dx * dx + dy * dy) ** 0.5
        angle_diff = abs((q.angle - t.angle + 180) % 360 - 180)
        return dist <= self.tolerance_px and angle_diff <= self.angle_tolerance_deg

    def matched_count(self) -> int:
        matched = set()
        for i, q in enumerate(self.query_minutiae):
            for j, t in enumerate(self.template_minutiae):
                if j in matched:
                    continue
                if self._match_minutiae(q, t):
                    matched.add(j)
                    break
        return len(matched)

    def match_score(self) -> float:
        if not self.query_minutiae or not self.template_minutiae:
            return 0.0
        return (self.matched_count() / max(len(self.query_minutiae), len(self.template_minutiae))) * 100

    def minutiae_count_ratio(self) -> float:
        if not self.template_minutiae:
            return 0.0
        return len(self.query_minutiae) / len(self.template_minutiae)

    def stats(self) -> Dict:
        return {
            "query_minutiae": len(self.query_minutiae),
            "template_minutiae": len(self.template_minutiae),
            "matched_count": self.matched_count(),
            "match_score_pct": round(self.match_score(), 1),
            "minutiae_ratio": round(self.minutiae_count_ratio(), 2),
        }

def run():
    q = [
        MinutiaePoint(10, 20, "ridge_ending", 45),
        MinutiaePoint(30, 40, "bifurcation", 90),
        MinutiaePoint(50, 60, "ridge_ending", 135),
    ]
    t = [
        MinutiaePoint(12, 22, "ridge_ending", 48),
        MinutiaePoint(32, 42, "bifurcation", 88),
        MinutiaePoint(55, 65, "ridge_ending", 140),
        MinutiaePoint(70, 80, "bifurcation", 180),
    ]
    lfc = LatentFingerprintCalculator(q, t)
    print(lfc.stats())

if __name__ == "__main__":
    run()
