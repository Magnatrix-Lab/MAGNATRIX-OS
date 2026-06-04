"""Dating Estimator — radiocarbon, thermoluminescence, stratigraphic dating, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sqrt, log, exp, fabs, pow, pi
from datetime import datetime, timedelta

class DatingMethod(Enum):
    RADIOCARBON = auto()
    THERMOLUMINESCENCE = auto()
    POTASSIUM_ARGON = auto()
    URANIUM_LEAD = auto()
    DENDROCHRONOLOGY = auto()
    STRATIGRAPHIC = auto()
    TYPOLOGICAL = auto()

@dataclass
class DatingResult:
    method: DatingMethod
    age_bp: float  # years before present
    uncertainty: float  # +/- years
    confidence: float  # 0-1
    sample_id: str = ""
    calibration_applied: bool = False

    @property
    def age_ce(self) -> float:
        """Age in Common Era (negative = BCE)."""
        return 1950.0 - self.age_bp

    def overlaps(self, other: 'DatingResult') -> bool:
        """Check if age ranges overlap within 2 sigma."""
        r1 = (self.age_bp - 2*self.uncertainty, self.age_bp + 2*self.uncertainty)
        r2 = (other.age_bp - 2*other.uncertainty, other.age_bp + 2*other.uncertainty)
        return max(r1[0], r2[0]) <= min(r1[1], r2[1])

    def weighted_average(self, other: 'DatingResult') -> Optional['DatingResult']:
        """Combine two dating results."""
        if self.uncertainty <= 0 or other.uncertainty <= 0:
            return None
        w1 = 1.0 / (self.uncertainty ** 2)
        w2 = 1.0 / (other.uncertainty ** 2)
        avg = (self.age_bp * w1 + other.age_bp * w2) / (w1 + w2)
        unc = sqrt(1.0 / (w1 + w2))
        return DatingResult(self.method, avg, unc, min(self.confidence, other.confidence) * 0.9)

class DatingEstimator:
    def __init__(self):
        self.results: List[DatingResult] = []

    def add_result(self, result: DatingResult) -> None:
        self.results.append(result)

    def calibrate_radiocarbon(self, result: DatingResult) -> DatingResult:
        """Simplified calibration curve for radiocarbon."""
        if result.method != DatingMethod.RADIOCARBON:
            return result
        # Simplified: apply a small correction based on age
        correction = 0.0
        if result.age_bp > 5000:
            correction = result.age_bp * 0.02
        return DatingResult(
            result.method,
            result.age_bp + correction,
            result.uncertainty * 1.5,
            result.confidence * 0.9,
            result.sample_id,
            calibration_applied=True
        )

    def consensus_age(self) -> Optional[DatingResult]:
        """Weighted consensus from all results."""
        if not self.results:
            return None
        total_weight = 0.0
        weighted_sum = 0.0
        for r in self.results:
            if r.uncertainty > 0:
                w = 1.0 / (r.uncertainty ** 2)
                total_weight += w
                weighted_sum += r.age_bp * w
        if total_weight == 0:
            return None
        avg = weighted_sum / total_weight
        unc = sqrt(1.0 / total_weight)
        conf = sum(r.confidence for r in self.results) / len(self.results)
        return DatingResult(DatingMethod.STRATIGRAPHIC, avg, unc, conf)

    def find_outliers(self, threshold_sigma: float = 2.0) -> List[DatingResult]:
        consensus = self.consensus_age()
        if not consensus:
            return []
        outliers = []
        for r in self.results:
            z = fabs(r.age_bp - consensus.age_bp) / sqrt(r.uncertainty**2 + consensus.uncertainty**2) if consensus.uncertainty > 0 or r.uncertainty > 0 else 0
            if z > threshold_sigma:
                outliers.append(r)
        return outliers

    def stratigraphic_consistency(self, expected_order: List[str]) -> bool:
        """Check if results are in expected stratigraphic order."""
        if len(self.results) < 2 or len(expected_order) != len(self.results):
            return True
        sorted_results = sorted(self.results, key=lambda r: r.age_bp, reverse=True)
        for i, sample_id in enumerate(expected_order):
            if sorted_results[i].sample_id != sample_id:
                return False
        return True

    def stats(self) -> Dict[str, float]:
        if not self.results:
            return {}
        ages = [r.age_bp for r in self.results]
        uncs = [r.uncertainty for r in self.results]
        return {
            "sample_count": len(self.results),
            "oldest_age_bp": max(ages),
            "youngest_age_bp": min(ages),
            "avg_uncertainty": sum(uncs) / len(uncs),
            "consensus_age_bp": self.consensus_age().age_bp if self.consensus_age() else 0.0
        }

def run():
    est = DatingEstimator()
    est.add_result(DatingResult(DatingMethod.RADIOCARBON, 3500, 50, 0.95, "S1"))
    est.add_result(DatingResult(DatingMethod.THERMOLUMINESCENCE, 3400, 120, 0.80, "S2"))
    est.add_result(DatingResult(DatingMethod.STRATIGRAPHIC, 3600, 200, 0.70, "S3"))
    cal = est.calibrate_radiocarbon(est.results[0])
    print(f"Calibrated radiocarbon: {cal.age_bp:.0f} ± {cal.uncertainty:.0f} BP")
    consensus = est.consensus_age()
    print(f"Consensus age: {consensus.age_bp:.0f} ± {consensus.uncertainty:.0f} BP ({consensus.age_ce:.0f} CE)")
    print(f"Outliers: {len(est.find_outliers())}")
    print(est.stats())

if __name__ == "__main__":
    run()
