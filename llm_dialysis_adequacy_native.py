"""
Dialysis Adequacy Calculator — Nephrology
Kt/V urea for hemodialysis and peritoneal dialysis.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum
import math


class DialysisType(Enum):
    HEMODIALYSIS = "hemodialysis"
    PERITONEAL = "peritoneal"


@dataclass
class DialysisProfile:
    dialysis_type: DialysisType
    pre_bun_mg_dl: float
    post_bun_mg_dl: float
    weight_kg: float
    dialysis_duration_hours: float
    ultrafiltration_volume_l: float = 0.0
    residual_urine_volume_ml: float = 0.0
    # PD-specific
    pd_kt_v_per_week: float = 0.0
    pd_creatinine_clearance_l_week: float = 0.0
    pd_urine_kt_v: float = 0.0


@dataclass
class DialysisResult:
    spktv: float
    urea_reduction_ratio: float
    adequacy_met: bool
    target_kt_v: float
    recommendations: List[str]
    follow_up: str


class DialysisAdequacyCalculator:
    """Kt/V and URR calculation for dialysis adequacy."""

    def calculate(self, profile: DialysisProfile) -> DialysisResult:
        if profile.dialysis_type == DialysisType.HEMODIALYSIS:
            # URR = (preBUN - postBUN) / preBUN * 100
            urr = ((profile.pre_bun_mg_dl - profile.post_bun_mg_dl) / profile.pre_bun_mg_dl * 100)

            # spKt/V (single-pool) — Daugirdas formula
            # spKt/V = -ln(post/pre - 0.008 * t) + (4 - 3.5 * post/pre) * UF/W
            t = profile.dialysis_duration_hours
            uf_w = profile.ultrafiltration_volume_l / profile.weight_kg if profile.weight_kg > 0 else 0
            ratio = profile.post_bun_mg_dl / profile.pre_bun_mg_dl

            spktv = (-math.log(ratio - 0.008 * t) + (4 - 3.5 * ratio) * uf_w)

            target = 1.2
            adequacy = spktv >= target and urr >= 65

            recs = []
            if spktv < 1.2:
                recs.append("spKt/V below target — increase dialysis time or blood flow rate")
            if urr < 65:
                recs.append("URR below 65% — optimize dialysis prescription")
            if not recs:
                recs.append("Adequacy target met — maintain current prescription")

            follow = "Monthly adequacy testing"

        else:  # Peritoneal dialysis
            # Total Kt/V = peritoneal + renal (if residual function)
            total_ktv = profile.pd_kt_v_per_week + profile.pd_urine_kt_v
            urr = 0.0  # Not applicable for PD
            spktv = total_ktv
            target = 1.7  # Weekly Kt/V for PD
            adequacy = total_ktv >= target

            # Creatinine clearance target for PD = 45 L/week/1.73m²
            cc_target = 45.0
            cc_adequate = profile.pd_creatinine_clearance_l_week >= cc_target
            adequacy = adequacy and cc_adequate

            recs = []
            if total_ktv < 1.7:
                recs.append("Weekly Kt/V below 1.7 — increase dialysate volume or exchanges")
            if not cc_adequate:
                recs.append("Creatinine clearance below target — consider more exchanges or larger fill volumes")
            if not recs:
                recs.append("PD adequacy targets met")

            follow = "Every 3-6 months (PET test, adequacy assessment)"

        return DialysisResult(
            spktv=round(spktv, 2),
            urea_reduction_ratio=round(urr, 1),
            adequacy_met=adequacy,
            target_kt_v=target,
            recommendations=recs,
            follow_up=follow
        )

    def std_ktv_equilibrated(self, spktv: float, dialysis_duration_hours: float, 
                             urea_volume_distribution_l: float, urea_generation_rate: float) -> float:
        """eKt/V (equilibrated) — simplified."""
        # eKt/V = spKt/V * (1 - 0.6/t + 0.03) roughly
        if dialysis_duration_hours > 0:
            ektv = spktv * (1 - 0.6 / dialysis_duration_hours + 0.03)
        else:
            ektv = spktv
        return round(ektv, 2)


def run():
    calc = DialysisAdequacyCalculator()

    print("=" * 60)
    print("Dialysis Adequacy Calculator")
    print("=" * 60)

    hd = DialysisProfile(
        DialysisType.HEMODIALYSIS, pre_bun_mg_dl=75, post_bun_mg_dl=28,
        weight_kg=70, dialysis_duration_hours=4, ultrafiltration_volume_l=2.5
    )
    result = calc.calculate(hd)
    print(f"\nHD: spKt/V = {result.spktv}, URR = {result.urea_reduction_ratio}%")
    print(f"Adequacy met: {result.adequacy_met}")
    print(f"Recommendations: {result.recommendations}")

    pd = DialysisProfile(
        DialysisType.PERITONEAL, pre_bun_mg_dl=50, post_bun_mg_dl=30,
        weight_kg=70, dialysis_duration_hours=0,
        pd_kt_v_per_week=1.5, pd_creatinine_clearance_l_week=40, pd_urine_kt_v=0.3
    )
    result2 = calc.calculate(pd)
    print(f"\nPD: Total Kt/V = {result2.spktv}")
    print(f"Adequacy met: {result2.adequacy_met}")
    print(f"Recommendations: {result2.recommendations}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
