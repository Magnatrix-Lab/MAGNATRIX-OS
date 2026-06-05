"""Native stdlib module: Soldering Temperature Calculator
Calculates flow points, melting ranges, and soldering temperatures.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SolderingTemperatureCalculator:
    solder_type: str  # hard, medium, easy, extra_easy, silver, gold
    metal_type: str = "silver"  # silver, gold, copper, brass

    _FLOW_POINTS = {
        "hard": 750, "medium": 720, "easy": 700, "extra_easy": 670,
        "silver": 760, "gold": 740, "platinum": 900,
    }

    _MELTING_RANGE = {
        "hard": (745, 780), "medium": (715, 745), "easy": (690, 720),
        "extra_easy": (665, 705), "silver": (755, 780), "gold": (735, 760),
    }

    def flow_point_c(self) -> int:
        return self._FLOW_POINTS.get(self.solder_type, 720)

    def melting_range_c(self) -> tuple:
        return self._MELTING_RANGE.get(self.solder_type, (700, 730))

    def recommended_soldering_temp_c(self) -> int:
        return self.flow_point_c() + 20

    def torch_flame_type(self) -> str:
        if self.flow_point_c() < 700:
            return "neutral"
        elif self.flow_point_c() < 800:
            return "neutral_to_reducing"
        return "oxidizing"

    def heat_sinking_needed(self) -> bool:
        return self.metal_type in ["gold", "platinum"] and self.solder_type in ["hard", "medium"]

    def solder_sequence(self, existing_solder_types: list) -> str:
        if not existing_solder_types:
            return "first_solder"
        hardest = max([self._FLOW_POINTS.get(s, 0) for s in existing_solder_types])
        current = self.flow_point_c()
        if current >= hardest:
            return "wrong_order_choose_easier"
        return "correct_order"

    def stats(self, existing_solder_types: Optional[list] = None) -> Dict:
        result = {
            "solder_type": self.solder_type,
            "metal_type": self.metal_type,
            "flow_point_c": self.flow_point_c(),
            "melting_range_c": self.melting_range_c(),
            "recommended_soldering_temp_c": self.recommended_soldering_temp_c(),
            "torch_flame_type": self.torch_flame_type(),
            "heat_sinking_needed": self.heat_sinking_needed(),
        }
        if existing_solder_types is not None:
            result["solder_sequence_check"] = self.solder_sequence(existing_solder_types)
        return result

def run():
    stc = SolderingTemperatureCalculator(solder_type="medium", metal_type="silver")
    print(stc.stats(existing_solder_types=["hard"]))

if __name__ == "__main__":
    run()
