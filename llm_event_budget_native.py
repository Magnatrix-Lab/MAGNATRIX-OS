"""Native stdlib module: Event Budget Calculator
Tracks event budgets by category with actual vs planned spending.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class BudgetStatus(Enum):
    UNDER = "under"
    ON_TRACK = "on_track"
    OVER = "over"

@dataclass
class BudgetLine:
    category: str
    planned: float
    actual: float

@dataclass
class EventBudget:
    event_name: str
    date: str
    lines: List[BudgetLine] = field(default_factory=list)

    def total_planned(self) -> float:
        return sum(l.planned for l in self.lines)

    def total_actual(self) -> float:
        return sum(l.actual for l in self.lines)

    def variance(self) -> float:
        return self.total_actual() - self.total_planned()

    def variance_pct(self) -> float:
        if self.total_planned() == 0:
            return 0.0
        return (self.variance() / self.total_planned()) * 100

    def status(self) -> BudgetStatus:
        vp = self.variance_pct()
        if vp > 5:
            return BudgetStatus.OVER
        elif vp < -5:
            return BudgetStatus.UNDER
        return BudgetStatus.ON_TRACK

    def stats(self) -> Dict:
        return {
            "event": self.event_name,
            "total_planned": round(self.total_planned(), 2),
            "total_actual": round(self.total_actual(), 2),
            "variance": round(self.variance(), 2),
            "variance_pct": round(self.variance_pct(), 2),
            "status": self.status().value,
        }

def run():
    eb = EventBudget(
        event_name="Annual Gala",
        date="2024-09-15",
        lines=[
            BudgetLine("venue", 15000, 14800),
            BudgetLine("catering", 25000, 26500),
            BudgetLine("entertainment", 8000, 7500),
            BudgetLine("decor", 5000, 5200),
            BudgetLine("marketing", 3000, 2800),
        ]
    )
    print(eb.stats())

if __name__ == "__main__":
    run()
