"""Fallacy Detector — informal fallacies, patterns, scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import re

@dataclass
class FallacyDetector:
    patterns: Dict[str, List[str]] = field(default_factory=lambda: {
        "ad_hominem": ["you are", "your character", "because you", "irrelevant personal"],
        "appeal_to_authority": ["expert says", "doctor says", "studies show", "according to"],
        "bandwagon": ["everyone believes", "popular opinion", "common sense", "everyone knows"],
        "false_cause": ["after this therefore", "because of that", "correlation implies"],
        "red_herring": ["irrelevant", "changing subject", "distracting", "off topic"]
    })
    weights: Dict[str, float] = field(default_factory=lambda: {
        "ad_hominem": 0.3, "appeal_to_authority": 0.2, "bandwagon": 0.2, "false_cause": 0.2, "red_herring": 0.1
    })

    def detect(self, text: str) -> Dict[str, float]:
        text_lower = text.lower()
        scores = {}
        for fallacy, markers in self.patterns.items():
            count = sum(1 for m in markers if m in text_lower)
            scores[fallacy] = min(1.0, count * self.weights.get(fallacy, 0.2))
        return scores

    def overall_fallacy_score(self, text: str) -> float:
        scores = self.detect(text)
        return sum(scores.values())

    def classify(self, text: str) -> Optional[str]:
        scores = self.detect(text)
        if max(scores.values()) == 0:
            return None
        return max(scores, key=scores.get)

    def explain(self, fallacy: str) -> str:
        explanations = {
            "ad_hominem": "Attacking the person rather than the argument.",
            "appeal_to_authority": "Using authority as sole evidence without substance.",
            "bandwagon": "Assuming something is true because many believe it.",
            "false_cause": "Assuming causation from correlation or sequence.",
            "red_herring": "Introducing an irrelevant topic to divert attention."
        }
        return explanations.get(fallacy, "Unknown fallacy.")

    def stats(self, text: str) -> Dict:
        return {"detected": self.detect(text), "score": self.overall_fallacy_score(text), "primary": self.classify(text)}

def run():
    fd = FallacyDetector()
    text = "You are wrong because you are a bad person. Everyone knows this is true."
    print(fd.stats(text))
    print("Explain:", fd.explain(fd.classify(text)))

if __name__ == "__main__":
    run()
