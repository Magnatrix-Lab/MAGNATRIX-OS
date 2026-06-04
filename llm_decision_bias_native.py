"""Decision Bias Detector — anchoring, confirmation, availability, framing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import re

@dataclass
class DecisionBias:
    biases: Dict[str, List[str]] = field(default_factory=lambda: {
        "anchoring": ["first", "initial", "starting", "original"],
        "confirmation": ["obviously", "as expected", "knew it", "confirms"],
        "availability": ["recently", "just heard", "news", "remember"],
        "framing": ["gain", "loss", "risky", "safe", "sure thing"],
        "sunk_cost": ["already invested", "cant give up", "spent so much", "waste"]
    })

    def detect(self, text: str) -> Dict[str, float]:
        words = set(re.findall(r'\w+', text.lower()))
        scores = {}
        for bias, markers in self.biases.items():
            count = sum(1 for m in markers if m in words or m in text.lower())
            scores[bias] = min(1.0, count / 2)
        return scores

    def dominant_bias(self, text: str) -> Optional[str]:
        scores = self.detect(text)
        if max(scores.values()) == 0:
            return None
        return max(scores, key=scores.get)

    def mitigation(self, bias: str) -> str:
        tips = {
            "anchoring": "Consider multiple reference points.",
            "confirmation": "Actively seek disconfirming evidence.",
            "availability": "Base decisions on statistical data, not recent examples.",
            "framing": "Reframe the decision in both gain and loss perspectives.",
            "sunk_cost": "Focus on future value, not past investment."
        }
        return tips.get(bias, "No specific mitigation known.")

    def stats(self, text: str) -> Dict:
        return {"detected": self.detect(text), "dominant": self.dominant_bias(text)}

def run():
    db = DecisionBias()
    text = "I already invested so much, I cant give up now. The initial offer confirms my expectation."
    print("Detect:", db.detect(text))
    print("Dominant:", db.dominant_bias(text))
    print("Mitigation:", db.mitigation(db.dominant_bias(text)))
    print(db.stats(text))

if __name__ == "__main__":
    run()
