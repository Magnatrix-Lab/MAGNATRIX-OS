"""Native stdlib module: Rennet Calculator
Determines rennet quantity based on milk type, temperature, and coagulation time.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class RennetType(Enum):
    ANIMAL = "animal"
    VEGETABLE = "vegetable"
    MICROBIAL = "microbial"
    CHY_MAX = "chy_max"

@dataclass
class RennetCalculator:
    milk_liters: float
    coagulation_time_min: float
    temp_c: float
    rennet_type: RennetType
    strength_imcu: int = 200

    def base_rennet_ml(self) -> float:
        return (self.milk_liters * 30) / self.strength_imcu

    def temp_factor(self) -> float:
        return 1.0 + (32 - self.temp_c) * 0.02

    def adjusted_rennet_ml(self) -> float:
        return self.base_rennet_ml() * self.temp_factor()

    def stats(self) -> Dict[str, float]:
        return {
            "base_rennet_ml": round(self.base_rennet_ml(), 3),
            "adjusted_rennet_ml": round(self.adjusted_rennet_ml(), 3),
            "temp_factor": round(self.temp_factor(), 3),
        }

def run():
    rc = RennetCalculator(milk_liters=50, coagulation_time_min=45, temp_c=32, rennet_type=RennetType.ANIMAL, strength_imcu=220)
    print(rc.stats())

if __name__ == "__main__":
    run()
