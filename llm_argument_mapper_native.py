"""Argument Mapper — premises, conclusions, fallacy detection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

@dataclass
class Argument:
    premises: List[str] = field(default_factory=list)
    conclusion: str = ""

class ArgumentMapper:
    def __init__(self):
        self.arguments: List[Argument] = []
        self.fallacy_patterns = {
            "ad_hominem": ["you are", "your character", "irrelevant person"],
            "straw_man": ["so you are saying", "exaggerated", "distorted"],
            "false_dichotomy": ["either or", "only two options", "black and white"],
            "slippery_slope": ["if we allow", "next thing", "cascade", "inevitably lead"],
            "hasty_generalization": ["all", "never", "always", "everyone knows"]
        }

    def add_argument(self, arg: Argument):
        self.arguments.append(arg)

    def check_validity(self, arg: Argument) -> bool:
        return len(arg.premises) > 0 and bool(arg.conclusion)

    def detect_fallacies(self, text: str) -> Dict[str, float]:
        text_lower = text.lower()
        scores = {}
        for fallacy, markers in self.fallacy_patterns.items():
            count = sum(1 for m in markers if m in text_lower)
            scores[fallacy] = min(1.0, count / 2)
        return scores

    def strength(self, arg: Argument) -> float:
        if not arg.premises or not arg.conclusion:
            return 0.0
        return min(1.0, len(arg.premises) / 3 + 0.3)

    def map_structure(self) -> List[Dict]:
        return [{"premises": a.premises, "conclusion": a.conclusion, "strength": self.strength(a)} for a in self.arguments]

    def stats(self) -> Dict:
        return {"arguments": len(self.arguments), "avg_strength": sum(self.strength(a) for a in self.arguments) / len(self.arguments) if self.arguments else 0}

def run():
    am = ArgumentMapper()
    am.add_argument(Argument(["All men are mortal", "Socrates is a man"], "Socrates is mortal"))
    print("Structure:", am.map_structure())
    print("Fallacies:", am.detect_fallacies("You are wrong because you are a bad person."))
    print(am.stats())

if __name__ == "__main__":
    run()
