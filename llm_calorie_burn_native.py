"""Native stdlib module: Calorie Burn Calculator
Estimates calories burned by activity, duration, and body weight.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Activity(Enum):
    WALKING = "walking"
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    WEIGHTLIFTING = "weightlifting"
    YOGA = "yoga"
    HIIT = "hiit"

@dataclass
class CalorieBurnCalculator:
    activity: Activity
    duration_min: float
    weight_kg: float
    intensity: str = "moderate"

    def met_value(self) -> float:
        mets = {
            Activity.WALKING: {"light": 3.0, "moderate": 4.0, "vigorous": 5.0},
            Activity.RUNNING: {"light": 7.0, "moderate": 9.0, "vigorous": 11.0},
            Activity.CYCLING: {"light": 5.0, "moderate": 7.5, "vigorous": 10.0},
            Activity.SWIMMING: {"light": 6.0, "moderate": 8.0, "vigorous": 10.0},
            Activity.WEIGHTLIFTING: {"light": 3.0, "moderate": 4.5, "vigorous": 6.0},
            Activity.YOGA: {"light": 2.5, "moderate": 3.0, "vigorous": 4.0},
            Activity.HIIT: {"light": 8.0, "moderate": 10.0, "vigorous": 12.0},
        }
        return mets.get(self.activity, {}).get(self.intensity, 5.0)

    def calories_burned(self) -> float:
        return self.met_value() * self.weight_kg * (self.duration_min / 60)

    def calories_per_min(self) -> float:
        if self.duration_min == 0:
            return 0.0
        return self.calories_burned() / self.duration_min

    def stats(self) -> Dict:
        return {
            "activity": self.activity.value,
            "intensity": self.intensity,
            "duration_min": self.duration_min,
            "met": self.met_value(),
            "calories_burned": round(self.calories_burned(), 1),
            "calories_per_min": round(self.calories_per_min(), 1),
        }

def run():
    cb = CalorieBurnCalculator(activity=Activity.RUNNING, duration_min=45, weight_kg=70, intensity="moderate")
    print(cb.stats())

if __name__ == "__main__":
    run()
