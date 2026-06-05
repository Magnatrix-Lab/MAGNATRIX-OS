"""Ethics Calculator — utilitarian, deontological, virtue scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class EthicsCalculator:
    def utilitarian_score(self, outcomes: List[float]) -> float:
        return sum(outcomes) / len(outcomes) if outcomes else 0.0

    def deontological_score(self, rules_broken: int, total_rules: int) -> float:
        if total_rules == 0:
            return 1.0
        return 1.0 - (rules_broken / total_rules)

    def virtue_score(self, virtues_exhibited: int, total_virtues: int) -> float:
        if total_virtues == 0:
            return 0.0
        return virtues_exhibited / total_virtues

    def trolley_problem(self, lever: bool, num_on_track1: int, num_on_track2: int) -> Dict:
        if lever:
            return {"action": "pull lever", "deaths": num_on_track2, "utilitarian": -num_on_track2}
        else:
            return {"action": "do nothing", "deaths": num_on_track1, "utilitarian": -num_on_track1}

    def evaluate(self, action: str, outcomes: List[float], rules_broken: int, total_rules: int, virtues: int, total_virtues: int) -> Dict:
        return {
            "action": action,
            "utilitarian": self.utilitarian_score(outcomes),
            "deontological": self.deontological_score(rules_broken, total_rules),
            "virtue": self.virtue_score(virtues, total_virtues),
            "overall": (self.utilitarian_score(outcomes) + self.deontological_score(rules_broken, total_rules) + self.virtue_score(virtues, total_virtues)) / 3
        }

    def stats(self) -> Dict:
        return {"frameworks": ["utilitarian", "deontological", "virtue"]}

def run():
    ec = EthicsCalculator()
    print("Trolley:", ec.trolley_problem(True, 5, 1))
    print("Evaluate:", ec.evaluate("donate", [10, 8, 5], 0, 5, 4, 6))
    print(ec.stats())

if __name__ == "__main__":
    run()
