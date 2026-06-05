"""Dice Probability — combinations, expected value, critical hits, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from itertools import product

@dataclass
class DiceProbability:
    sides: int = 6
    num_dice: int = 2
    modifier: int = 0

    def all_outcomes(self) -> List[int]:
        outcomes = []
        for combo in product(range(1, self.sides + 1), repeat=self.num_dice):
            outcomes.append(sum(combo) + self.modifier)
        return outcomes

    def probability(self, target: int) -> float:
        outcomes = self.all_outcomes()
        return outcomes.count(target) / len(outcomes) if outcomes else 0.0

    def expected_value(self) -> float:
        return sum(self.all_outcomes()) / len(self.all_outcomes()) if self.all_outcomes() else 0.0

    def critical_hit_chance(self, threshold: int) -> float:
        outcomes = self.all_outcomes()
        return sum(1 for o in outcomes if o >= threshold) / len(outcomes) if outcomes else 0.0

    def distribution(self) -> Dict[int, float]:
        outcomes = self.all_outcomes()
        total = len(outcomes)
        return {i: outcomes.count(i) / total for i in set(outcomes)}

    def stats(self, threshold: int = 10) -> Dict:
        return {"expected": round(self.expected_value(), 2), "critical": round(self.critical_hit_chance(threshold), 3), "outcomes": len(self.all_outcomes())}

def run():
    dp = DiceProbability(sides=6, num_dice=3, modifier=2)
    print(dp.stats())
    print("P(12):", dp.probability(12))
    print("Distribution:", dp.distribution())

if __name__ == "__main__":
    run()
