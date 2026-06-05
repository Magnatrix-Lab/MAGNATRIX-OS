"""Art Critic Scorer — composition, technique, originality, impact, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ArtCriticScorer:
    composition: float = 0.0
    technique: float = 0.0
    originality: float = 0.0
    emotional_impact: float = 0.0
    color_harmony: float = 0.0

    def overall(self) -> float:
        return (self.composition + self.technique + self.originality + self.emotional_impact + self.color_harmony) / 5

    def strengths(self) -> List[str]:
        attrs = {
            "composition": self.composition,
            "technique": self.technique,
            "originality": self.originality,
            "emotional impact": self.emotional_impact,
            "color harmony": self.color_harmony
        }
        return [k for k, v in attrs.items() if v >= 8]

    def weaknesses(self) -> List[str]:
        attrs = {
            "composition": self.composition,
            "technique": self.technique,
            "originality": self.originality,
            "emotional impact": self.emotional_impact,
            "color harmony": self.color_harmony
        }
        return [k for k, v in attrs.items() if v <= 4]

    def recommendation(self) -> str:
        w = self.weaknesses()
        if w:
            return f"Focus on improving: {', '.join(w)}."
        return "Excellent work across all dimensions."

    def grade(self) -> str:
        o = self.overall()
        if o >= 9: return "A+"
        elif o >= 8: return "A"
        elif o >= 7: return "B"
        elif o >= 6: return "C"
        elif o >= 5: return "D"
        return "F"

    def stats(self) -> Dict:
        return {"overall": round(self.overall(), 2), "grade": self.grade(), "strengths": self.strengths(), "weaknesses": self.weaknesses()}

def run():
    ac = ArtCriticScorer(composition=8, technique=7, originality=9, emotional_impact=6, color_harmony=8)
    print(ac.stats())
    print(ac.recommendation())

if __name__ == "__main__":
    run()
