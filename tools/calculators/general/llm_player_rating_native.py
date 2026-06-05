"""Native stdlib module: Player Rating Calculator
Calculates composite player ratings across multiple performance metrics.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Sport(Enum):
    BASKETBALL = "basketball"
    SOCCER = "soccer"
    BASEBALL = "baseball"
    TENNIS = "tennis"

@dataclass
class Metric:
    name: str
    value: float
    weight: float
    max_value: float = 100.0

@dataclass
class PlayerRatingCalculator:
    player_name: str
    sport: Sport
    metrics: List[Metric] = field(default_factory=list)

    def normalized_score(self, metric: Metric) -> float:
        if metric.max_value == 0:
            return 0.0
        return (metric.value / metric.max_value) * 100

    def weighted_rating(self) -> float:
        total_weight = sum(m.weight for m in self.metrics)
        if total_weight == 0:
            return 0.0
        return sum(self.normalized_score(m) * m.weight for m in self.metrics) / total_weight

    def overall_rating(self) -> float:
        return max(0, min(100, self.weighted_rating()))

    def top_metric(self) -> str:
        if not self.metrics:
            return ""
        return max(self.metrics, key=lambda m: self.normalized_score(m)).name

    def stats(self) -> Dict:
        return {
            "player": self.player_name,
            "sport": self.sport.value,
            "overall_rating": round(self.overall_rating(), 1),
            "top_metric": self.top_metric(),
            "metrics_count": len(self.metrics),
        }

def run():
    pr = PlayerRatingCalculator(
        player_name="LeBron",
        sport=Sport.BASKETBALL,
        metrics=[
            Metric("points", 27.0, 2.0, 40.0),
            Metric("rebounds", 7.5, 1.5, 15.0),
            Metric("assists", 7.0, 1.5, 15.0),
            Metric("steals", 1.2, 1.0, 3.0),
            Metric("blocks", 0.8, 1.0, 3.0),
        ]
    )
    print(pr.stats())

if __name__ == "__main__":
    run()
