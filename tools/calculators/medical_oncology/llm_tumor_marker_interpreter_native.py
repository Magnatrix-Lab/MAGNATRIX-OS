"""
Tumor Marker Interpreter — Oncology
CEA, CA-125, PSA, AFP, CA 19-9 trends and clinical significance.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class MarkerType(Enum):
    CEA = "cea"
    CA125 = "ca125"
    PSA = "psa"
    AFP = "afp"
    CA199 = "ca199"
    LDH = "ldh"
    BETA_HCG = "beta_hcg"
    CA153 = "ca153"
    HE4 = "he4"
    CALCITONIN = "calcitonin"


@dataclass
class MarkerProfile:
    marker: MarkerType
    value: float
    previous_value: Optional[float] = None
    previous_date_days_ago: int = 0
    age: int = 50
    gender: str = ""
    smoking_status: str = "never"
    known_malignancy: str = ""  # e.g., "colorectal", "ovarian"
    treatment_active: bool = False


@dataclass
class MarkerResult:
    interpretation: str
    trend: str
    doubling_time_days: Optional[float]
    clinical_significance: str
    false_positive_causes: List[str]
    follow_up: str
    recommendations: List[str]


class TumorMarkerCalculator:
    """Tumor marker interpretation with trend analysis."""

    THRESHOLDS: Dict[MarkerType, Dict] = {
        MarkerType.CEA: {"normal": 3.0, "elevated": 5.0, "cancer": "colorectal, lung, pancreatic"},
        MarkerType.CA125: {"normal": 35.0, "elevated": 35.0, "cancer": "ovarian, endometrial"},
        MarkerType.PSA: {"normal": 4.0, "elevated": 4.0, "cancer": "prostate"},
        MarkerType.AFP: {"normal": 10.0, "elevated": 10.0, "cancer": "hepatocellular, germ cell"},
        MarkerType.CA199: {"normal": 37.0, "elevated": 37.0, "cancer": "pancreatic, biliary"},
        MarkerType.LDH: {"normal": 250.0, "elevated": 250.0, "cancer": "lymphoma, germ cell, melanoma"},
        MarkerType.BETA_HCG: {"normal": 5.0, "elevated": 5.0, "cancer": "germ cell, choriocarcinoma"},
        MarkerType.CA153: {"normal": 30.0, "elevated": 30.0, "cancer": "breast"},
        MarkerType.HE4: {"normal": 70.0, "elevated": 70.0, "cancer": "ovarian"},
        MarkerType.CALCITONIN: {"normal": 10.0, "elevated": 10.0, "cancer": "medullary thyroid"},
    }

    def calculate(self, profile: MarkerProfile) -> MarkerResult:
        thresholds = self.THRESHOLDS.get(profile.marker, {"normal": 0, "elevated": 0})
        normal = thresholds["normal"]
        cancer_type = thresholds.get("cancer", "")

        if profile.value < normal:
            interp = "Within normal limits"
        elif profile.value < normal * 2:
            interp = "Mildly elevated"
        elif profile.value < normal * 5:
            interp = "Moderately elevated"
        else:
            interp = "Significantly elevated"

        # Trend
        if profile.previous_value and profile.previous_value > 0 and profile.previous_date_days_ago > 0:
            ratio = profile.value / profile.previous_value
            if ratio > 1.5:
                trend = "Rising rapidly"
            elif ratio > 1.1:
                trend = "Rising"
            elif ratio < 0.7:
                trend = "Falling"
            elif ratio < 0.9:
                trend = "Falling slowly"
            else:
                trend = "Stable"
            # Doubling time (simplified)
            if ratio > 1 and profile.previous_date_days_ago > 0:
                doubling = profile.previous_date_days_ago * (math.log(2) / math.log(ratio))
            else:
                doubling = None
        else:
            trend = "No prior data"
            doubling = None

        # Clinical significance
        if profile.known_malignancy and cancer_type and profile.known_malignancy in cancer_type:
            if profile.treatment_active and trend in ["Falling", "Falling slowly"]:
                sig = "Favorable treatment response"
            elif profile.treatment_active and trend in ["Rising", "Rising rapidly"]:
                sig = "Possible treatment failure / progression"
            else:
                sig = f"Monitoring {profile.known_malignancy} disease status"
        else:
            if profile.value > normal * 2:
                sig = "Elevated — evaluate for malignancy or benign causes"
            else:
                sig = "Mild elevation — may be non-specific"

        # False positive causes
        fp = []
        if profile.marker == MarkerType.CEA:
            fp = ["Smoking", "IBD", "COPD", "Liver disease", "Pancreatitis"]
        elif profile.marker == MarkerType.CA125:
            fp = ["Menstruation", "Pregnancy", "Endometriosis", "PID", "Pancreatitis", "Cirrhosis"]
        elif profile.marker == MarkerType.PSA:
            fp = ["BPH", "Prostatitis", "Ejaculation within 48h", "DRE", "Cycling"]
        elif profile.marker == MarkerType.AFP:
            fp = ["Pregnancy", "Hepatitis", "Cirrhosis", "Germ cell tumors"]
        elif profile.marker == MarkerType.CA199:
            fp = ["Pancreatitis", "Cholangitis", "Gallstones", "Thyroid disease"]
        elif profile.marker == MarkerType.LDH:
            fp = ["Hemolysis", "Muscle injury", "Heart failure", "Liver disease"]

        recs = ["Repeat marker in 4-6 weeks to confirm trend", "Correlate with imaging (CT/MRI/PET)"]
        if profile.known_malignancy and trend in ["Rising", "Rising rapidly"]:
            recs.append("Restaging imaging and multidisciplinary tumor board discussion")
        if profile.marker == MarkerType.PSA and profile.value > 4 and profile.value < 10:
            recs.append("Free/total PSA ratio if not done")
        if profile.marker == MarkerType.CA125 and profile.value > 35:
            recs.append("Pelvic ultrasound/MRI if no known ovarian cancer")
        if profile.marker == MarkerType.HE4 and profile.value > 70:
            recs.append("ROMA score calculation for ovarian cancer risk")

        follow = "Repeat in 4-8 weeks if newly elevated, or per treatment protocol"

        return MarkerResult(
            interpretation=interp,
            trend=trend,
            doubling_time_days=round(doubling, 1) if doubling else None,
            clinical_significance=sig,
            false_positive_causes=fp,
            follow_up=follow,
            recommendations=recs
        )


import math


def run():
    calc = TumorMarkerCalculator()

    print("=" * 60)
    print("Tumor Marker Interpreter")
    print("=" * 60)

    profile = MarkerProfile(
        marker=MarkerType.CEA, value=12.5, previous_value=8.0,
        previous_date_days_ago=60, known_malignancy="colorectal",
        treatment_active=True, smoking_status="former"
    )

    result = calc.calculate(profile)
    print(f"\nMarker: {profile.marker.value}")
    print(f"Interpretation: {result.interpretation}")
    print(f"Trend: {result.trend}")
    print(f"Doubling time: {result.doubling_time_days} days")
    print(f"Significance: {result.clinical_significance}")
    print(f"False positives: {result.false_positive_causes}")
    print(f"Recommendations: {result.recommendations}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
