"""Native stdlib module: Chocolate Tempering Calculator
Calculates tempering curves, crystal formation, and target temperatures.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ChocolateTemperingCalculator:
    chocolate_type: str  # dark, milk, white, ruby
    batch_weight_kg: float = 1.0

    _TEMP_RANGES = {
        "dark": {"melt": 50, "cool": 27, "reheat": 31},
        "milk": {"melt": 45, "cool": 26, "reheat": 29},
        "white": {"melt": 43, "cool": 25, "reheat": 28},
        "ruby": {"melt": 45, "cool": 26, "reheat": 29},
    }

    def melt_temp_c(self) -> int:
        return self._TEMP_RANGES.get(self.chocolate_type, {}).get("melt", 50)

    def cool_temp_c(self) -> int:
        return self._TEMP_RANGES.get(self.chocolate_type, {}).get("cool", 27)

    def reheat_temp_c(self) -> int:
        return self._TEMP_RANGES.get(self.chocolate_type, {}).get("reheat", 31)

    def seed_chocolate_pct(self) -> float:
        return 20.0

    def seed_weight_g(self) -> float:
        return self.batch_weight_kg * 1000 * (self.seed_chocolate_pct() / 100)

    def tempering_time_min(self) -> float:
        return 20 + self.batch_weight_kg * 5

    def working_time_min(self) -> float:
        return 15 + self.batch_weight_kg * 3

    def cocoa_butter_content_pct(self) -> float:
        contents = {"dark": 55, "milk": 35, "white": 38, "ruby": 36}
        return contents.get(self.chocolate_type, 50)

    def crystal_type_target(self) -> str:
        return "form_V_beta"

    def stats(self) -> Dict:
        return {
            "chocolate_type": self.chocolate_type,
            "melt_temp_c": self.melt_temp_c(),
            "cool_temp_c": self.cool_temp_c(),
            "reheat_temp_c": self.reheat_temp_c(),
            "seed_chocolate_pct": self.seed_chocolate_pct(),
            "seed_weight_g": round(self.seed_weight_g(), 1),
            "tempering_time_min": round(self.tempering_time_min(), 1),
            "working_time_min": round(self.working_time_min(), 1),
            "cocoa_butter_content_pct": self.cocoa_butter_content_pct(),
            "target_crystal": self.crystal_type_target(),
        }

def run():
    ctc = ChocolateTemperingCalculator(chocolate_type="dark", batch_weight_kg=2)
    print(ctc.stats())

if __name__ == "__main__":
    run()
