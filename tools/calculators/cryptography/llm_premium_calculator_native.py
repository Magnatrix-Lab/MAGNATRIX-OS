"""Native stdlib module: Premium Calculator
Calculates insurance premiums by risk factors, coverage, and deductibles.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class PolicyType(Enum):
    AUTO = "auto"
    HOME = "home"
    LIFE = "life"
    HEALTH = "health"
    BUSINESS = "business"

@dataclass
class PremiumCalculator:
    policy_type: PolicyType
    base_premium: float
    coverage_amount: float
    deductible: float
    risk_factor: float = 1.0
    age: int = 35
    claim_history: int = 0

    def deductible_discount_pct(self) -> float:
        if self.deductible >= 1000:
            return 15
        elif self.deductible >= 500:
            return 10
        elif self.deductible >= 250:
            return 5
        return 0

    def age_factor(self) -> float:
        if self.policy_type == PolicyType.LIFE:
            if self.age < 30:
                return 0.8
            elif self.age < 50:
                return 1.0
            elif self.age < 65:
                return 1.5
            return 2.5
        elif self.policy_type == PolicyType.AUTO:
            if self.age < 25:
                return 1.5
            elif self.age < 40:
                return 1.0
            return 0.9
        return 1.0

    def claim_surcharge_pct(self) -> float:
        return self.claim_history * 10

    def calculated_premium(self) -> float:
        premium = self.base_premium * self.risk_factor * self.age_factor()
        premium *= (1 - self.deductible_discount_pct() / 100)
        premium *= (1 + self.claim_surcharge_pct() / 100)
        return premium

    def stats(self) -> Dict:
        return {
            "policy_type": self.policy_type.value,
            "base_premium": self.base_premium,
            "calculated_premium": round(self.calculated_premium(), 2),
            "age_factor": round(self.age_factor(), 2),
            "deductible_discount_pct": self.deductible_discount_pct(),
            "claim_surcharge_pct": self.claim_surcharge_pct(),
        }

def run():
    pc = PremiumCalculator(policy_type=PolicyType.AUTO, base_premium=800, coverage_amount=50000, deductible=500, risk_factor=1.1, age=28, claim_history=1)
    print(pc.stats())

if __name__ == "__main__":
    run()
