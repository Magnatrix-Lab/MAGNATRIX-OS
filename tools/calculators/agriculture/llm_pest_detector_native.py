"""Pest Detector — population model, threshold, IPM, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class PestDetector:
    population: float = 100.0
    growth_rate: float = 0.1
    carrying_capacity: float = 10000.0
    threshold: float = 500.0

    def logistic_growth(self, days: int) -> List[float]:
        pops = [self.population]
        for _ in range(days):
            p = pops[-1]
            p = p + self.growth_rate * p * (1 - p / self.carrying_capacity)
            pops.append(p)
        return pops

    def detection_probability(self, sample_size: int) -> float:
        if self.population == 0:
            return 0.0
        p_per_unit = self.population / self.carrying_capacity
        return 1 - (1 - p_per_unit) ** sample_size

    def action_threshold(self, current: float) -> str:
        if current < self.threshold * 0.5:
            return "monitor"
        elif current < self.threshold:
            return "preventive"
        else:
            return "control"

    def spray_efficacy(self, mortality: float = 0.8) -> float:
        return self.population * (1 - mortality)

    def stats(self) -> Dict:
        return {"population": round(self.population, 1), "threshold": self.threshold, "action": self.action_threshold(self.population)}

def run():
    pd = PestDetector(population=300)
    print(pd.stats())
    print("Growth:", pd.logistic_growth(5)[:5])

if __name__ == "__main__":
    run()
