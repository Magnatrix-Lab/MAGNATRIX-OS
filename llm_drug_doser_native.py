"""Drug Doser — mg/kg, species, weight-based, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class DrugDoser:
    drug_name: str = ""
    dose_mg_per_kg: float = 0.0
    frequency: int = 1
    route: str = "oral"

    def calculate(self, weight_kg: float) -> float:
        return self.dose_mg_per_kg * weight_kg

    def daily_dose(self, weight_kg: float) -> float:
        return self.calculate(weight_kg) * self.frequency

    def volume_to_administer(self, weight_kg: float, concentration_mg_per_ml: float) -> float:
        if concentration_mg_per_ml <= 0:
            return 0.0
        return self.calculate(weight_kg) / concentration_mg_per_ml

    def safe_range(self, weight_kg: float, min_dose: float, max_dose: float) -> bool:
        d = self.calculate(weight_kg)
        return min_dose <= d <= max_dose

    def stats(self, weight_kg: float) -> Dict:
        return {"dose": round(self.calculate(weight_kg), 2), "daily": round(self.daily_dose(weight_kg), 2), "volume": round(self.volume_to_administer(weight_kg, 10), 2)}

def run():
    dd = DrugDoser("Amoxicillin", 10, 2, "oral")
    print(dd.stats(15))

if __name__ == "__main__":
    run()
