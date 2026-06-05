"""
Autoimmune Risk Calculator — Immunology
ANA titer interpretation, autoimmune disease risk scoring.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class ANAPattern(Enum):
    NEGATIVE = "negative"
    HOMOGENOUS = "homogenous"
    SPECKLED = "speckled"
    NUCLEOLAR = "nucleolar"
    CENTROMERE = "centromere"
    CYTOPLASMIC = "cytoplasmic"


@dataclass
class AutoimmuneProfile:
    ana_titer: int  # 1:40, 1:80, 1:160, 1:320, 1:640, etc.
    ana_pattern: ANAPattern
    age: int
    gender: str
    symptoms: List[str]  # joint_pain, rash, fatigue, raynaud, sicca, photosensitivity
    organ_involvement: List[str] = None  # kidney, lung, CNS, skin, joints
    other_autoantibodies: Dict[str, str] = None  # {"anti-dsDNA": "positive", "anti-Smith": "negative", ...}
    family_history: bool = False

    def __post_init__(self):
        if self.organ_involvement is None:
            self.organ_involvement = []
        if self.other_autoantibodies is None:
            self.other_autoantibodies = {}


@dataclass
class AutoimmuneResult:
    ana_significant: bool
    lupus_probability: str
    scleroderma_probability: str
    sjogren_probability: str
    myositis_probability: str
    other_disease_associations: List[str]
    recommendations: List[str]
    follow_up_tests: List[str]


class AutoimmuneRiskCalculator:
    """ANA and autoimmune disease risk interpretation."""

    def calculate(self, profile: AutoimmuneProfile) -> AutoimmuneResult:
        # ANA significance
        significant = profile.ana_titer >= 160 and profile.ana_pattern != ANAPattern.NEGATIVE
        if profile.age > 60 and profile.ana_titer <= 160 and profile.ana_pattern == ANAPattern.SPECKLED:
            significant = False  # Low-titer speckled in elderly often non-specific

        # Pattern-based associations
        associations = []
        if profile.ana_pattern == ANAPattern.HOMOGENOUS:
            associations.append("SLE, drug-induced lupus, juvenile idiopathic arthritis")
        elif profile.ana_pattern == ANAPattern.SPECKLED:
            associations.append("SLE, Sjogren, MCTD, polymyositis")
        elif profile.ana_pattern == ANAPattern.NUCLEOLAR:
            associations.append("Scleroderma, polymyositis")
        elif profile.ana_pattern == ANAPattern.CENTROMERE:
            associations.append("Limited scleroderma / CREST")
        elif profile.ana_pattern == ANAPattern.CYTOPLASMIC:
            associations.append("Polymyositis, primary biliary cholangitis")

        # Specific autoantibody scoring
        lupus_score = 0
        sclero_score = 0
        sjogren_score = 0
        myositis_score = 0

        if "anti-dsDNA" in profile.other_autoantibodies and profile.other_autoantibodies["anti-dsDNA"] == "positive":
            lupus_score += 5
        if "anti-Smith" in profile.other_autoantibodies and profile.other_autoantibodies["anti-Smith"] == "positive":
            lupus_score += 5
        if "anti-Ro/SSA" in profile.other_autoantibodies and profile.other_autoantibodies["anti-Ro/SSA"] == "positive":
            lupus_score += 2
            sjogren_score += 3
        if "anti-La/SSB" in profile.other_autoantibodies and profile.other_autoantibodies["anti-La/SSB"] == "positive":
            sjogren_score += 3
        if "anti-Scl-70" in profile.other_autoantibodies and profile.other_autoantibodies["anti-Scl-70"] == "positive":
            sclero_score += 5
        if "anti-centromere" in profile.other_autoantibodies and profile.other_autoantibodies["anti-centromere"] == "positive":
            sclero_score += 5
        if "anti-Jo-1" in profile.other_autoantibodies and profile.other_autoantibodies["anti-Jo-1"] == "positive":
            myositis_score += 5
        if "anti-RNP" in profile.other_autoantibodies and profile.other_autoantibodies["anti-RNP"] == "positive":
            lupus_score += 2

        # Clinical symptom scoring
        symptom_score = len(profile.symptoms)
        if "photosensitivity" in profile.symptoms:
            lupus_score += 2
        if "sicca" in profile.symptoms:
            sjogren_score += 2
        if "raynaud" in profile.symptoms:
            sclero_score += 2
        if "joint_pain" in profile.symptoms:
            lupus_score += 1

        # Organ involvement
        if "kidney" in profile.organ_involvement:
            lupus_score += 3
        if "lung" in profile.organ_involvement:
            sclero_score += 2
            lupus_score += 2
        if "skin" in profile.organ_involvement:
            lupus_score += 2
            sclero_score += 1
        if "CNS" in profile.organ_involvement:
            lupus_score += 3

        # Family history
        if profile.family_history:
            lupus_score += 1
            sclero_score += 1
            sjogren_score += 1

        def prob(score):
            if score >= 8:
                return "High"
            elif score >= 5:
                return "Moderate"
            elif score >= 3:
                return "Low"
            else:
                return "Very Low"

        recs = []
        if significant:
            recs.append("Refer to rheumatology for formal evaluation")
        else:
            recs.append("ANA low-titer or non-specific — clinical correlation needed")
        if lupus_score >= 5:
            recs += ["SLE workup: complement levels (C3/C4), anti-dsDNA, urinalysis, ESR/CRP"]
        if sclero_score >= 5:
            recs += ["Scleroderma workup: PFTs, echo, capillaroscopy, anti-Scl-70/centromere"]
        if sjogren_score >= 5:
            recs += ["Sjogren workup: Schirmer test, salivary gland biopsy, RF, anti-SSA/SSB"]
        if myositis_score >= 5:
            recs += ["Myositis workup: CK, aldolase, EMG, muscle biopsy, anti-Jo-1 panel"]

        follow_up = ["Repeat ANA if initially negative but high suspicion"]
        if lupus_score >= 5:
            follow_up += ["SLICC/ACR classification criteria scoring", "Lupus anticoagulant, anti-cardiolipin"]
        if sclero_score >= 5:
            follow_up += ["Nailfold capillaroscopy", "6-minute walk test", "HRCT chest"]

        return AutoimmuneResult(
            ana_significant=significant,
            lupus_probability=prob(lupus_score),
            scleroderma_probability=prob(sclero_score),
            sjogren_probability=prob(sjogren_score),
            myositis_probability=prob(myositis_score),
            other_disease_associations=associations,
            recommendations=recs,
            follow_up_tests=follow_up
        )


def run():
    calc = AutoimmuneRiskCalculator()

    print("=" * 60)
    print("Autoimmune Risk Calculator")
    print("=" * 60)

    profile = AutoimmuneProfile(
        ana_titer=320, ana_pattern=ANAPattern.SPECKLED,
        age=32, gender="female",
        symptoms=["joint_pain", "fatigue", "photosensitivity", "rash"],
        organ_involvement=["kidney", "skin"],
        other_autoantibodies={"anti-dsDNA": "positive", "anti-Ro/SSA": "positive"},
        family_history=True
    )

    result = calc.calculate(profile)
    print(f"\nANA significant: {result.ana_significant}")
    print(f"Lupus probability: {result.lupus_probability}")
    print(f"Scleroderma probability: {result.scleroderma_probability}")
    print(f"Sjogren probability: {result.sjogren_probability}")
    print(f"Myositis probability: {result.myositis_probability}")
    print(f"Associations: {result.other_disease_associations}")
    print(f"Recommendations: {result.recommendations}")
    print(f"Follow-up: {result.follow_up_tests}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
