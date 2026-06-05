"""
Vaccine Efficacy Calculator — Immunology
Herd immunity threshold, coverage rates, and outbreak risk estimation.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict
import math


@dataclass
class VaccineProfile:
    r0: float                    # Basic reproduction number
    vaccine_efficacy_percent: float
    current_coverage_percent: float
    target_coverage_percent: float
    population_size: int = 100000
    age_groups: dict = None      # {"0-4": 0.1, "5-18": 0.2, ...}
    susceptible_depletion: bool = True

    def __post_init__(self):
        if self.age_groups is None:
            self.age_groups = {"general": 1.0}


@dataclass
class VaccineResult:
    herd_immunity_threshold: float
    current_coverage_adequate: bool
    outbreak_risk: str
    additional_coverage_needed: float
    cases_prevented: int
    effective_reproduction_current: float
    effective_reproduction_target: float
    recommendations: List[str]


class VaccineEfficacyCalculator:
    """Herd immunity and outbreak risk calculator."""

    def calculate(self, profile: VaccineProfile) -> VaccineResult:
        # Herd immunity threshold: 1 - 1/R0
        if profile.r0 <= 1:
            herd_threshold = 0.0
        else:
            herd_threshold = 1 - (1 / profile.r0)

        # Effective coverage = coverage * efficacy
        effective_current = (profile.current_coverage_percent / 100) * (profile.vaccine_efficacy_percent / 100)
        effective_target = (profile.target_coverage_percent / 100) * (profile.vaccine_efficacy_percent / 100)

        # Effective reproduction number
        re_current = profile.r0 * (1 - effective_current)
        re_target = profile.r0 * (1 - effective_target)

        # Outbreak risk
        if re_current > 1.5:
            outbreak = "Very High"
        elif re_current > 1.0:
            outbreak = "High"
        elif re_current > 0.7:
            outbreak = "Moderate"
        else:
            outbreak = "Low"

        adequate = effective_current >= herd_threshold
        additional_needed = max(0, (herd_threshold - effective_current) * 100)

        # Cases prevented (simple model)
        if profile.susceptible_depletion:
            cases_prevented = int(profile.population_size * (effective_target - effective_current) * profile.r0)
        else:
            cases_prevented = 0
        cases_prevented = max(0, cases_prevented)

        recs = []
        if not adequate:
            recs.append(f"Increase coverage by {additional_needed:.1f}% to reach herd immunity")
        if re_current > 1.0:
            recs.append("Outbreak likely without intervention — booster campaign recommended")
        if profile.vaccine_efficacy_percent < 70:
            recs.append("Low efficacy vaccine — target higher coverage or consider alternative vaccine")
        recs.append("Surveillance and rapid outbreak response protocol")
        if adequate:
            recs.append("Maintain current coverage with ongoing surveillance")

        return VaccineResult(
            herd_immunity_threshold=round(herd_threshold * 100, 2),
            current_coverage_adequate=adequate,
            outbreak_risk=outbreak,
            additional_coverage_needed=round(additional_needed, 2),
            cases_prevented=cases_prevented,
            effective_reproduction_current=round(re_current, 2),
            effective_reproduction_target=round(re_target, 2),
            recommendations=recs
        )

    def outbreak_size_estimate(self, re: float, initial_cases: int, population: int) -> dict:
        """Simple SIR estimate."""
        if re <= 1:
            return {"total_cases": initial_cases, "peak_cases": initial_cases, "duration_days": 14, "note": "Outbreak self-limiting (R_e <= 1)"}
        # Very rough approximation
        attack_rate = min(0.8, 1 - math.exp(-re * 0.5))
        total = int(population * attack_rate)
        return {
            "total_cases": total,
            "peak_cases": int(total * 0.2),
            "duration_days": int(30 + re * 10),
            "attack_rate_percent": round(attack_rate * 100, 2)
        }


def run():
    calc = VaccineEfficacyCalculator()

    print("=" * 60)
    print("Vaccine Efficacy Calculator")
    print("=" * 60)

    profile = VaccineProfile(
        r0=5.0, vaccine_efficacy_percent=95,
        current_coverage_percent=60, target_coverage_percent=90,
        population_size=1000000
    )

    result = calc.calculate(profile)
    print(f"\nHerd immunity threshold: {result.herd_immunity_threshold}%")
    print(f"Coverage adequate: {result.current_coverage_adequate}")
    print(f"Outbreak risk: {result.outbreak_risk}")
    print(f"Additional coverage needed: {result.additional_coverage_needed}%")
    print(f"Cases prevented: {result.cases_prevented}")
    print(f"R_e current: {result.effective_reproduction_current}")
    print(f"R_e target: {result.effective_reproduction_target}")
    print(f"Recommendations: {result.recommendations}")

    print(f"\nOutbreak estimate (R_e=2.5, 10 initial cases): {calc.outbreak_size_estimate(2.5, 10, 100000)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
