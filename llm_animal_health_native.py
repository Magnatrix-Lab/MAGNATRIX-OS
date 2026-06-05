"""Animal Health Monitor — vital signs, temperature, behavior, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class AnimalHealthMonitor:
    species: str = "cattle"
    weight_kg: float = 500.0
    temperature: float = 38.5
    heart_rate: float = 60.0
    respiration: float = 20.0

    def normal_range(self, metric: str) -> Tuple[float, float]:
        ranges = {
            "temperature": {"cattle": (38.0, 39.2), "horse": (37.5, 38.5), "dog": (38.0, 39.2), "cat": (38.0, 39.2)},
            "heart_rate": {"cattle": (40, 80), "horse": (28, 40), "dog": (60, 140), "cat": (120, 180)},
            "respiration": {"cattle": (10, 30), "horse": (8, 16), "dog": (10, 30), "cat": (20, 30)}
        }
        return ranges.get(metric, {}).get(self.species, (0, 0))

    def check_vital(self, metric: str, value: float) -> str:
        low, high = self.normal_range(metric)
        if value < low: return "low"
        if value > high: return "high"
        return "normal"

    def health_score(self) -> float:
        checks = [
            self.check_vital("temperature", self.temperature),
            self.check_vital("heart_rate", self.heart_rate),
            self.check_vital("respiration", self.respiration)
        ]
        normal = sum(1 for c in checks if c == "normal")
        return normal / len(checks) if checks else 0.0

    def dosage(self, drug_mg_per_kg: float) -> float:
        return self.weight_kg * drug_mg_per_kg

    def bcs_estimate(self, body_condition: int) -> str:
        if body_condition < 3: return "underweight"
        elif body_condition > 7: return "overweight"
        return "ideal"

    def stats(self) -> Dict:
        return {
            "health_score": round(self.health_score(), 2),
            "temp_status": self.check_vital("temperature", self.temperature),
            "hr_status": self.check_vital("heart_rate", self.heart_rate),
            "resp_status": self.check_vital("respiration", self.respiration)
        }

def run():
    ahm = AnimalHealthMonitor(species="horse", temperature=39.5, heart_rate=45, respiration=20)
    print(ahm.stats())
    print("Dosage:", ahm.dosage(2.5))

if __name__ == "__main__":
    run()
