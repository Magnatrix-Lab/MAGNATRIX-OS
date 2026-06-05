"""
Thyroid Function Calculator — Endocrinology
TSH/T3/T4 interpretation, TSH index, and thyroid disorder risk.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ThyroidStatus(Enum):
    EUTHYROID = "euthyroid"
    SUBCLINICAL_HYPOTHYROIDISM = "subclinical_hypothyroidism"
    OVERT_HYPOTHYROIDISM = "overt_hypothyroidism"
    SUBCLINICAL_HYPERTHYROIDISM = "subclinical_hyperthyroidism"
    OVERT_HYPERTHYROIDISM = "overt_hyperthyroidism"
    CENTRAL_HYPOTHYROIDISM = "central_hypothyroidism"
    THYROIDITIS = "thyroiditis"


@dataclass
class ThyroidProfile:
    tsh_miu_l: float
    free_t4_pmol_l: Optional[float] = None
    free_t3_pmol_l: Optional[float] = None
    tpo_antibodies_iu_ml: Optional[float] = None
    tg_antibodies_iu_ml: Optional[float] = None
    pregnancy: bool = False
    age: int = 35
    on_thyroid_medication: bool = False
    on_biotin: bool = False


@dataclass
class ThyroidResult:
    status: ThyroidStatus
    tsh_interpretation: str
    ft4_interpretation: Optional[str]
    ft3_interpretation: Optional[str]
    risk_hashimoto: bool
    risk_graves: bool
    follow_up: str
    recommendations: List[str]
    notes: List[str]


class ThyroidCalculator:
    """TSH and thyroid hormone interpretation."""

    def calculate(self, profile: ThyroidProfile) -> ThyroidResult:
        notes = []
        recs = []

        if profile.on_biotin:
            notes.append("Biotin supplementation can falsely lower TSH and raise T3/T4 — stop 2-3 days before retest.")
        if profile.on_thyroid_medication:
            notes.append("On thyroid medication — interpret in context of dose and timing.")

        # Pregnancy-adjusted TSH ranges (trimester 1)
        if profile.pregnancy:
            tsh_low, tsh_high = 0.1, 2.5
        else:
            tsh_low, tsh_high = 0.4, 4.0

        # TSH interpretation
        if profile.tsh_miu_l < tsh_low:
            tsh_interp = "Low TSH"
        elif profile.tsh_miu_l > tsh_high:
            tsh_interp = "High TSH"
        else:
            tsh_interp = "TSH within reference"

        # FT4 interpretation
        ft4_interp = None
        if profile.free_t4_pmol_l is not None:
            ft4_low, ft4_high = 10.0, 22.0
            if profile.free_t4_pmol_l < ft4_low:
                ft4_interp = "Low FT4"
            elif profile.free_t4_pmol_l > ft4_high:
                ft4_interp = "High FT4"
            else:
                ft4_interp = "FT4 within reference"

        # FT3 interpretation
        ft3_interp = None
        if profile.free_t3_pmol_l is not None:
            ft3_low, ft3_high = 3.5, 6.5
            if profile.free_t3_pmol_l < ft3_low:
                ft3_interp = "Low FT3"
            elif profile.free_t3_pmol_l > ft3_high:
                ft3_interp = "High FT3"
            else:
                ft3_interp = "FT3 within reference"

        # Status determination
        if profile.tsh_miu_l > tsh_high:
            if ft4_interp and "Low" in ft4_interp:
                status = ThyroidStatus.OVERT_HYPOTHYROIDISM
            else:
                status = ThyroidStatus.SUBCLINICAL_HYPOTHYROIDISM
        elif profile.tsh_miu_l < tsh_low:
            if ft4_interp and "High" in ft4_interp:
                status = ThyroidStatus.OVERT_HYPERTHYROIDISM
            else:
                status = ThyroidStatus.SUBCLINICAL_HYPERTHYROIDISM
        else:
            if ft4_interp and "Low" in ft4_interp:
                status = ThyroidStatus.CENTRAL_HYPOTHYROIDISM
            else:
                status = ThyroidStatus.EUTHYROID

        # Autoimmune risk
        hashimoto = (profile.tpo_antibodies_iu_ml and profile.tpo_antibodies_iu_ml > 34) or                     (profile.tg_antibodies_iu_ml and profile.tg_antibodies_iu_ml > 40)
        graves = (profile.tpo_antibodies_iu_ml and profile.tpo_antibodies_iu_ml > 34) and status.value.endswith("hyperthyroidism")

        if hashimoto:
            notes.append("Positive thyroid antibodies — Hashimoto's thyroiditis likely.")
        if graves:
            notes.append("Hyperthyroidism + antibodies — consider Graves' disease. TRAb testing recommended.")

        # Follow-up
        if status == ThyroidStatus.EUTHYROID:
            follow = "Routine screening every 1-2 years if risk factors present"
        elif status == ThyroidStatus.SUBCLINICAL_HYPOTHYROIDISM:
            follow = "Recheck TSH + FT4 in 3-6 months; treat if TSH > 10 or symptomatic"
        elif status == ThyroidStatus.OVERT_HYPOTHYROIDISM:
            follow = "Start levothyroxine; recheck TSH in 6-8 weeks"
        elif status == ThyroidStatus.SUBCLINICAL_HYPERTHYROIDISM:
            follow = "Recheck in 1-3 months; evaluate for atrial fibrillation/osteoporosis"
        elif status == ThyroidStatus.OVERT_HYPERTHYROIDISM:
            follow = "Urgent endocrinology; antithyroid meds / radioactive iodine / surgery"
        else:
            follow = "Endocrinology referral for central causes"

        if status.value.endswith("hypothyroidism"):
            recs.append("Levothyroxine if indicated; start low in elderly/cardiac patients")
        if status.value.endswith("hyperthyroidism"):
            recs.append("Methimazole (PTU if pregnant); beta-blocker for symptoms")
        if hashimoto and not status.value.endswith("hypothyroidism"):
            recs.append("Annual TSH monitoring — Hashimoto's can progress to hypothyroidism")
        if profile.pregnancy and status != ThyroidStatus.EUTHYROID:
            recs.append("Urgent obstetric-endocrine co-management — thyroid affects fetal neurodevelopment")

        return ThyroidResult(
            status=status,
            tsh_interpretation=tsh_interp,
            ft4_interpretation=ft4_interp,
            ft3_interpretation=ft3_interp,
            risk_hashimoto=hashimoto,
            risk_graves=graves,
            follow_up=follow,
            recommendations=recs,
            notes=notes
        )


def run():
    calc = ThyroidCalculator()

    print("=" * 60)
    print("Thyroid Function Calculator")
    print("=" * 60)

    cases = [
        ThyroidProfile(tsh_miu_l=8.5, free_t4_pmol_l=9.0, free_t3_pmol_l=3.2, tpo_antibodies_iu_ml=120),
        ThyroidProfile(tsh_miu_l=0.2, free_t4_pmol_l=28.0, free_t3_pmol_l=8.0, tpo_antibodies_iu_ml=45),
        ThyroidProfile(tsh_miu_l=2.5, free_t4_pmol_l=15.0, free_t3_pmol_l=5.0),
    ]

    for i, c in enumerate(cases, 1):
        result = calc.calculate(c)
        print(f"\nCase {i}: TSH={c.tsh_miu_l}, FT4={c.free_t4_pmol_l}")
        print(f"  Status: {result.status.value}")
        print(f"  Hashimoto risk: {result.risk_hashimoto}, Graves risk: {result.risk_graves}")
        print(f"  Follow-up: {result.follow_up}")
        print(f"  Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
