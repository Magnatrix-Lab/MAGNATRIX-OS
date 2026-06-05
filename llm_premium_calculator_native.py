"""Premium Calculator — life, health, auto, actuarial, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class PremiumCalculator:
    age: int = 30
    gender: str = "male"
    sum_assured: float = 100000.0
    term_years: int = 20
    risk_factor: float = 1.0

    def life_premium(self) -> float:
        base = self.sum_assured / 1000 * 5
        age_factor = 1 + (self.age - 25) * 0.02
        gender_factor = 0.95 if self.gender == "female" else 1.0
        return base * age_factor * gender_factor * self.risk_factor / self.term_years

    def health_premium(self) -> float:
        base = 5000
        age_factor = 1 + (self.age - 25) * 0.03
        return base * age_factor * self.risk_factor

    def auto_premium(self, car_value: float = 20000) -> float:
        base = car_value * 0.03
        age_factor = 1.5 if self.age < 25 else 1.0 if self.age < 50 else 1.2
        return base * age_factor * self.risk_factor

    def net_present_value(self, discount_rate: float = 0.05) -> float:
        premium = self.life_premium()
        return sum(premium / ((1 + discount_rate) ** t) for t in range(1, self.term_years + 1))

    def stats(self) -> Dict:
        return {"life": round(self.life_premium(), 2), "health": round(self.health_premium(), 2), "npv": round(self.net_present_value(), 2)}

def run():
    pc = PremiumCalculator(age=45, sum_assured=500000, risk_factor=1.2)
    print(pc.stats())
    print("Auto:", pc.auto_premium(30000))

if __name__ == "__main__":
    run()
