"""Exercise Prescriber -- FITT, intensity, progression, contraindications, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ExercisePrescriber:
    age: int = 30
    max_hr: int = 0
    fitness_level: str = "moderate"
    conditions: List[str] = field(default_factory=list)

    def estimated_max_hr(self) -> int:
        return 220 - self.age

    def target_hr_zone(self, intensity: str) -> Tuple[int, int]:
        max_hr = self.max_hr or self.estimated_max_hr()
        zones = {"low": (0.5, 0.6), "moderate": (0.6, 0.7), "vigorous": (0.7, 0.85), "max": (0.85, 0.95)}
        low, high = zones.get(intensity, (0.6, 0.7))
        return int(max_hr * low), int(max_hr * high)

    def fitt_recommendation(self, goal: str) -> Dict:
        plans = {
            "strength": {"frequency": 3, "intensity": "moderate", "time": 45, "type": "resistance"},
            "cardio": {"frequency": 5, "intensity": "moderate", "time": 30, "type": "aerobic"},
            "flexibility": {"frequency": 7, "intensity": "low", "time": 15, "type": "stretching"},
        }
        return plans.get(goal, {"frequency": 3, "intensity": "moderate", "time": 30, "type": "mixed"})

    def contraindicated(self, exercise: str) -> bool:
        restrictions = {
            "high intensity": ["heart disease", "hypertension"],
            "heavy lifting": ["hernia", "back pain", "pregnancy"],
            "inversion": ["glaucoma", "hypertension"],
        }
        for cond in self.conditions:
            if cond in restrictions.get(exercise, []):
                return True
        return False

    def progression(self, weeks: int) -> List[float]:
        base = 0.5
        return [min(0.95, base + 0.05 * w) for w in range(weeks)]

    def stats(self) -> Dict:
        return {"max_hr": self.estimated_max_hr(), "fitness": self.fitness_level, "conditions": len(self.conditions)}

def run():
    ep = ExercisePrescriber(age=45, conditions=["hypertension"])
    print(ep.stats())
    print("Target zone:", ep.target_hr_zone("moderate"))
    print("FITT cardio:", ep.fitt_recommendation("cardio"))
    print("Contraindicated high intensity:", ep.contraindicated("high intensity"))

if __name__ == "__main__":
    run()
