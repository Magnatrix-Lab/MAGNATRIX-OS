"""
Urinalysis Calculator — Nephrology
Dipstick interpretation, urine sediment analysis, and kidney disease risk.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class UrineColor(Enum):
    CLEAR = "clear"
    STRAW = "straw"
    YELLOW = "yellow"
    AMBER = "amber"
    RED = "red"
    BROWN = "brown"
    CLOUDY = "cloudy"


@dataclass
class UrinalysisProfile:
    color: UrineColor
    specific_gravity: float
    ph: float
    protein_mg_dl: float
    glucose_mg_dl: float
    ketones: str = "negative"  # negative, trace, small, moderate, large
    bilirubin: bool = False
    blood: str = "negative"  # negative, trace, small, moderate, large
    leukocytes: str = "negative"
    nitrites: bool = False
    urobilinogen: float = 0.0  # mg/dL
    rbc_per_hpf: int = 0
    wbc_per_hpf: int = 0
    bacteria: bool = False
    casts: List[str] = None  # hyaline, granular, rbc, wbc, waxy, fatty
    crystals: List[str] = None
    epithelial_cells: str = "few"  # none, few, moderate, many

    def __post_init__(self):
        if self.casts is None:
            self.casts = []
        if self.crystals is None:
            self.crystals = []


@dataclass
class UrinalysisResult:
    findings: List[str]
    abnormalities: List[str]
    suspected_diagnoses: List[str]
    culture_indicated: bool
    microscopy_needed: bool
    follow_up_tests: List[str]
    recommendations: List[str]


class UrinalysisCalculator:
    """Urine dipstick and sediment interpretation."""

    def calculate(self, profile: UrinalysisProfile) -> UrinalysisResult:
        findings = []
        abnormalities = []
        diagnoses = []
        culture = False
        microscopy = False
        recs = []

        # Color
        if profile.color == UrineColor.RED:
            findings.append("Gross hematuria")
            abnormalities.append("Hematuria")
            diagnoses.append("UTI, stones, malignancy, glomerulonephritis")
            microscopy = True
        elif profile.color == UrineColor.BROWN:
            findings.append("Dark urine — possible bilirubin, hemoglobin, myoglobin")
            abnormalities.append("Abnormal color")
            diagnoses.append("Hemolysis, rhabdomyolysis, bilirubinuria")
        elif profile.color == UrineColor.CLOUDY:
            findings.append("Cloudy urine")
            abnormalities.append("Possible pyuria or crystalluria")

        # Specific gravity
        if profile.specific_gravity > 1.030:
            findings.append("High specific gravity — dehydration or contrast")
        elif profile.specific_gravity < 1.003:
            findings.append("Low specific gravity — DI, overhydration, tubular damage")

        # pH
        if profile.ph > 7.5:
            findings.append("Alkaline pH — Proteus infection or RTA")
            abnormalities.append("Alkaline pH")
        elif profile.ph < 5.0:
            findings.append("Acidic pH — normal or metabolic acidosis")

        # Protein
        if profile.protein_mg_dl > 30:
            findings.append(f"Proteinuria ({profile.protein_mg_dl} mg/dL)")
            abnormalities.append("Proteinuria")
            diagnoses.append("Glomerular disease, diabetic nephropathy, hypertension")
            follow_up = ["Urine protein-to-creatinine ratio", "24-hour urine protein", "Renal panel"]
        else:
            follow_up = []

        # Glucose
        if profile.glucose_mg_dl > 100:
            findings.append("Glucosuria")
            abnormalities.append("Hyperglycemia or proximal tubular defect")
            diagnoses.append("Diabetes mellitus, Fanconi syndrome")

        # Ketones
        if profile.ketones != "negative":
            findings.append(f"Ketonuria: {profile.ketones}")
            abnormalities.append("Ketones")
            diagnoses.append("DKA, starvation, low-carb diet")

        # Bilirubin
        if profile.bilirubin:
            findings.append("Bilirubinuria")
            abnormalities.append("Conjugated hyperbilirubinemia")
            diagnoses.append("Hepatocellular disease, cholestasis")

        # Blood
        if profile.blood != "negative":
            findings.append(f"Blood: {profile.blood}")
            abnormalities.append("Hematuria")
            diagnoses.append("UTI, stones, trauma, malignancy, GN")
            microscopy = True
            if "rbc" not in profile.casts:
                follow_up.append("Urine culture", "Urine microscopy", "CT urogram if persistent")

        # Leukocytes / nitrites
        if profile.leukocytes != "negative" or profile.nitrites:
            findings.append("Pyuria / nitrites — UTI likely")
            abnormalities.append("UTI indicators")
            diagnoses.append("Urinary tract infection")
            culture = True
            recs.append("Urine culture and sensitivity")

        # Microscopy
        if profile.rbc_per_hpf > 3:
            abnormalities.append(f"RBCs {profile.rbc_per_hpf}/HPF")
            microscopy = True
        if profile.wbc_per_hpf > 5:
            abnormalities.append(f"WBCs {profile.wbc_per_hpf}/HPF")
            microscopy = True
            culture = True
        if profile.bacteria:
            abnormalities.append("Bacteria on microscopy")
            culture = True

        # Casts
        if "rbc" in profile.casts:
            abnormalities.append("RBC casts")
            diagnoses.append("Glomerulonephritis")
        if "wbc" in profile.casts:
            abnormalities.append("WBC casts")
            diagnoses.append("Pyelonephritis, interstitial nephritis")
        if "waxy" in profile.casts:
            abnormalities.append("Waxy casts")
            diagnoses.append("Advanced CKD / renal failure")
        if "fatty" in profile.casts:
            abnormalities.append("Fatty casts")
            diagnoses.append("Nephrotic syndrome")

        if not abnormalities:
            findings.append("No significant abnormalities")
            recs.append("Routine follow-up as clinically indicated")

        if culture:
            recs.append("Start empiric antibiotics if symptomatic UTI, adjust based on culture")
        if microscopy:
            recs.append("Urine microscopy by trained personnel")
        if "proteinuria" in [a.lower() for a in abnormalities] or profile.protein_mg_dl > 30:
            recs.append("Quantify proteinuria and evaluate for renal disease")

        return UrinalysisResult(
            findings=findings,
            abnormalities=abnormalities,
            suspected_diagnoses=list(set(diagnoses)),
            culture_indicated=culture,
            microscopy_needed=microscopy,
            follow_up_tests=follow_up,
            recommendations=recs
        )


def run():
    calc = UrinalysisCalculator()

    print("=" * 60)
    print("Urinalysis Calculator")
    print("=" * 60)

    profile = UrinalysisProfile(
        color=UrineColor.RED, specific_gravity=1.025, ph=6.5,
        protein_mg_dl=50, glucose_mg_dl=80, blood="moderate",
        leukocytes="small", nitrites=True, rbc_per_hpf=25, wbc_per_hpf=12,
        bacteria=True, casts=["wbc"], crystals=["calcium oxalate"]
    )

    result = calc.calculate(profile)
    print(f"\nFindings: {result.findings}")
    print(f"Abnormalities: {result.abnormalities}")
    print(f"Suspected: {result.suspected_diagnoses}")
    print(f"Culture needed: {result.culture_indicated}")
    print(f"Microscopy needed: {result.microscopy_needed}")
    print(f"Follow-up: {result.follow_up_tests}")
    print(f"Recommendations: {result.recommendations}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
