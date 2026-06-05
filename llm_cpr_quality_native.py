"""
CPR Quality Calculator — Emergency Medicine
Rate, depth, recoil scoring, and ROSC probability estimation.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum
import math


class CompressionQuality(Enum):
    EXCELLENT = "excellent"
    ADEQUATE = "adequate"
    POOR = "poor"
    DANGEROUS = "dangerous"


@dataclass
class CPRProfile:
    compression_rate_per_min: float  # Target 100-120
    compression_depth_mm: float      # Target 50-60 mm (adult)
    full_recoil: bool                 # Chest wall fully recoils
    interruptions_seconds: float     # Total pause time per minute
    ventilation_rate_per_min: float  # Target 10/min (2 every 30)
    patient_age_years: int = 35
    patient_weight_kg: float = 70
    witnessed_arrest: bool = False
    initial_rhythm: str = "unknown"  # vf, vt, asystole, pea
    time_to_cpr_minutes: float = 0.0
    aed_shocks_delivered: int = 0


@dataclass
class CPRResult:
    rate_quality: CompressionQuality
    depth_quality: CompressionQuality
    overall_quality: CompressionQuality
    score_percent: float
    rosc_probability: float
    defibrillation_success: float
    recommendations: List[str]
    notes: List[str]


class CPRQualityCalculator:
    """CPR quality scoring and ROSC probability estimation."""

    def calculate(self, profile: CPRProfile) -> CPRResult:
        recs = []
        notes = []

        # Rate assessment
        if 100 <= profile.compression_rate_per_min <= 120:
            rate_q = CompressionQuality.EXCELLENT
        elif 80 <= profile.compression_rate_per_min <= 130:
            rate_q = CompressionQuality.ADEQUATE
            recs.append("Adjust rate to 100-120/min")
        elif profile.compression_rate_per_min < 60:
            rate_q = CompressionQuality.DANGEROUS
            recs.append("Rate too slow — increase immediately to 100-120/min")
        else:
            rate_q = CompressionQuality.POOR
            recs.append("Rate suboptimal — adjust to 100-120/min")

        # Depth assessment (adult 50-60 mm)
        target_min = 50
        target_max = 60
        if profile.patient_age_years < 1:
            target_min, target_max = 30, 40  # Infant
        elif profile.patient_age_years < 8:
            target_min, target_max = 40, 50  # Child

        if target_min <= profile.compression_depth_mm <= target_max:
            depth_q = CompressionQuality.EXCELLENT
        elif profile.compression_depth_mm >= target_min * 0.8:
            depth_q = CompressionQuality.ADEQUATE
            recs.append(f"Depth suboptimal — aim for {target_min}-{target_max} mm")
        elif profile.compression_depth_mm < target_min * 0.5:
            depth_q = CompressionQuality.DANGEROUS
            recs.append(f"Depth insufficient — push harder, aim {target_min}-{target_max} mm")
        else:
            depth_q = CompressionQuality.POOR
            recs.append(f"Depth inadequate — push to {target_min}-{target_max} mm")

        # Recoil
        if not profile.full_recoil:
            recs.append("Allow full chest recoil — do not lean on chest")
            notes.append("Incomplete recoil reduces venous return and coronary perfusion.")

        # Interruptions (CPR fraction target > 80%)
        ccf = (60 - profile.interruptions_seconds) / 60 * 100  # Chest compression fraction
        if ccf < 80:
            recs.append(f"Minimize interruptions — CCF is {round(ccf, 1)}%, aim > 80%")

        # Ventilation
        if profile.ventilation_rate_per_min > 12:
            recs.append("Hyperventilation — reduce to 10 breaths/min (2 per 30 compressions)")
            notes.append("Hyperventilation increases intrathoracic pressure and reduces ROSC.")
        elif profile.ventilation_rate_per_min < 6:
            recs.append("Hypoventilation — ensure 2 ventilations per 30 compressions")

        # Overall quality
        qualities = [rate_q, depth_q]
        if not profile.full_recoil or ccf < 80:
            qualities.append(CompressionQuality.POOR)
        if CompressionQuality.DANGEROUS in qualities:
            overall = CompressionQuality.DANGEROUS
        elif CompressionQuality.POOR in qualities:
            overall = CompressionQuality.POOR
        elif CompressionQuality.ADEQUATE in qualities:
            overall = CompressionQuality.ADEQUATE
        else:
            overall = CompressionQuality.EXCELLENT

        # Score (0-100)
        score = 100
        if rate_q != CompressionQuality.EXCELLENT:
            score -= 15
        if depth_q != CompressionQuality.EXCELLENT:
            score -= 15
        if not profile.full_recoil:
            score -= 10
        if ccf < 80:
            score -= 10
        if profile.ventilation_rate_per_min > 12 or profile.ventilation_rate_per_min < 6:
            score -= 10
        score = max(0, score)

        # ROSC probability (very rough heuristic)
        base_rosc = 0.30
        if profile.witnessed_arrest:
            base_rosc += 0.15
        if profile.initial_rhythm in ["vf", "vt"]:
            base_rosc += 0.20
        if profile.aed_shocks_delivered > 0 and profile.initial_rhythm in ["vf", "vt"]:
            base_rosc += 0.10
        if profile.time_to_cpr_minutes <= 2:
            base_rosc += 0.10
        elif profile.time_to_cpr_minutes > 5:
            base_rosc -= 0.15

        # Quality adjustment
        if overall == CompressionQuality.EXCELLENT:
            base_rosc += 0.10
        elif overall == CompressionQuality.POOR:
            base_rosc -= 0.15
        elif overall == CompressionQuality.DANGEROUS:
            base_rosc -= 0.25

        rosc_prob = max(0.05, min(0.85, base_rosc))

        # Defibrillation success for VF/VT
        defib_success = 0.0
        if profile.initial_rhythm in ["vf", "vt"]:
            defib_success = 0.75 if profile.aed_shocks_delivered > 0 else 0.60
            if profile.time_to_cpr_minutes > 4:
                defib_success -= 0.15

        return CPRResult(
            rate_quality=rate_q,
            depth_quality=depth_q,
            overall_quality=overall,
            score_percent=round(score, 1),
            rosc_probability=round(rosc_prob, 3),
            defibrillation_success=round(defib_success, 3),
            recommendations=recs,
            notes=notes
        )

    def team_rotation_schedule(self, team_size: int, cycle_duration_seconds: int = 120) -> List[dict]:
        """Generate compressor rotation schedule to avoid fatigue."""
        schedule = []
        for i in range(team_size):
            role = "Compressor" if i == 0 else ("Airway" if i == 1 else "Team leader / IV")
            schedule.append({
                "member": i + 1,
                "role": role,
                "cycle_seconds": cycle_duration_seconds,
                "rotate_every": f"{cycle_duration_seconds // 60} min",
            })
        return schedule


def run():
    calc = CPRQualityCalculator()

    print("=" * 60)
    print("CPR Quality Calculator")
    print("=" * 60)

    cases = [
        CPRProfile(110, 55, True, 5, 10, 35, 70, True, "vf", 1.0, 2),
        CPRProfile(80, 40, False, 20, 15, 35, 70, False, "asystole", 6.0, 0),
        CPRProfile(130, 60, True, 3, 8, 5, 20, True, "vf", 0.5, 1),
    ]

    for i, c in enumerate(cases, 1):
        result = calc.calculate(c)
        print(f"\nCase {i}: Age {c.patient_age_years}, Rhythm {c.initial_rhythm}")
        print(f"  Rate: {result.rate_quality.value} | Depth: {result.depth_quality.value}")
        print(f"  Overall: {result.overall_quality.value} | Score: {result.score_percent}%")
        print(f"  ROSC probability: {result.rosc_probability}")
        print(f"  Defib success: {result.defibrillation_success}")
        print(f"  Recommendations: {result.recommendations}")

    print(f"\nTeam rotation (4-person, 2-min cycles): {calc.team_rotation_schedule(4)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
