"""Native stdlib module: Smokehouse Timer
Schedules smoking stages by temperature, humidity, and time for cured meats.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class WoodType(Enum):
    HICKORY = "hickory"
    APPLE = "apple"
    MESQUITE = "mesquite"
    CHERRY = "cherry"
    OAK = "oak"

@dataclass
class SmokeStage:
    name: str
    temp_c: float
    humidity_pct: float
    hours: float

@dataclass
class SmokehouseTimer:
    product_name: str
    target_internal_temp_c: float
    wood: WoodType
    stages: List[SmokeStage] = field(default_factory=list)

    def total_time_hours(self) -> float:
        return sum(s.hours for s in self.stages)

    def average_temp(self) -> float:
        if not self.stages:
            return 0.0
        total = sum(s.temp_c * s.hours for s in self.stages)
        return total / self.total_time_hours()

    def stats(self) -> Dict[str, float]:
        return {
            "total_hours": round(self.total_time_hours(), 1),
            "avg_temp_c": round(self.average_temp(), 1),
            "target_internal_c": self.target_internal_temp_c,
            "stages": len(self.stages),
        }

def run():
    timer = SmokehouseTimer(
        product_name="Bacon",
        target_internal_temp_c=65,
        wood=WoodType.APPLE,
        stages=[
            SmokeStage("drying", 43, 70, 2),
            SmokeStage("smoking", 60, 60, 4),
            SmokeStage("finishing", 74, 55, 1),
        ]
    )
    print(timer.stats())

if __name__ == "__main__":
    run()
