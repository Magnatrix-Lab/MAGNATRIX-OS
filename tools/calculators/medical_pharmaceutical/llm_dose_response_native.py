"""Native stdlib module: Dose Response Calculator
Calculates EC50, IC50, and dose-response curves for drug development.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class DoseResponseCalculator:
    drug_name: str
    max_response: float
    min_response: float
    ec50_molar: float
    hill_slope: float

    def response_at_concentration(self, concentration_molar: float) -> float:
        if self.ec50_molar == 0 or concentration_molar == 0:
            return self.min_response
        return self.min_response + (self.max_response - self.min_response) / (1 + (self.ec50_molar / concentration_molar) ** self.hill_slope)

    def concentration_for_response(self, target_response: float) -> float:
        if self.max_response == self.min_response or target_response <= self.min_response:
            return 0.0
        ratio = (self.max_response - self.min_response) / (target_response - self.min_response) - 1
        if ratio <= 0:
            return 0.0
        return self.ec50_molar * (ratio ** (1 / self.hill_slope))

    def ic50_from_ec50(self, max_response_pct: float = 100) -> float:
        if self.hill_slope == 0:
            return 0.0
        return self.ec50_molar * ((max_response_pct / (100 - max_response_pct)) ** (1 / self.hill_slope))

    def pIC50(self) -> float:
        if self.ec50_molar == 0:
            return 0.0
        return -math.log10(self.ec50_molar)

    def pEC50(self) -> float:
        if self.ec50_molar == 0:
            return 0.0
        return -math.log10(self.ec50_molar)

    def stats(self) -> Dict:
        return {
            "drug": self.drug_name,
            "ec50_molar": f"{self.ec50_molar:.2e}",
            "pEC50": round(self.pEC50(), 2),
            "pIC50": round(self.pIC50(), 2),
            "hill_slope": self.hill_slope,
            "max_response": self.max_response,
            "min_response": self.min_response,
        }

def run():
    drc = DoseResponseCalculator(drug_name="Compound-X", max_response=100, min_response=0, ec50_molar=1e-6, hill_slope=1.5)
    print(drc.stats())
    print(f"Response at 1e-6 M: {drc.response_at_concentration(1e-6):.1f}")

if __name__ == "__main__":
    run()
