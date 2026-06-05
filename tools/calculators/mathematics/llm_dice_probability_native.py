"""Native stdlib module: Dice Probability Calculator
Calculates probabilities for dice rolls, combinations, and success thresholds.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class DiceProbabilityCalculator:
    num_dice: int
    sides_per_die: int
    target_value: int

    def min_total(self) -> int:
        return self.num_dice

    def max_total(self) -> int:
        return self.num_dice * self.sides_per_die

    def total_combinations(self) -> int:
        return self.sides_per_die ** self.num_dice

    def probability_meet_or_exceed(self) -> float:
        if self.target_value > self.max_total():
            return 0.0
        if self.target_value <= self.min_total():
            return 1.0
        favorable = 0
        for total in range(self.target_value, self.max_total() + 1):
            favorable += self._ways_to_total(total)
        return favorable / self.total_combinations()

    def _ways_to_total(self, total: int) -> int:
        if self.num_dice == 1:
            return 1 if self.min_total() <= total <= self.max_total() else 0
        if total < self.num_dice or total > self.num_dice * self.sides_per_die:
            return 0
        count = 0
        for i in range(1, self.sides_per_die + 1):
            count += self._ways_recursive(self.num_dice - 1, total - i)
        return count

    def _ways_recursive(self, dice: int, total: int) -> int:
        if dice == 0:
            return 1 if total == 0 else 0
        if total < dice or total > dice * self.sides_per_die:
            return 0
        count = 0
        for i in range(1, self.sides_per_die + 1):
            count += self._ways_recursive(dice - 1, total - i)
        return count

    def expected_value(self) -> float:
        return self.num_dice * (self.sides_per_die + 1) / 2

    def stats(self) -> Dict:
        return {
            "num_dice": self.num_dice,
            "sides": self.sides_per_die,
            "target": self.target_value,
            "min_total": self.min_total(),
            "max_total": self.max_total(),
            "expected_value": round(self.expected_value(), 2),
            "p_meet_or_exceed": round(self.probability_meet_or_exceed(), 4),
        }

def run():
    dpc = DiceProbabilityCalculator(num_dice=2, sides_per_die=6, target_value=7)
    print(dpc.stats())

if __name__ == "__main__":
    run()
