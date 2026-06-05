"""Fermentation Tracker — gravity, attenuation, ABV, temp, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class FermentationTracker:
    og: float = 1.050
    fg: float = 1.010
    fermentation_temp: float = 20.0
    yeast_strain: str = "ale"

    def attenuation(self) -> float:
        if self.og <= 1.0:
            return 0.0
        return (self.og - self.fg) / (self.og - 1.0) * 100

    def abv(self) -> float:
        return (self.og - self.fg) * 131.25

    def abw(self) -> float:
        return self.abv() * 0.79

    def residual_sugar_gpl(self) -> float:
        return (self.fg - 1.0) * 1000

    def fermentation_time_estimate(self, cell_count_billion: float = 100) -> float:
        base = 7 if self.yeast_strain == "ale" else 14
        return base / (cell_count_billion / 100) ** 0.5

    def stats(self) -> Dict:
        return {"attenuation": round(self.attenuation(), 1), "abv": round(self.abv(), 2), "time_est": round(self.fermentation_time_estimate(), 1)}

def run():
    ft = FermentationTracker(og=1.060, fg=1.012, yeast_strain="lager")
    print(ft.stats())
    print("Residual sugar:", ft.residual_sugar_gpl())

if __name__ == "__main__":
    run()
