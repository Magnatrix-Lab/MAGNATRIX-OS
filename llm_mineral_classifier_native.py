"""Mineral Classifier — hardness, luster, streak, density, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

@dataclass
class Mineral:
    name: str
    hardness: float
    density: float
    luster: str
    streak: str
    cleavage: str

class MineralClassifier:
    def __init__(self):
        self.minerals: List[Mineral] = []

    def add_mineral(self, m: Mineral):
        self.minerals.append(m)

    def classify(self, hardness: float, density: float, luster: str, streak: str) -> List[str]:
        matches = []
        for m in self.minerals:
            score = 0
            if abs(m.hardness - hardness) < 1: score += 1
            if abs(m.density - density) < 1: score += 1
            if m.luster == luster: score += 1
            if m.streak == streak: score += 1
            if score >= 3:
                matches.append(m.name)
        return matches

    def mohs_scale(self, hardness: float) -> str:
        if hardness < 2.5: return "fingernail"
        elif hardness < 5.5: return "knife"
        elif hardness < 6.5: return "glass"
        elif hardness < 7.5: return "steel"
        return "quartz"

    def specific_gravity(self, weight_air: float, weight_water: float) -> float:
        if weight_water <= 0:
            return 0.0
        return weight_air / (weight_air - weight_water)

    def stats(self) -> Dict:
        return {"minerals": len(self.minerals), "hardness_range": (min(m.hardness for m in self.minerals), max(m.hardness for m in self.minerals)) if self.minerals else (0, 0)}

def run():
    mc = MineralClassifier()
    mc.add_mineral(Mineral("Quartz", 7, 2.65, "vitreous", "white", "none"))
    mc.add_mineral(Mineral("Feldspar", 6, 2.56, "vitreous", "white", "good"))
    mc.add_mineral(Mineral("Calcite", 3, 2.71, "vitreous", "white", "perfect"))
    print("Classify:", mc.classify(7, 2.65, "vitreous", "white"))
    print(mc.stats())

if __name__ == "__main__":
    run()
