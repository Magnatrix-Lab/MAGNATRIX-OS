"""
Radiation Therapy Calculator — Oncology
Total dose, fractionation, BED, and EQD2 calculations.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum
import math


class TreatmentSite(Enum):
    BREAST = "breast"
    PROSTATE = "prostate"
    LUNG = "lung"
    HEAD_NECK = "head_neck"
    BRAIN = "brain"
    CERVIX = "cervix"
    RECTUM = "rectum"
    ESOPHAGUS = "esophagus"
    SKIN = "skin"
    BONE = "bone"


@dataclass
class RadiationProfile:
    site: TreatmentSite
    total_dose_gy: float
    fraction_size_gy: float
    fractions: int
    treatment_duration_days: int
    concurrent_chemo: bool = False
    previous_radiation_gy: float = 0.0
    alpha_beta_ratio: float = 10.0  # 10 for early effects, 3 for late effects


@dataclass
class RadiationResult:
    biologically_effective_dose_gy: float
    equivalent_dose_2gy_per_fraction_gy: float
    estimated_tumor_control: str
    estimated_normal_tissue_complication: str
    treatment_time_correction: float
    overall_treatment_time: int
    recommendations: List[str]
    follow_up: str


class RadiationCalculator:
    """Radiation therapy dose calculation with BED and EQD2."""

    def calculate(self, profile: RadiationProfile) -> RadiationResult:
        # BED = n * d * (1 + d / (alpha/beta))
        n = profile.fractions
        d = profile.fraction_size_gy
        ab = profile.alpha_beta_ratio

        bed = n * d * (1 + d / ab)

        # EQD2 = BED / (1 + 2 / (alpha/beta))
        eqd2 = bed / (1 + 2 / ab)

        # Tumor control estimate (very rough)
        if eqd2 >= 70:
            tumor_control = "High (>80% local control for most sites)"
        elif eqd2 >= 60:
            tumor_control = "Moderate-to-high (60-80% local control)"
        elif eqd2 >= 50:
            tumor_control = "Moderate (40-60% local control)"
        else:
            tumor_control = "Low (<40% local control)"

        # Normal tissue complication (for late effects, alpha/beta = 3)
        bed_late = n * d * (1 + d / 3)
        eqd2_late = bed_late / (1 + 2 / 3)

        if eqd2_late > 80:
            ntc = "High risk of severe late complications"
        elif eqd2_late > 65:
            ntc = "Moderate risk of late complications"
        elif eqd2_late > 50:
            ntc = "Low-to-moderate risk"
        else:
            ntc = "Low risk of late complications"

        # Overall treatment time factor (proliferation)
        # For head and neck: 0.6 Gy/day loss beyond 28 days
        if profile.site == TreatmentSite.HEAD_NECK and profile.treatment_duration_days > 28:
            time_loss = (profile.treatment_duration_days - 28) * 0.6
        else:
            time_loss = 0.0

        recs = ["IGRT/IMRT for target precision", "Weekly on-treatment imaging"]
        if profile.concurrent_chemo:
            recs += ["Concurrent chemotherapy increases acute toxicity — monitor closely", "Cisplatin/5-FU protocols per tumor type"]
        if profile.previous_radiation_gy > 0:
            recs.append(f"Prior radiation {profile.previous_radiation_gy}Gy — cumulative dose consideration, re-irradiation planning")
        if eqd2_late > 65:
            recs.append("Dose constraints to OARs strictly enforced — consider proton therapy if available")

        follow = "Acute toxicity assessment weekly during treatment, late toxicity at 3, 6, 12 months post-RT"

        return RadiationResult(
            biologically_effective_dose_gy=round(bed, 1),
            equivalent_dose_2gy_per_fraction_gy=round(eqd2, 1),
            estimated_tumor_control=tumor_control,
            estimated_normal_tissue_complication=ntc,
            treatment_time_correction=round(time_loss, 1),
            overall_treatment_time=profile.treatment_duration_days,
            recommendations=recs,
            follow_up=follow
        )

    def hypofractionation_equivalent(self, conventional_dose_gy: float, conventional_fractions: int,
                                     hypofraction_dose_gy: float, hypofractions: int,
                                     alpha_beta: float = 10.0) -> dict:
        """Compare conventional vs hypofractionated schedules."""
        d_conv = conventional_dose_gy / conventional_fractions
        d_hypo = hypofraction_dose_gy / hypofractions
        bed_conv = conventional_fractions * d_conv * (1 + d_conv / alpha_beta)
        bed_hypo = hypofractions * d_hypo * (1 + d_hypo / alpha_beta)
        eqd2_conv = bed_conv / (1 + 2 / alpha_beta)
        eqd2_hypo = bed_hypo / (1 + 2 / alpha_beta)
        return {
            "conventional_bed": round(bed_conv, 1),
            "hypofractionated_bed": round(bed_hypo, 1),
            "conventional_eqd2": round(eqd2_conv, 1),
            "hypofractionated_eqd2": round(eqd2_hypo, 1),
            "equivalent": abs(eqd2_conv - eqd2_hypo) < 5,
            "hypofractionated_more_effective_for_tumor": bed_hypo > bed_conv,
        }


def run():
    calc = RadiationCalculator()

    print("=" * 60)
    print("Radiation Therapy Calculator")
    print("=" * 60)

    profile = RadiationProfile(
        site=TreatmentSite.LUNG, total_dose_gy=60, fraction_size_gy=2,
        fractions=30, treatment_duration_days=40, concurrent_chemo=True
    )

    result = calc.calculate(profile)
    print(f"\nBED: {result.biologically_effective_dose_gy} Gy")
    print(f"EQD2: {result.equivalent_dose_2gy_per_fraction_gy} Gy")
    print(f"Tumor control: {result.estimated_tumor_control}")
    print(f"Late toxicity: {result.estimated_normal_tissue_complication}")
    print(f"Time correction: {result.treatment_time_correction} Gy")
    print(f"Recommendations: {result.recommendations}")

    print(f"\nHypofractionation compare: {calc.hypofractionation_equivalent(60, 30, 55, 20, 10)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
