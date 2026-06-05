"""Document Examiner — handwriting, forgery detection, ink analysis, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class DocumentExaminer:
    features: Dict[str, float] = field(default_factory=dict)
    """feature -> score 0-1"""

    def add_feature(self, name: str, score: float):
        self.features[name] = score

    def authenticity_score(self) -> float:
        if not self.features:
            return 0.5
        weights = {"pressure": 0.2, "slant": 0.15, "spacing": 0.15, "ink_consistency": 0.2, "paper_age": 0.15, "watermark": 0.15}
        total = 0.0
        weight_sum = 0.0
        for f, w in weights.items():
            if f in self.features:
                total += self.features[f] * w
                weight_sum += w
        return total / weight_sum if weight_sum > 0 else 0.5

    def forgery_indicators(self) -> List[str]:
        indicators = []
        if self.features.get("pressure", 1) < 0.3:
            indicators.append("irregular pressure")
        if self.features.get("ink_consistency", 1) < 0.4:
            indicators.append("ink mismatch")
        if self.features.get("paper_age", 1) < 0.3:
            indicators.append("paper/date inconsistency")
        return indicators

    def verdict(self) -> str:
        score = self.authenticity_score()
        if score > 0.8:
            return "authentic"
        elif score > 0.5:
            return "questionable"
        return "likely forged"

    def stats(self) -> Dict:
        return {"score": round(self.authenticity_score(), 3), "verdict": self.verdict(), "indicators": self.forgery_indicators()}

def run():
    de = DocumentExaminer()
    de.add_feature("pressure", 0.9)
    de.add_feature("slant", 0.85)
    de.add_feature("ink_consistency", 0.4)
    print(de.stats())

if __name__ == "__main__":
    run()
