"""Behavioral Predictor — habit loops, nudges, choice architecture, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class BehavioralPredictor:
    habits: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    """habit -> (frequency, reward)"""
    nudges: List[Dict] = field(default_factory=list)

    def habit_strength(self, habit: str) -> float:
        freq, reward = self.habits.get(habit, (0, 0))
        return freq * reward

    def predict_adoption(self, habit: str, nudge_effectiveness: float = 0.1) -> float:
        base = self.habit_strength(habit)
        return 1 - math.exp(-base * nudge_effectiveness)

    def add_nudge(self, name: str, target: str, effect: float):
        self.nudges.append({"name": name, "target": target, "effect": effect})

    def nudge_impact(self, habit: str) -> float:
        total = 0.0
        for nudge in self.nudges:
            if nudge["target"] == habit:
                total += nudge["effect"]
        return total

    def choice_probability(self, options: List[str], utilities: List[float]) -> List[float]:
        if not utilities or sum(utilities) == 0:
            return [1/len(options)] * len(options) if options else []
        total = sum(utilities)
        return [u / total for u in utilities]

    def stats(self) -> Dict:
        return {"habits": len(self.habits), "nudges": len(self.nudges)}

def run():
    bp = BehavioralPredictor()
    bp.habits["exercise"] = (5, 0.8)
    bp.add_nudge("reminder", "exercise", 0.2)
    print("Strength:", bp.habit_strength("exercise"))
    print("Adoption:", bp.predict_adoption("exercise"))
    print("Choice:", bp.choice_probability(["A", "B"], [0.7, 0.3]))
    print(bp.stats())

if __name__ == "__main__":
    run()
