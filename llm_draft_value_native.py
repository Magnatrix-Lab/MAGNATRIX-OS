"""Native stdlib module: Draft Value Calculator
Calculates draft pick value and trade fairness using value charts.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class DraftPick:
    round: int
    pick_number: int

@dataclass
class DraftValueCalculator:
    picks: List[DraftPick] = field(default_factory=list)
    received_picks: List[DraftPick] = field(default_factory=list)

    def _pick_value(self, pick: DraftPick) -> float:
        if pick.pick_number <= 1:
            return 3000
        elif pick.pick_number <= 10:
            return 3000 - (pick.pick_number - 1) * 150
        elif pick.pick_number <= 32:
            return 1650 - (pick.pick_number - 10) * 40
        elif pick.pick_number <= 64:
            return 800 - (pick.pick_number - 32) * 15
        elif pick.pick_number <= 100:
            return 350 - (pick.pick_number - 64) * 8
        elif pick.pick_number <= 150:
            return 100 - (pick.pick_number - 100) * 1.5
        else:
            return max(10, 50 - (pick.pick_number - 150) * 0.5)

    def total_value_given(self) -> float:
        return sum(self._pick_value(p) for p in self.picks)

    def total_value_received(self) -> float:
        return sum(self._pick_value(p) for p in self.received_picks)

    def trade_fairness(self) -> str:
        if self.total_value_given() == 0:
            return "no_trade"
        ratio = self.total_value_received() / self.total_value_given()
        if 0.9 <= ratio <= 1.1:
            return "fair"
        elif ratio > 1.1:
            return "favorable"
        return "unfavorable"

    def stats(self) -> Dict:
        return {
            "value_given": round(self.total_value_given(), 1),
            "value_received": round(self.total_value_received(), 1),
            "fairness": self.trade_fairness(),
            "picks_given": len(self.picks),
            "picks_received": len(self.received_picks),
        }

def run():
    dvc = DraftValueCalculator(
        picks=[DraftPick(1, 15)],
        received_picks=[DraftPick(1, 25), DraftPick(2, 50), DraftPick(4, 120)]
    )
    print(dvc.stats())

if __name__ == "__main__":
    run()
