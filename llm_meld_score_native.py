"""
MELD Score Calculator — Hepatology
Model for End-Stage Liver Disease score for transplant prioritization.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum
import math


@dataclass
class MELDProfile:
    creatinine_mg_dl: float
    bilirubin_mg_dl: float
    inr: float
    sodium_mmol_l: float = 140.0
    dialysis_last_week: bool = False


@dataclass
class MELDResult:
    meld_score: float
    meld_na_score: float
    three_month_mortality: float
    priority_category: str
    transplant_listing: bool
    recommendations: List[str]


class MELDCalculator:
    """MELD and MELD-Na calculator for liver transplant priority."""

    def calculate(self, profile: MELDProfile) -> MELDResult:
        # Dialysis override
        creatinine = profile.creatinine_mg_dl
        if profile.dialysis_last_week:
            creatinine = 4.0
        if creatinine < 1.0:
            creatinine = 1.0

        # MELD formula (original 2001, updated 2006)
        bilirubin = max(profile.bilirubin_mg_dl, 1.0)
        inr = max(profile.inr, 1.0)

        meld = (3.78 * math.log(bilirubin) +
                11.2 * math.log(inr) +
                9.57 * math.log(creatinine) + 6.43)

        meld = max(6, min(meld, 40))

        # MELD-Na (2016)
        sodium = max(min(profile.sodium_mmol_l, 137), 125)
        meld_na = meld - sodium - (0.025 * meld * (140 - sodium)) + 140
        meld_na = max(6, min(meld_na, 40))

        # 3-month mortality estimate (rough)
        if meld_na <= 9:
            mortality = 1.9
        elif meld_na <= 19:
            mortality = 6.0
        elif meld_na <= 29:
            mortality = 19.6
        elif meld_na <= 39:
            mortality = 52.6
        else:
            mortality = 71.3

        if meld_na >= 15:
            priority = "High priority for transplant listing"
            listing = True
        elif meld_na >= 10:
            priority = "Moderate priority — monitor closely"
            listing = False
        else:
            priority = "Low priority"
            listing = False

        recs = ["Hepatology referral", "HCC screening (ultrasound + AFP every 6 months)", "Variceal surveillance endoscopy"]
        if listing:
            recs += ["Transplant center evaluation", "Nutritional assessment", "Cardiac/Pulmonary workup"]
        if profile.dialysis_last_week:
            recs.append("Combined liver-kidney transplant evaluation if prolonged hepatorenal syndrome")

        return MELDResult(
            meld_score=round(meld, 1),
            meld_na_score=round(meld_na, 1),
            three_month_mortality=round(mortality, 1),
            priority_category=priority,
            transplant_listing=listing,
            recommendations=recs
        )

    def meld_3_0(self, albumin_g_dl: float, sodium_mmol_l: float, creatinine_mg_dl: float,
                 bilirubin_mg_dl: float, inr: float) -> dict:
        """MELD 3.0 (2021) with albumin and female sex bonus."""
        # Simplified — full MELD 3.0 includes sex and albumin
        # This is a partial implementation
        base = self.calculate(MELDProfile(creatinine_mg_dl, bilirubin_mg_dl, inr, sodium_mmol_l))
        albumin_bonus = max(0, (3.5 - albumin_g_dl)) * 2
        return {
            "meld_3_0_estimate": round(base.meld_na_score + albumin_bonus, 1),
            "note": "Full MELD 3.0 includes female sex bonus (+1.33 points). Refer to OPTN calculator.",
            "meld_na": base.meld_na_score
        }


def run():
    calc = MELDCalculator()

    print("=" * 60)
    print("MELD Score Calculator")
    print("=" * 60)

    cases = [
        MELDProfile(1.2, 3.5, 1.8, 138, False),
        MELDProfile(2.8, 8.0, 2.5, 132, True),
    ]

    for i, c in enumerate(cases, 1):
        result = calc.calculate(c)
        print(f"\nCase {i}: MELD = {result.meld_score}, MELD-Na = {result.meld_na_score}")
        print(f"  3-month mortality: {result.three_month_mortality}%")
        print(f"  Priority: {result.priority_category}")
        print(f"  Listing: {result.transplant_listing}")

    print(f"\nMELD 3.0 estimate: {calc.meld_3_0(2.8, 135, 2.0, 6.0, 2.2)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
