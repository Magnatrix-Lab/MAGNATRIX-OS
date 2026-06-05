"""Bioavailability Calculator — AUC, F, tmax, Cmax, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class BioavailabilityCalculator:
    auc_iv: float = 100.0
    auc_po: float = 80.0
    dose_iv: float = 10.0
    dose_po: float = 100.0

    def absolute_bioavailability(self) -> float:
        return (self.auc_po * self.dose_iv) / (self.auc_iv * self.dose_po) if self.auc_iv * self.dose_po > 0 else 0.0

    def relative_bioavailability(self, auc_ref: float, dose_ref: float) -> float:
        return (self.auc_po * dose_ref) / (auc_ref * self.dose_po) if auc_ref * self.dose_po > 0 else 0.0

    def auc_from_concentrations(self, concentrations: List[Tuple[float, float]], method: str = "trapezoidal") -> float:
        if not concentrations or len(concentrations) < 2:
            return 0.0
        auc = 0.0
        for i in range(len(concentrations) - 1):
            t1, c1 = concentrations[i]
            t2, c2 = concentrations[i+1]
            if method == "trapezoidal":
                auc += (c1 + c2) / 2 * (t2 - t1)
        return auc

    def half_life(self, concentrations: List[Tuple[float, float]]) -> float:
        if len(concentrations) < 2:
            return 0.0
        c_max = max(c for _, c in concentrations)
        c_half = c_max / 2
        for i, (t, c) in enumerate(concentrations):
            if c <= c_half:
                if i > 0:
                    t_prev, c_prev = concentrations[i-1]
                    return t_prev + (t - t_prev) * (c_prev - c_half) / (c_prev - c)
                return t
        return 0.0

    def stats(self) -> Dict:
        return {"absolute_F": round(self.absolute_bioavailability(), 3), "percent": round(self.absolute_bioavailability() * 100, 1)}

def run():
    bac = BioavailabilityCalculator(auc_iv=120, auc_po=90, dose_iv=5, dose_po=50)
    print(bac.stats())
    conc = [(0, 0), (0.5, 10), (1, 15), (2, 12), (4, 8), (8, 4), (12, 2)]
    print("AUC:", bac.auc_from_concentrations(conc))
    print("t1/2:", bac.half_life(conc))

if __name__ == "__main__":
    run()
