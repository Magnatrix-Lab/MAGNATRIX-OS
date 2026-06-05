"""Native stdlib module: Staking Yield Calculator
Calculates staking rewards, APY, and compounding returns.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class StakingYieldCalculator:
    principal: float
    apr_pct: float
    compounding_frequency: int = 365
    staking_period_days: int = 365
    validator_fee_pct: float = 5.0

    def effective_apr(self) -> float:
        return self.apr_pct * (1 - self.validator_fee_pct / 100)

    def apy(self) -> float:
        r = self.effective_apr() / 100
        n = self.compounding_frequency
        return ((1 + r / n) ** n - 1) * 100

    def total_reward(self) -> float:
        r = self.effective_apr() / 100
        n = self.compounding_frequency
        t = self.staking_period_days / 365
        return self.principal * ((1 + r / n) ** (n * t) - 1)

    def total_value(self) -> float:
        return self.principal + self.total_reward()

    def monthly_reward(self) -> float:
        return self.total_reward() / (self.staking_period_days / 30)

    def daily_reward(self) -> float:
        return self.total_reward() / self.staking_period_days

    def inflation_adjusted_yield(self, inflation_pct: float) -> float:
        return self.effective_apr() - inflation_pct

    def stats(self, inflation_pct: float = 0) -> Dict:
        return {
            "principal": self.principal,
            "apr_pct": self.apr_pct,
            "effective_apr_pct": round(self.effective_apr(), 2),
            "apy_pct": round(self.apy(), 2),
            "total_reward": round(self.total_reward(), 4),
            "total_value": round(self.total_value(), 4),
            "monthly_reward": round(self.monthly_reward(), 4),
            "daily_reward": round(self.daily_reward(), 4),
            "real_yield_pct": round(self.inflation_adjusted_yield(inflation_pct), 2) if inflation_pct else None,
        }

def run():
    syc = StakingYieldCalculator(principal=1000, apr_pct=8, compounding_frequency=365, staking_period_days=365, validator_fee_pct=5)
    print(syc.stats(inflation_pct=3))

if __name__ == "__main__":
    run()
