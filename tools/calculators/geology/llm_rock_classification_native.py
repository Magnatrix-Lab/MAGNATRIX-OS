"""Native stdlib module: Rock Classification Calculator
Classifies rocks by mineral composition, grain size, and hardness.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class RockType(Enum):
    IGNEOUS = "igneous"
    SEDIMENTARY = "sedimentary"
    METAMORPHIC = "metamorphic"

class GrainSize(Enum):
    FINE = "fine"
    MEDIUM = "medium"
    COARSE = "coarse"

@dataclass
class MineralComponent:
    name: str
    percentage: float
    hardness_mohs: float

@dataclass
class RockClassificationCalculator:
    rock_name: str
    rock_type: RockType
    grain_size: GrainSize
    minerals: List[MineralComponent] = field(default_factory=list)
    density_g_cm3: float = 2.65

    def total_composition(self) -> float:
        return sum(m.percentage for m in self.minerals)

    def dominant_mineral(self) -> str:
        if not self.minerals:
            return "unknown"
        return max(self.minerals, key=lambda m: m.percentage).name

    def avg_hardness(self) -> float:
        if not self.minerals:
            return 0.0
        total = sum(m.percentage for m in self.minerals)
        if total == 0:
            return 0.0
        return sum(m.percentage * m.hardness_mohs for m in self.minerals) / total

    def porosity_estimate(self) -> float:
        if self.grain_size == GrainSize.FINE:
            return 30.0
        elif self.grain_size == GrainSize.MEDIUM:
            return 25.0
        return 20.0

    def stats(self) -> Dict:
        return {
            "rock": self.rock_name,
            "type": self.rock_type.value,
            "grain_size": self.grain_size.value,
            "dominant_mineral": self.dominant_mineral(),
            "avg_hardness_mohs": round(self.avg_hardness(), 1),
            "porosity_estimate_pct": self.porosity_estimate(),
            "density_g_cm3": self.density_g_cm3,
        }

def run():
    rc = RockClassificationCalculator(
        rock_name="Granite",
        rock_type=RockType.IGNEOUS,
        grain_size=GrainSize.COARSE,
        minerals=[
            MineralComponent("quartz", 30, 7.0),
            MineralComponent("feldspar", 50, 6.0),
            MineralComponent("mica", 15, 2.5),
            MineralComponent("hornblende", 5, 5.5),
        ],
        density_g_cm3=2.7
    )
    print(rc.stats())

if __name__ == "__main__":
    run()
