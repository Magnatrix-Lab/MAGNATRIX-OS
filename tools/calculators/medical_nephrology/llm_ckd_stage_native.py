"""
CKD Stage Calculator — Nephrology
GFR + albuminuria heat map (KDIGO 2012 classification).
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class AlbuminuriaStage(Enum):
    A1 = "A1"  # <30 mg/g (normal to mildly increased)
    A2 = "A2"  # 30-300 mg/g (moderately increased)
    A3 = "A3"  # >300 mg/g (severely increased)


class GFRStage(Enum):
    G1 = "G1"   # >=90
    G2 = "G2"   # 60-89
    G3A = "G3a" # 45-59
    G3B = "G3b" # 30-44
    G4 = "G4"   # 15-29
    G5 = "G5"   # <15


class RiskColor(Enum):
    GREEN = "low_risk"
    YELLOW = "moderately_increased_risk"
    ORANGE = "high_risk"
    RED = "very_high_risk"
    DARK_RED = "highest_risk"


@dataclass
class CKDProfile:
    egfr: float
    acr_mg_g: float  # urine albumin-to-creatinine ratio
    diabetes: bool = False
    hypertension: bool = False


@dataclass
class CKDResult:
    gfr_stage: GFRStage
    albuminuria_stage: AlbuminuriaStage
    risk_color: RiskColor
    risk_description: str
    annual_mortality_risk: str
    progression_to_esrd_risk: str
    recommendations: List[str]
    follow_up_frequency: str


class CKDStageCalculator:
    """KDIGO 2012 CKD GFR-albuminuria heat map."""

    # KDIGO risk matrix: GFR stage (rows) x Albuminuria (cols)
    RISK_MATRIX = {
        (GFRStage.G1, AlbuminuriaStage.A1): RiskColor.GREEN,
        (GFRStage.G1, AlbuminuriaStage.A2): RiskColor.YELLOW,
        (GFRStage.G1, AlbuminuriaStage.A3): RiskColor.ORANGE,
        (GFRStage.G2, AlbuminuriaStage.A1): RiskColor.GREEN,
        (GFRStage.G2, AlbuminuriaStage.A2): RiskColor.YELLOW,
        (GFRStage.G2, AlbuminuriaStage.A3): RiskColor.ORANGE,
        (GFRStage.G3A, AlbuminuriaStage.A1): RiskColor.YELLOW,
        (GFRStage.G3A, AlbuminuriaStage.A2): RiskColor.ORANGE,
        (GFRStage.G3A, AlbuminuriaStage.A3): RiskColor.RED,
        (GFRStage.G3B, AlbuminuriaStage.A1): RiskColor.ORANGE,
        (GFRStage.G3B, AlbuminuriaStage.A2): RiskColor.RED,
        (GFRStage.G3B, AlbuminuriaStage.A3): RiskColor.DARK_RED,
        (GFRStage.G4, AlbuminuriaStage.A1): RiskColor.RED,
        (GFRStage.G4, AlbuminuriaStage.A2): RiskColor.DARK_RED,
        (GFRStage.G4, AlbuminuriaStage.A3): RiskColor.DARK_RED,
        (GFRStage.G5, AlbuminuriaStage.A1): RiskColor.DARK_RED,
        (GFRStage.G5, AlbuminuriaStage.A2): RiskColor.DARK_RED,
        (GFRStage.G5, AlbuminuriaStage.A3): RiskColor.DARK_RED,
    }

    def calculate(self, profile: CKDProfile) -> CKDResult:
        # GFR stage
        if profile.egfr >= 90:
            gfr = GFRStage.G1
        elif profile.egfr >= 60:
            gfr = GFRStage.G2
        elif profile.egfr >= 45:
            gfr = GFRStage.G3A
        elif profile.egfr >= 30:
            gfr = GFRStage.G3B
        elif profile.egfr >= 15:
            gfr = GFRStage.G4
        else:
            gfr = GFRStage.G5

        # Albuminuria stage
        if profile.acr_mg_g < 30:
            alb = AlbuminuriaStage.A1
        elif profile.acr_mg_g <= 300:
            alb = AlbuminuriaStage.A2
        else:
            alb = AlbuminuriaStage.A3

        # Risk color
        risk = self.RISK_MATRIX.get((gfr, alb), RiskColor.DARK_RED)

        risk_desc = {
            RiskColor.GREEN: "Low risk (if no other markers of kidney disease)",
            RiskColor.YELLOW: "Moderately increased risk",
            RiskColor.ORANGE: "High risk",
            RiskColor.RED: "Very high risk",
            RiskColor.DARK_RED: "Highest risk",
        }[risk]

        # Mortality and ESRD risk
        if risk == RiskColor.GREEN:
            mortality = "Low"
            esrd = "Very low"
            follow = "Every 1-2 years"
        elif risk == RiskColor.YELLOW:
            mortality = "Low-to-moderate"
            esrd = "Low"
            follow = "Every 6-12 months"
        elif risk == RiskColor.ORANGE:
            mortality = "Moderate"
            esrd = "Moderate"
            follow = "Every 3-6 months"
        elif risk == RiskColor.RED:
            mortality = "High"
            esrd = "High"
            follow = "Every 3 months"
        else:
            mortality = "Very high"
            esrd = "Very high"
            follow = "Every 1-3 months"

        recs = ["BP control <130/80", "Avoid nephrotoxic agents"]
        if alb != AlbuminuriaStage.A1:
            recs += ["ACE inhibitor or ARB (maximally tolerated dose)", "Sodium restriction <2g/day"]
        if profile.diabetes:
            recs += ["HbA1c target 7% (individualize)", "SGLT2 inhibitor if eGFR >= 30"]
        if risk.value in ["high_risk", "very_high_risk", "highest_risk"]:
            recs += ["Nephrology referral", "Anemia and bone-mineral disorder monitoring"]
        if gfr == GFRStage.G5:
            recs += ["Dialysis preparation", "Transplant evaluation"]

        return CKDResult(
            gfr_stage=gfr,
            albuminuria_stage=alb,
            risk_color=risk,
            risk_description=risk_desc,
            annual_mortality_risk=mortality,
            progression_to_esrd_risk=esrd,
            recommendations=recs,
            follow_up_frequency=follow
        )

    def risk_heatmap_summary(self) -> List[str]:
        """Printable risk matrix summary."""
        lines = ["KDIGO 2012 CKD Risk Heat Map:", " " * 20 + "A1      A2      A3"]
        for gfr in [GFRStage.G1, GFRStage.G2, GFRStage.G3A, GFRStage.G3B, GFRStage.G4, GFRStage.G5]:
            row = f"{gfr.value:>5}"
            for alb in [AlbuminuriaStage.A1, AlbuminuriaStage.A2, AlbuminuriaStage.A3]:
                color = self.RISK_MATRIX.get((gfr, alb), RiskColor.DARK_RED)
                row += f"  {color.value[:6]:>6}"
            lines.append(row)
        return lines


def run():
    calc = CKDStageCalculator()

    print("=" * 60)
    print("CKD Stage Calculator (KDIGO 2012)")
    print("=" * 60)

    profile = CKDProfile(egfr=38, acr_mg_g=450, diabetes=True, hypertension=True)
    result = calc.calculate(profile)
    print(f"\nGFR stage: {result.gfr_stage.value}")
    print(f"Albuminuria: {result.albuminuria_stage.value}")
    print(f"Risk: {result.risk_color.value}")
    print(f"Description: {result.risk_description}")
    print(f"Mortality risk: {result.annual_mortality_risk}")
    print(f"ESRD risk: {result.progression_to_esrd_risk}")
    print(f"Follow-up: {result.follow_up_frequency}")
    print(f"Recommendations: {result.recommendations}")

    print("\n" + "\n".join(calc.risk_heatmap_summary()))
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
