"""Proofer — fermentation time, temp, humidity, dough rise, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Proofer:
    dough_temp: float = 24.0
    ambient_temp: float = 26.0
    humidity_pct: float = 75.0
    yeast_pct: float = 1.0

    def proof_time(self, rise_factor: float = 2.0) -> float:
        base_time = 120
        temp_factor = 2 ** ((30 - self.ambient_temp) / 10)
        yeast_factor = 1 / (self.yeast_pct / 1.0)
        return base_time * temp_factor * yeast_factor * math.log(rise_factor) / math.log(2)

    def co2_production(self, flour_g: float = 1000) -> float:
        return flour_g * self.yeast_pct * 0.01 * (self.ambient_temp / 30) ** 2

    def optimal_humidity(self) -> float:
        return 75 + max(0, (self.ambient_temp - 25) * 0.5)

    def overproofed(self, time_min: float) -> bool:
        return time_min > self.proof_time() * 2

    def poke_test(self, indent_recovery: float) -> str:
        if indent_recovery < 0.3: return "underproofed"
        elif indent_recovery < 0.7: return "ready"
        return "overproofed"

    def stats(self) -> Dict:
        return {"proof_time": round(self.proof_time(), 1), "optimal_humidity": self.optimal_humidity(), "overproofed": self.overproofed(300)}

def run():
    p = Proofer(ambient_temp=28, yeast_pct=1.5)
    print(p.stats())
    print("Poke test 0.5:", p.poke_test(0.5))

if __name__ == "__main__":
    run()
