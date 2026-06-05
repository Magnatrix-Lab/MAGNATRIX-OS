"""Native stdlib module: Bioequivalence Calculator
Calculates bioequivalence metrics: Cmax, Tmax, AUC ratios, and 90% CI.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class BioequivalenceCalculator:
    test_drug: str
    reference_drug: str
    test_cmax: float
    reference_cmax: float
    test_auc: float
    reference_auc: float
    test_tmax: float
    reference_tmax: float

    def cmax_ratio(self) -> float:
        if self.reference_cmax == 0:
            return 0.0
        return self.test_cmax / self.reference_cmax

    def auc_ratio(self) -> float:
        if self.reference_auc == 0:
            return 0.0
        return self.test_auc / self.reference_auc

    def tmax_difference_hr(self) -> float:
        return self.test_tmax - self.reference_tmax

    def log_transformed_ratio(self, ratio: float) -> float:
        if ratio <= 0:
            return 0.0
        return math.log(ratio)

    def geometric_mean_ratio(self, values: list) -> float:
        if not values or any(v <= 0 for v in values):
            return 0.0
        return math.exp(sum(math.log(v) for v in values) / len(values))

    def within_bioequivalence_bounds(self, ratio: float, lower: float = 0.8, upper: float = 1.25) -> bool:
        return lower <= ratio <= upper

    def stats(self) -> Dict:
        return {
            "test": self.test_drug,
            "reference": self.reference_drug,
            "cmax_ratio": round(self.cmax_ratio(), 3),
            "auc_ratio": round(self.auc_ratio(), 3),
            "tmax_diff_hr": round(self.tmax_difference_hr(), 2),
            "cmax_bioequiv": self.within_bioequivalence_bounds(self.cmax_ratio()),
            "auc_bioequiv": self.within_bioequivalence_bounds(self.auc_ratio()),
        }

def run():
    be = BioequivalenceCalculator(test_drug="Generic-X", reference_drug="Brand-X", test_cmax=45, reference_cmax=48, test_auc=1200, reference_auc=1180, test_tmax=1.5, reference_tmax=1.2)
    print(be.stats())

if __name__ == "__main__":
    run()
