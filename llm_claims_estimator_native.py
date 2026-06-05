"""Claims Estimator — severity, reserve, payout, fraud flag, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ClaimsEstimator:
    damage_amount: float = 0.0
    deductible: float = 500.0
    policy_limit: float = 100000.0
    depreciation: float = 0.0

    def net_payout(self) -> float:
        net = max(0, self.damage_amount - self.deductible) * (1 - self.depreciation)
        return min(net, self.policy_limit)

    def reserve(self, uncertainty: float = 0.2) -> float:
        return self.net_payout() * (1 + uncertainty)

    def fraud_score(self, indicators: List[str]) -> float:
        score = 0.0
        if "delayed_report" in indicators:
            score += 0.2
        if "inconsistent_damage" in indicators:
            score += 0.3
        if "prior_claims" in indicators:
            score += 0.15
        if "no_police_report" in indicators:
            score += 0.1
        return min(1.0, score)

    def salvage_value(self, value: float, damage_pct: float) -> float:
        return value * (1 - damage_pct) * 0.1

    def stats(self, indicators: List[str] = None) -> Dict:
        ind = indicators or []
        return {
            "payout": round(self.net_payout(), 2),
            "reserve": round(self.reserve(), 2),
            "fraud_score": round(self.fraud_score(ind), 3)
        }

def run():
    ce = ClaimsEstimator(damage_amount=5000, deductible=1000, depreciation=0.1)
    print(ce.stats(["delayed_report", "prior_claims"]))

if __name__ == "__main__":
    run()
