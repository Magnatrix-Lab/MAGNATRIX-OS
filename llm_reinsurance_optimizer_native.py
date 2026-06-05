"""Reinsurance Optimizer — ceding, retention, layers, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ReinsuranceOptimizer:
    total_exposure: float = 1000000.0
    retention: float = 100000.0
    premium: float = 50000.0

    def ceded_amount(self, loss: float) -> float:
        if loss <= self.retention:
            return 0.0
        return min(loss - self.retention, self.total_exposure - self.retention)

    def retained_amount(self, loss: float) -> float:
        return min(loss, self.retention)

    def cession_ratio(self) -> float:
        return (self.total_exposure - self.retention) / self.total_exposure if self.total_exposure > 0 else 0.0

    def layer_structure(self, layers: List[Tuple[float, float]]) -> List[Dict]:
        """Layers as (attachment, limit)"""
        result = []
        for attach, limit in layers:
            result.append({"attach": attach, "limit": limit, "capacity": limit - attach})
        return result

    def cost_efficiency(self, expected_loss: float) -> float:
        return expected_loss / self.premium if self.premium > 0 else 0.0

    def stats(self, loss: float = 500000) -> Dict:
        return {
            "ceded": round(self.ceded_amount(loss), 0),
            "retained": round(self.retained_amount(loss), 0),
            "cession_ratio": round(self.cession_ratio(), 3)
        }

def run():
    ro = ReinsuranceOptimizer(retention=200000, premium=75000)
    print(ro.stats(600000))
    print("Layers:", ro.layer_structure([(200000, 500000), (500000, 1000000)]))

if __name__ == "__main__":
    run()
