"""Native stdlib module: Transaction Fee Estimator
Estimates blockchain transaction fees by gas price, complexity, and priority.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

@dataclass
class TransactionFeeEstimator:
    gas_limit: int
    base_fee_gwei: float
    max_priority_fee_gwei: float
    priority: Priority = Priority.MEDIUM

    def priority_multiplier(self) -> float:
        multipliers = {Priority.LOW: 0.8, Priority.MEDIUM: 1.0, Priority.HIGH: 1.5, Priority.URGENT: 2.5}
        return multipliers.get(self.priority, 1.0)

    def effective_priority_fee_gwei(self) -> float:
        return self.max_priority_fee_gwei * self.priority_multiplier()

    def total_fee_per_gas_gwei(self) -> float:
        return self.base_fee_gwei + self.effective_priority_fee_gwei()

    def total_fee_eth(self) -> float:
        return (self.gas_limit * self.total_fee_per_gas_gwei()) / 1e9

    def total_fee_usd(self, eth_price_usd: float) -> float:
        return self.total_fee_eth() * eth_price_usd

    def vs_legacy_savings_pct(self, legacy_gas_price_gwei: float) -> float:
        if legacy_gas_price_gwei == 0:
            return 0.0
        legacy_fee = (self.gas_limit * legacy_gas_price_gwei) / 1e9
        if legacy_fee == 0:
            return 0.0
        return ((legacy_fee - self.total_fee_eth()) / legacy_fee) * 100

    def stats(self, eth_price_usd: float = 3500, legacy_gas_price_gwei: float = 0) -> Dict:
        return {
            "gas_limit": self.gas_limit,
            "base_fee_gwei": self.base_fee_gwei,
            "priority_fee_gwei": round(self.effective_priority_fee_gwei(), 2),
            "total_fee_eth": round(self.total_fee_eth(), 6),
            "total_fee_usd": round(self.total_fee_usd(eth_price_usd), 2),
            "vs_legacy_savings_pct": round(self.vs_legacy_savings_pct(legacy_gas_price_gwei), 1) if legacy_gas_price_gwei else None,
        }

def run():
    tfe = TransactionFeeEstimator(gas_limit=21000, base_fee_gwei=25, max_priority_fee_gwei=2, priority=Priority.MEDIUM)
    print(tfe.stats(eth_price_usd=3500, legacy_gas_price_gwei=50))

if __name__ == "__main__":
    run()
