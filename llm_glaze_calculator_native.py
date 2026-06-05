"""Native stdlib module: Glaze Calculator
Calculates glaze recipes, unity formulas, and SiO2:Al2O3 ratios.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class GlazeCalculator:
    silica_pct: float
    alumina_pct: float
    flux_pct: float
    batch_grams: float = 1000.0

    def total_pct(self) -> float:
        return self.silica_pct + self.alumina_pct + self.flux_pct

    def normalized_silica(self) -> float:
        return self.silica_pct / self.total_pct() if self.total_pct() else 0

    def normalized_alumina(self) -> float:
        return self.alumina_pct / self.total_pct() if self.total_pct() else 0

    def normalized_flux(self) -> float:
        return self.flux_pct / self.total_pct() if self.total_pct() else 0

    def silica_alumina_ratio(self) -> float:
        return self.silica_pct / self.alumina_pct if self.alumina_pct else 0

    def flux_index(self) -> float:
        return self.normalized_flux() / (self.normalized_silica() + self.normalized_alumina())

    def batch_amount(self, material_pct: float) -> float:
        return material_pct / 100 * self.batch_grams

    def stats(self) -> Dict:
        return {
            "normalized_silica": round(self.normalized_silica(), 3),
            "normalized_alumina": round(self.normalized_alumina(), 3),
            "normalized_flux": round(self.normalized_flux(), 3),
            "silica_alumina_ratio": round(self.silica_alumina_ratio(), 2),
            "flux_index": round(self.flux_index(), 3),
            "batch_grams": self.batch_grams,
        }

def run():
    gc = GlazeCalculator(silica_pct=60, alumina_pct=15, flux_pct=25, batch_grams=2000)
    print(gc.stats())

if __name__ == "__main__":
    run()
