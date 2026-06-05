"""Native stdlib module: Anchorage Calculator
Calculates anchor holding power, chain length, and swinging circle for vessels.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class BottomType(Enum):
    MUD = "mud"
    SAND = "sand"
    CLAY = "clay"
    ROCK = "rock"
    GRASS = "grass"

class AnchorType(Enum):
    STOCKLESS = "stockless"
    DANFORTH = "danforth"
    PLOW = "plow"
    CLAW = "claw"

@dataclass
class AnchorageCalculator:
    vessel_displacement_ton: float
    wind_speed_kts: float
    current_speed_kts: float
    water_depth_m: float
    bottom_type: BottomType
    anchor_type: AnchorType

    def holding_power_required_kn(self) -> float:
        wind_force = 0.001 * (self.wind_speed_kts ** 2) * self.vessel_displacement_ton ** 0.67
        current_force = 0.5 * self.vessel_displacement_ton ** 0.67 * (self.current_speed_kts ** 2)
        return wind_force + current_force

    def anchor_holding_factor(self) -> float:
        factors = {
            (AnchorType.STOCKLESS, BottomType.MUD): 4,
            (AnchorType.STOCKLESS, BottomType.SAND): 3,
            (AnchorType.DANFORTH, BottomType.SAND): 8,
            (AnchorType.DANFORTH, BottomType.MUD): 6,
            (AnchorType.PLOW, BottomType.MUD): 6,
            (AnchorType.PLOW, BottomType.SAND): 5,
            (AnchorType.CLAW, BottomType.MUD): 5,
            (AnchorType.CLAW, BottomType.SAND): 4,
        }
        return factors.get((self.anchor_type, self.bottom_type), 3)

    def required_anchor_weight_kg(self) -> float:
        if self.anchor_holding_factor() == 0:
            return 0.0
        return (self.holding_power_required_kn() * 1000) / (self.anchor_holding_factor() * 9.81)

    def chain_length_m(self, scope_ratio: float = 5) -> float:
        return self.water_depth_m * scope_ratio

    def swinging_circle_radius_m(self, chain_length_m: float = 0) -> float:
        cl = chain_length_m if chain_length_m else self.chain_length_m()
        return cl + self.vessel_displacement_ton ** 0.33

    def stats(self) -> Dict:
        return {
            "holding_power_required_kn": round(self.holding_power_required_kn(), 1),
            "anchor_holding_factor": self.anchor_holding_factor(),
            "required_anchor_weight_kg": round(self.required_anchor_weight_kg(), 1),
            "chain_length_m": round(self.chain_length_m(), 1),
            "swinging_circle_m": round(self.swinging_circle_radius_m(), 1),
        }

def run():
    ac = AnchorageCalculator(vessel_displacement_ton=50000, wind_speed_kts=30, current_speed_kts=2, water_depth_m=50, bottom_type=BottomType.MUD, anchor_type=AnchorType.STOCKLESS)
    print(ac.stats())

if __name__ == "__main__":
    run()
