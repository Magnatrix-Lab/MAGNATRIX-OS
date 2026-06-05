"""Native stdlib module: Pollen Calendar
Tracks pollen flow periods and nectar yields by season and flora.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class FlowPeriod:
    plant_name: str
    start_month: int
    end_month: int
    nectar_flow_rating: float
    pollen_rating: float

@dataclass
class PollenCalendar:
    apiary_name: str
    flow_periods: List[FlowPeriod] = field(default_factory=list)

    def active_flows(self, month: int) -> List[FlowPeriod]:
        return [f for f in self.flow_periods if f.start_month <= month <= f.end_month]

    def total_nectar_rating(self, month: int) -> float:
        return sum(f.nectar_flow_rating for f in self.active_flows(month))

    def total_pollen_rating(self, month: int) -> float:
        return sum(f.pollen_rating for f in self.active_flows(month))

    def best_month(self) -> int:
        if not self.flow_periods:
            return 0
        month_scores = {}
        for m in range(1, 13):
            month_scores[m] = self.total_nectar_rating(m) + self.total_pollen_rating(m)
        return max(month_scores, key=month_scores.get)

    def stats(self, month: int = 0) -> Dict:
        return {
            "apiary": self.apiary_name,
            "active_flows": len(self.active_flows(month)) if month else 0,
            "total_nectar_rating": round(self.total_nectar_rating(month), 1) if month else None,
            "total_pollen_rating": round(self.total_pollen_rating(month), 1) if month else None,
            "best_month": self.best_month(),
        }

def run():
    pc = PollenCalendar(
        apiary_name="Spring Valley",
        flow_periods=[
            FlowPeriod("Dandelion", 3, 5, 3.0, 4.0),
            FlowPeriod("Clover", 5, 7, 5.0, 3.5),
            FlowPeriod("Basswood", 6, 7, 4.5, 2.0),
            FlowPeriod("Goldenrod", 8, 9, 3.5, 4.5),
            FlowPeriod("Aster", 9, 10, 2.5, 3.0),
        ]
    )
    print(pc.stats(month=6))

if __name__ == "__main__":
    run()
