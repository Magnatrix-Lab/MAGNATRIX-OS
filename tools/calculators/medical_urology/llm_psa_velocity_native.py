"""
PSA Velocity Calculator — Urology
PSA doubling time, velocity, and prostate cancer risk stratification.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import math


class PSARiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class PSAProfile:
    psa_values_ng_ml: List[float]  # chronological
    dates_months: List[float]     # corresponding dates in months from first
    age: int
    prostate_volume_ml: float = 30.0
    free_psa_percent: float = 0.0
    psa_density: float = 0.0
    family_history: bool = False
    african_american: bool = False
    prior_biopsy: bool = False


@dataclass
class PSAResult:
    psa_velocity_ng_ml_year: float
    psa_doubling_time_months: Optional[float]
    psa_density_ng_ml: float
    free_total_ratio: float
    risk_level: PSARiskLevel
    biopsy_recommended: bool
    mri_recommended: bool
    follow_up_interval_months: int
    notes: List[str]


class PSAVelocityCalculator:
    """PSA trend analysis and prostate cancer risk."""

    def calculate(self, profile: PSAProfile) -> PSAResult:
        notes = []
        values = profile.psa_values_ng_ml
        dates = profile.dates_months

        if len(values) < 2 or len(values) != len(dates):
            raise ValueError("Need at least 2 PSA values with corresponding dates")

        # PSA velocity (linear regression simplified)
        if len(values) >= 2:
            # Slope = (last - first) / (last_date - first_date) in months
            velocity_monthly = (values[-1] - values[0]) / (dates[-1] - dates[0]) if dates[-1] != dates[0] else 0
            velocity_yearly = velocity_monthly * 12
        else:
            velocity_yearly = 0

        # PSA doubling time (simplified, assuming exponential growth)
        if len(values) >= 2 and values[0] > 0 and values[-1] > values[0]:
            ratio = values[-1] / values[0]
            months_diff = dates[-1] - dates[0]
            if ratio > 1 and months_diff > 0:
                pdt = months_diff * (math.log(2) / math.log(ratio))
            else:
                pdt = None
        else:
            pdt = None

        # PSA density
        if profile.psa_density > 0:
            psad = profile.psa_density
        else:
            psad = values[-1] / profile.prostate_volume_ml if profile.prostate_volume_ml > 0 else 0

        # Free/total ratio
        if profile.free_psa_percent > 0 and values[-1] > 0:
            ft_ratio = profile.free_psa_percent / 100
        else:
            ft_ratio = 0.15  # Default assumption

        # Risk stratification
        current_psa = values[-1]
        if current_psa < 4 and psad < 0.15 and (not pdt or pdt > 60):
            risk = PSARiskLevel.LOW
        elif current_psa < 10 and psad < 0.15 and velocity_yearly < 0.75:
            risk = PSARiskLevel.MODERATE
        elif current_psa < 20 and (psad >= 0.15 or velocity_yearly >= 0.75 or (pdt and pdt < 36)):
            risk = PSARiskLevel.HIGH
        else:
            risk = PSARiskLevel.VERY_HIGH

        # Age-specific thresholds
        if profile.age < 50 and current_psa > 2.5:
            risk = max(risk, PSARiskLevel.MODERATE)
            notes.append("PSA > 2.5 in men <50 warrants evaluation.")
        if profile.age < 60 and current_psa > 3.5:
            risk = max(risk, PSARiskLevel.MODERATE)

        # Biopsy recommendation
        biopsy = (current_psa > 4 and risk.value in ["moderate", "high", "very_high"]) or (psad > 0.15)
        if profile.african_american:
            biopsy = biopsy or current_psa > 3.5
            notes.append("African American men — consider biopsy at lower PSA thresholds.")
        if profile.family_history:
            biopsy = biopsy or current_psa > 3.5

        # MRI recommendation
        mri = biopsy and current_psa > 4 and not profile.prior_biopsy

        # Follow-up
        if risk == PSARiskLevel.LOW:
            follow = 12
        elif risk == PSARiskLevel.MODERATE:
            follow = 6
        else:
            follow = 3

        if velocity_yearly > 0.75:
            notes.append("PSA velocity > 0.75 ng/mL/year — associated with increased cancer risk.")
        if pdt and pdt < 36:
            notes.append("PSA doubling time < 3 years — concerning for aggressive disease.")
        if psad > 0.15:
            notes.append("PSA density > 0.15 — elevated cancer risk.")
        if ft_ratio < 0.15 and current_psa > 4:
            notes.append("Free PSA < 15% — increased likelihood of prostate cancer.")

        return PSAResult(
            psa_velocity_ng_ml_year=round(velocity_yearly, 2),
            psa_doubling_time_months=round(pdt, 1) if pdt else None,
            psa_density_ng_ml=round(psad, 2),
            free_total_ratio=round(ft_ratio, 2),
            risk_level=risk,
            biopsy_recommended=biopsy,
            mri_recommended=mri,
            follow_up_interval_months=follow,
            notes=notes
        )


def run():
    calc = PSAVelocityCalculator()

    print("=" * 60)
    print("PSA Velocity Calculator")
    print("=" * 60)

    profile = PSAProfile(
        psa_values_ng_ml=[2.8, 3.5, 4.8, 6.2],
        dates_months=[0, 6, 12, 18],
        age=62, prostate_volume_ml=45,
        free_psa_percent=12, family_history=True
    )

    result = calc.calculate(profile)
    print(f"\nPSA velocity: {result.psa_velocity_ng_ml_year} ng/mL/year")
    print(f"Doubling time: {result.psa_doubling_time_months} months")
    print(f"PSA density: {result.psa_density_ng_ml}")
    print(f"Free/Total: {result.free_total_ratio}")
    print(f"Risk: {result.risk_level.value}")
    print(f"Biopsy: {result.biopsy_recommended}, MRI: {result.mri_recommended}")
    print(f"Follow-up: {result.follow_up_interval_months} months")
    print(f"Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
