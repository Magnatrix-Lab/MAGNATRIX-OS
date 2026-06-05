"""Native stdlib module: Pharmacokinetics Calculator
Calculates drug half-life, clearance, volume of distribution, and AUC.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class PharmacokineticsCalculator:
    drug_name: str
    dose_mg: float
    half_life_hr: float
    volume_distribution_l: float
    bioavailability_pct: float = 100.0

    def elimination_rate_constant(self) -> float:
        if self.half_life_hr == 0:
            return 0.0
        return math.log(2) / self.half_life_hr

    def clearance_l_hr(self) -> float:
        return self.elimination_rate_constant() * self.volume_distribution_l

    def auc_mg_hr_l(self) -> float:
        if self.clearance_l_hr() == 0:
            return 0.0
        return (self.dose_mg * (self.bioavailability_pct / 100)) / self.clearance_l_hr()

    def peak_concentration_mg_l(self) -> float:
        if self.volume_distribution_l == 0:
            return 0.0
        return (self.dose_mg * (self.bioavailability_pct / 100)) / self.volume_distribution_l

    def time_to_eliminate_pct(self, percentage: float = 95) -> float:
        if self.elimination_rate_constant() == 0:
            return 0.0
        return -math.log(1 - percentage / 100) / self.elimination_rate_constant()

    def concentration_at_time(self, time_hr: float) -> float:
        k = self.elimination_rate_constant()
        c0 = self.peak_concentration_mg_l()
        return c0 * math.exp(-k * time_hr)

    def loading_dose_mg(self, target_concentration_mg_l: float) -> float:
        if self.bioavailability_pct == 0:
            return 0.0
        return (target_concentration_mg_l * self.volume_distribution_l) / (self.bioavailability_pct / 100)

    def maintenance_dose_mg(self, dosing_interval_hr: float) -> float:
        if dosing_interval_hr == 0:
            return 0.0
        return self.loading_dose_mg(1.0) * (1 - math.exp(-self.elimination_rate_constant() * dosing_interval_hr))

    def stats(self) -> Dict:
        return {
            "drug": self.drug_name,
            "dose_mg": self.dose_mg,
            "half_life_hr": self.half_life_hr,
            "vd_l": self.volume_distribution_l,
            "ke_hr": round(self.elimination_rate_constant(), 4),
            "clearance_l_hr": round(self.clearance_l_hr(), 2),
            "auc_mg_hr_l": round(self.auc_mg_hr_l(), 2),
            "cmax_mg_l": round(self.peak_concentration_mg_l(), 2),
        }

def run():
    pk = PharmacokineticsCalculator(drug_name="Amoxicillin", dose_mg=500, half_life_hr=1.2, volume_distribution_l=15, bioavailability_pct=90)
    print(pk.stats())

if __name__ == "__main__":
    run()
