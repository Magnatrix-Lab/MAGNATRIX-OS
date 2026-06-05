"""
Testosterone Calculator — Men's Health
Free testosterone, bioavailable testosterone, and hypogonadism diagnosis.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class HypogonadismSeverity(Enum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class TestosteroneProfile:
    total_testosterone_ng_dl: float
    shbg_nmol_l: float
    albumin_g_dl: float
    lh_miu_ml: float
    fsh_miu_ml: float
    estradiol_pg_ml: float
    prolactin_ng_ml: float
    age: int
    morning_sample: bool = True
    bmi: float = 25.0
    on_testosterone_therapy: bool = False
    on_opioids: bool = False
    on_steroids: bool = False
    sleep_apnea: bool = False


@dataclass
class TestosteroneResult:
    calculated_free_testosterone_ng_dl: float
    bioavailable_testosterone_ng_dl: float
    free_testosterone_percent: float
    hypogonadism: bool
    primary_vs_secondary: str
    severity: HypogonadismSeverity
    testosterone_replacement_indicated: bool
    monitoring: List[str]
    contraindications: List[str]
    recommendations: List[str]


class TestosteroneCalculator:
    """Free testosterone calculation and hypogonadism assessment."""

    def calculate(self, profile: TestosteroneProfile) -> TestosteroneResult:
        # Free testosterone (Vermeulen formula approximation)
        # cFT = (TT - N * cBT) where N is constant
        # Simplified: use law of mass action approximation
        # cFT = [TT] / (1 + (SHBG * K_a) + (albumin * K_a_albumin))
        # Approximation constants
        ka_shbg = 1.0  # 1/nM (binding affinity constant approximation)
        ka_albumin = 0.0001  # 1/nM

        shbg_nM = profile.shbg_nmol_l
        albumin_uM = profile.albumin_g_dl * 145.0  # ~convert to uM (simplified)
        albumin_nM = albumin_uM * 1000
        tt_nM = profile.total_testosterone_ng_dl * 0.0347  # ng/dL to nM

        free_fraction = 1 / (1 + shbg_nM * ka_shbg + albumin_nM * ka_albumin)
        free_t_nM = tt_nM * free_fraction
        free_t_ng_dl = free_t_nM / 0.0347

        bioavailable_fraction = free_fraction + (albumin_nM * ka_albumin * free_fraction)
        bioavailable_t_ng_dl = (tt_nM * bioavailable_fraction) / 0.0347

        free_percent = free_fraction * 100

        # Hypogonadism thresholds (morning total T < 300 ng/dL is common threshold)
        # Free T < 5-9 ng/dL (varies by lab)
        if not profile.morning_sample:
            threshold = 250  # Lower threshold for afternoon
            notes = ["Afternoon sample — testosterone naturally lower, confirm with morning sample."]
        else:
            threshold = 300
            notes = []

        if profile.total_testosterone_ng_dl < threshold or free_t_ng_dl < 5:
            hypogonadism = True
            if profile.total_testosterone_ng_dl < 150:
                severity = HypogonadismSeverity.SEVERE
            elif profile.total_testosterone_ng_dl < 230:
                severity = HypogonadismSeverity.MODERATE
            else:
                severity = HypogonadismSeverity.MILD
        else:
            hypogonadism = False
            severity = HypogonadismSeverity.NONE

        # Primary vs secondary
        if hypogonadism:
            if profile.lh_miu_ml > 10 and profile.fsh_miu_ml > 10:
                primary_secondary = "Primary (testicular failure)"
            elif profile.lh_miu_ml < 3 and profile.fsh_miu_ml < 3:
                primary_secondary = "Secondary (hypothalamic/pituitary)"
            else:
                primary_secondary = "Mixed / Indeterminate"
        else:
            primary_secondary = "Not applicable"

        # TRT indication
        trt = (hypogonadism and severity.value in ["moderate", "severe"] and
               not profile.on_testosterone_therapy and profile.morning_sample)

        # Contraindications
        contraindications = []
        if profile.prolactin_ng_ml > 20:
            contraindications.append("Elevated prolactin — evaluate pituitary adenoma before TRT")
        if profile.estradiol_pg_ml > 50:
            contraindications.append("Elevated estradiol — may aromatize with TRT")
        if profile.sleep_apnea:
            contraindications.append("Sleep apnea — TRT may worsen")
        if profile.bmi > 35:
            contraindications.append("Severe obesity — address weight first, aromatization risk")
        if profile.on_opioids:
            notes.append("Opioids suppress GnRH — consider opioid reduction before TRT.")
        if profile.on_steroids:
            notes.append("Exogenous steroids suppress HPA axis — discontinue if possible.")

        recs = []
        if hypogonadism and not trt:
            recs.append("Repeat morning total testosterone + LH/FSH + prolactin")
        if trt:
            recs += ["Testosterone replacement (gel, injection, patch)", "Monitor hematocrit, PSA, lipids every 3-6 months"]
        if "Secondary" in primary_secondary:
            recs += ["Pituitary MRI if no obvious cause", "Evaluate for hemochromatosis, Kallmann syndrome"]
        if "Primary" in primary_secondary:
            recs += ["Karyotype if age < 40 (Klinefelter syndrome)", "Testicular ultrasound if masses suspected"]
        if profile.prolactin_ng_ml > 20:
            recs.append("Prolactinoma workup: MRI sella, visual field testing")

        monitoring = ["Morning testosterone", "Hematocrit (polycythemia risk)", "PSA", "Digital rectal exam"]
        if trt:
            monitoring += ["Lipid panel", "Bone density if prolonged hypogonadism"]

        return TestosteroneResult(
            calculated_free_testosterone_ng_dl=round(free_t_ng_dl, 2),
            bioavailable_testosterone_ng_dl=round(bioavailable_t_ng_dl, 2),
            free_testosterone_percent=round(free_percent, 2),
            hypogonadism=hypogonadism,
            primary_vs_secondary=primary_secondary,
            severity=severity,
            testosterone_replacement_indicated=trt,
            monitoring=monitoring,
            contraindications=contraindications,
            recommendations=recs + notes
        )

    def trt_dose_options(self, severity: str) -> List[dict]:
        """TRT dosing options."""
        return [
            {"form": "Injection (IM/SC)", "dose": "Testosterone cypionate 100-200mg every 1-2 weeks", "notes": "Most cost-effective"},
            {"form": "Transdermal gel", "dose": "50-100mg daily", "notes": "Mimics diurnal rhythm, skin transfer risk"},
            {"form": "Patch", "dose": "4-6mg daily", "notes": "Skin irritation common"},
            {"form": "Pellet", "dose": "150-450mg every 3-6 months", "notes": "Surgical insertion, difficult to remove"},
        ]


def run():
    calc = TestosteroneCalculator()

    print("=" * 60)
    print("Testosterone Calculator")
    print("=" * 60)

    profile = TestosteroneProfile(
        total_testosterone_ng_dl=180, shbg_nmol_l=35, albumin_g_dl=4.2,
        lh_miu_ml=12, fsh_miu_ml=15, estradiol_pg_ml=28, prolactin_ng_ml=8,
        age=45, morning_sample=True, bmi=30, sleep_apnea=False
    )

    result = calc.calculate(profile)
    print(f"\nFree T: {result.calculated_free_testosterone_ng_dl} ng/dL")
    print(f"Bioavailable T: {result.bioavailable_testosterone_ng_dl} ng/dL")
    print(f"Free %: {result.free_testosterone_percent}%")
    print(f"Hypogonadism: {result.hypogonadism} ({result.severity.value})")
    print(f"Type: {result.primary_vs_secondary}")
    print(f"TRT indicated: {result.testosterone_replacement_indicated}")
    print(f"Contraindications: {result.contraindications}")
    print(f"Recommendations: {result.recommendations}")

    print(f"\nTRT options: {calc.trt_dose_options('moderate')}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
