"""Blast Designer — powder factor, stemming, burden, spacing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class BlastDesigner:
    hole_diameter_mm: float = 150.0
    rock_density: float = 2.7
    explosive_density: float = 1.2
    bench_height: float = 10.0

    def burden(self) -> float:
        return 25 * self.hole_diameter_mm / 1000

    def spacing(self) -> float:
        return 1.25 * self.burden()

    def stemming_length(self) -> float:
        return 0.7 * self.burden()

    def charge_length(self) -> float:
        return self.bench_height - self.stemming_length()

    def powder_factor(self) -> float:
        vol = self.burden() * self.spacing() * self.bench_height
        charge_vol = math.pi * (self.hole_diameter_mm / 2000) ** 2 * self.charge_length()
        explosive_mass = charge_vol * self.explosive_density
        return explosive_mass / vol if vol > 0 else 0

    def hole_count(self, area_length: float, area_width: float) -> int:
        b = self.burden()
        s = self.spacing()
        rows = int(area_length / b) + 1
        cols = int(area_width / s) + 1
        return rows * cols

    def stats(self) -> Dict:
        return {"burden": round(self.burden(), 2), "spacing": round(self.spacing(), 2), "pf": round(self.powder_factor(), 3)}

def run():
    bd = BlastDesigner()
    print(bd.stats())
    print("Holes for 100x50m:", bd.hole_count(100, 50))

if __name__ == "__main__":
    run()
