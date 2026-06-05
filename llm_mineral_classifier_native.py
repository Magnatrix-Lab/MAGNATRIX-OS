"""Mineral Classifier — hardness, streak, luster, cleavage, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class MineralClassifier:
    hardness: float = 0.0
    streak: str = ""
    luster: str = ""
    cleavage: str = ""
    color: str = ""
    specific_gravity: float = 0.0

    def match(self, candidates: List[Dict]) -> List[str]:
        matches = []
        for c in candidates:
            score = 0
            if abs(c.get("hardness", 0) - self.hardness) < 1: score += 1
            if c.get("streak", "") == self.streak: score += 1
            if c.get("luster", "") == self.luster: score += 1
            if c.get("cleavage", "") == self.cleavage: score += 1
            if score >= 2:
                matches.append(c.get("name", ""))
        return matches

    def mohs_comparison(self, other_hardness: float) -> str:
        if self.hardness > other_hardness:
            return "can scratch"
        elif self.hardness < other_hardness:
            return "can be scratched by"
        return "same hardness"

    def density_estimate(self, mass_g: float, volume_ml: float) -> float:
        return mass_g / volume_ml if volume_ml > 0 else 0.0

    def stats(self) -> Dict:
        return {"hardness": self.hardness, "luster": self.luster, "sg": self.specific_gravity}

def run():
    mc = MineralClassifier(hardness=7, streak="white", luster="vitreous", color="purple")
    candidates = [
        {"name": "Quartz", "hardness": 7, "streak": "white", "luster": "vitreous"},
        {"name": "Amethyst", "hardness": 7, "streak": "white", "luster": "vitreous"},
    ]
    print("Match:", mc.match(candidates))
    print(mc.stats())

if __name__ == "__main__":
    run()
