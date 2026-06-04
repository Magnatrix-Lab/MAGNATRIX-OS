"""Climate Modeler — radiation balance, greenhouse, feedback, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class ClimateModeler:
    solar_constant: float = 1361.0
    albedo: float = 0.3
    emissivity: float = 0.61
    sigma: float = 5.67e-8

    def effective_temperature(self) -> float:
        s = self.solar_constant / 4 * (1 - self.albedo)
        return (s / (self.emissivity * self.sigma)) ** 0.25

    def equilibrium_temp(self, forcing: float = 0.0) -> float:
        base = self.effective_temperature()
        return base + forcing * 0.8

    def greenhouse_effect(self) -> float:
        no_ghg = ((self.solar_constant / 4) * (1 - self.albedo) / self.sigma) ** 0.25
        return self.effective_temperature() - no_ghg

    def feedback(self, temp_change: float, lambda_total: float = -1.2) -> float:
        return temp_change / lambda_total if lambda_total != 0 else 0.0

    def stats(self) -> Dict:
        return {"Teff": round(self.effective_temperature(), 2), "ghg_effect": round(self.greenhouse_effect(), 2)}

def run():
    cm = ClimateModeler()
    print(cm.stats())
    print("With forcing:", cm.equilibrium_temp(3.7))

if __name__ == "__main__":
    run()
