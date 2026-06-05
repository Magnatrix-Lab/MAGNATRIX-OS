"""Confectionery Thermometer — caramel, fudge, toffee, praline, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ConfectioneryThermometer:
    temp: float = 100.0

    def stage(self) -> str:
        if self.temp < 110: return "thread"
        elif self.temp < 115: return "soft ball"
        elif self.temp < 118: return "firm ball"
        elif self.temp < 121: return "hard ball"
        elif self.temp < 132: return "soft crack"
        elif self.temp < 146: return "hard crack"
        elif self.temp < 154: return "clear liquid"
        elif self.temp < 182: return "caramel"
        return "burnt"

    def suitable_for(self) -> str:
        stages = {
            "thread": "syrups, meringue",
            "soft ball": "fudge, praline",
            "firm ball": "caramel",
            "hard ball": "nougat",
            "soft crack": "taffy, butterscotch",
            "hard crack": "lollipops, brittles",
            "caramel": "caramel sauce, flan",
        }
        return stages.get(self.stage(), "unknown")

    def water_content(self) -> float:
        return max(0, 30 - (self.temp - 100) * 0.3)

    def stats(self) -> Dict:
        return {"stage": self.stage(), "use": self.suitable_for(), "water": round(self.water_content(), 1)}

def run():
    for t in [110, 120, 140, 160, 190]:
        print(ConfectioneryThermometer(t).stats())

if __name__ == "__main__":
    run()
