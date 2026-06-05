"""Native stdlib module: Pacing Calculator
Calculates race pacing, split times, and negative/positive splits for runners.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Split:
    distance_km: float
    time_min: float

@dataclass
class PacingCalculator:
    race_name: str
    total_distance_km: float
    target_time_min: float
    splits: List[Split] = field(default_factory=list)

    def avg_pace_min_per_km(self) -> float:
        if self.total_distance_km == 0:
            return 0.0
        return self.target_time_min / self.total_distance_km

    def avg_speed_kmh(self) -> float:
        if self.target_time_min == 0:
            return 0.0
        return (self.total_distance_km / self.target_time_min) * 60

    def split_variance(self) -> float:
        if not self.splits or len(self.splits) < 2:
            return 0.0
        paces = [s.time_min / s.distance_km for s in self.splits]
        avg_pace = sum(paces) / len(paces)
        return sum((p - avg_pace) ** 2 for p in paces) / len(paces)

    def split_type(self) -> str:
        if not self.splits or len(self.splits) < 2:
            return "even"
        first_half = sum(s.time_min for s in self.splits[:len(self.splits)//2])
        second_half = sum(s.time_min for s in self.splits[len(self.splits)//2:])
        if second_half < first_half:
            return "negative"
        elif second_half > first_half:
            return "positive"
        return "even"

    def stats(self) -> Dict:
        return {
            "race": self.race_name,
            "distance_km": self.total_distance_km,
            "target_time_min": self.target_time_min,
            "avg_pace_min_km": round(self.avg_pace_min_per_km(), 2),
            "avg_speed_kmh": round(self.avg_speed_kmh(), 2),
            "split_type": self.split_type(),
            "split_variance": round(self.split_variance(), 3),
        }

def run():
    pc = PacingCalculator(
        race_name="Marathon",
        total_distance_km=42.195,
        target_time_min=180,
        splits=[
            Split(5, 21),
            Split(5, 21.5),
            Split(5, 21),
            Split(5, 21.5),
            Split(5, 21),
            Split(5, 20.5),
            Split(5, 20),
            Split(5, 19.5),
            Split(2.195, 8.5),
        ]
    )
    print(pc.stats())

if __name__ == "__main__":
    run()
