"""Mainspring Calculator — torque, turns, dimensions, alloy, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class MainspringCalculator:
    width: float = 1.5
    thickness: float = 0.1
    length: float = 300.0
    arbor_diameter: float = 5.0
    barrel_diameter: float = 10.0

    def max_turns(self) -> float:
        return self.length / (math.pi * (self.barrel_diameter + self.arbor_diameter) / 2)

    def torque(self, modulus: float = 200000) -> float:
        return modulus * self.thickness ** 3 * self.width / (12 * self.length * 1000)

    def energy(self) -> float:
        return self.torque() * self.max_turns() * 2 * math.pi

    def thickness_by_space(self, available_height: float) -> float:
        return available_height / 2.5

    def alloy_grade(self) -> str:
        if self.thickness < 0.05: return "Nivarox"
        elif self.thickness < 0.1: return "Elinvar"
        return "Carbon steel"

    def stats(self) -> Dict:
        return {"max_turns": round(self.max_turns(), 1), "torque": round(self.torque(), 6), "energy": round(self.energy(), 4), "alloy": self.alloy_grade()}

def run():
    mc = MainspringCalculator(width=2, thickness=0.15, length=400, barrel_diameter=12)
    print(mc.stats())

if __name__ == "__main__":
    run()
