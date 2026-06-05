"""Chocolate Temper — crystal forms, temper curve, snap test, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ChocolateTemper:
    chocolate_type: str = "dark"
    current_temp: float = 45.0

    def temper_curve(self) -> Dict[str, float]:
        curves = {
            "dark": {"melt": 50, "cool": 27, "reheat": 31},
            "milk": {"melt": 45, "cool": 26, "reheat": 29},
            "white": {"melt": 43, "cool": 25, "reheat": 28},
        }
        return curves.get(self.chocolate_type, curves["dark"])

    def crystal_form(self) -> str:
        if self.current_temp < 17: return "I (unstable)"
        elif self.current_temp < 21: return "II"
        elif self.current_temp < 26: return "III"
        elif self.current_temp < 28: return "IV"
        elif self.current_temp < 32: return "V (stable)"
        elif self.current_temp < 35: return "VI"
        return "melted"

    def is_tempered(self) -> bool:
        c = self.temper_curve()
        return c["cool"] <= self.current_temp <= c["reheat"]

    def temper_index(self) -> float:
        c = self.temper_curve()
        target = (c["cool"] + c["reheat"]) / 2
        return 1 - abs(self.current_temp - target) / 10

    def stats(self) -> Dict:
        return {"crystal": self.crystal_form(), "tempered": self.is_tempered(), "index": round(self.temper_index(), 2)}

def run():
    ct = ChocolateTemper("milk", 28)
    print(ct.stats())
    print("Curve:", ct.temper_curve())

if __name__ == "__main__":
    run()
