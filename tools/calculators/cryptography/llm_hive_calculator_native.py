"""Native stdlib module: Hive Calculator
Calculates hive productivity, honey yield, and colony strength metrics.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class HiveType(Enum):
    LANGSTROTH = "langstroth"
    WARRÉ = "warre"
    TOP_BAR = "top_bar"
    FLOW = "flow"

@dataclass
class HiveCalculator:
    hive_type: HiveType
    num_colonies: int
    frames_per_hive: int
    honey_per_frame_kg: float = 1.5
    bees_per_frame: int = 2000

    def total_honey_potential_kg(self) -> float:
        return self.num_colonies * self.frames_per_hive * self.honey_per_frame_kg

    def estimated_population(self) -> int:
        return self.num_colonies * self.frames_per_hive * self.bees_per_frame

    def honey_per_colony_kg(self) -> float:
        return self.frames_per_hive * self.honey_per_frame_kg

    def revenue(self, price_per_kg: float) -> float:
        return self.total_honey_potential_kg() * price_per_kg

    def stats(self, price_per_kg: float = 0) -> Dict:
        return {
            "hive_type": self.hive_type.value,
            "colonies": self.num_colonies,
            "total_honey_potential_kg": round(self.total_honey_potential_kg(), 1),
            "estimated_population": self.estimated_population(),
            "honey_per_colony_kg": round(self.honey_per_colony_kg(), 1),
            "revenue": round(self.revenue(price_per_kg), 2) if price_per_kg else None,
        }

def run():
    hc = HiveCalculator(hive_type=HiveType.LANGSTROTH, num_colonies=20, frames_per_hive=10, honey_per_frame_kg=1.8, bees_per_frame=2500)
    print(hc.stats(price_per_kg=15))

if __name__ == "__main__":
    run()
