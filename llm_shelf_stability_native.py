"""Shelf Stability — pH, oxidation, preservation, challenge, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class ShelfStability:
    pH: float = 6.0
    water_activity: float = 0.8
    preservative_pct: float = 0.5
    antioxidant_pct: float = 0.1
    packaging: str = "jar"

    def microbial_risk(self) -> str:
        if self.water_activity > 0.9 and self.pH > 4.5 and self.preservative_pct < 0.5:
            return "high"
        elif self.water_activity > 0.85:
            return "moderate"
        return "low"

    def oxidation_rate(self, temp: float = 25) -> float:
        base = 0.01
        return base * math.exp(0.1 * (temp - 25)) * (1 - self.antioxidant_pct * 5)

    def shelf_life_days(self) -> int:
        risk = self.microbial_risk()
        if risk == "high":
            return 30
        elif risk == "moderate":
            return 180
        if self.packaging == "airless":
            return 730
        return 365

    def challenge_test_pass(self, inoculum: float = 1000) -> bool:
        reduction = self.preservative_pct * 2000
        return reduction >= inoculum

    def stats(self) -> Dict:
        return {"risk": self.microbial_risk(), "shelf_life": self.shelf_life_days(), "oxidation": round(self.oxidation_rate(), 4)}

def run():
    ss = ShelfStability(pH=7.5, water_activity=0.92, preservative_pct=0.3, packaging="jar")
    print(ss.stats())
    print("Challenge test:", ss.challenge_test_pass())

if __name__ == "__main__":
    run()
