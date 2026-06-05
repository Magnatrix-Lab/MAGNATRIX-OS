"""
Anemia Classification Calculator — Hematology
Morphological classification (MCV/MCH) and differential diagnosis.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class AnemiaType(Enum):
    MICROCYTIC = "microcytic"
    NORMOCYTIC = "normocytic"
    MACROCYTIC = "macrocytic"


class AnemiaCause(Enum):
    IRON_DEFICIENCY = "iron_deficiency"
    THALASSEMIA = "thalassemia"
    ANEMIA_OF_CHRONIC_DISEASE = "anemia_of_chronic_disease"
    SIDEROBLASTIC = "sideroblastic"
    B12_FOLATE_DEFICIENCY = "b12_folate_deficiency"
    LIVER_DISEASE = "liver_disease"
    HEMOLYSIS = "hemolysis"
    APLASTIC = "aplastic"
    BONE_MARROW_FAILURE = "bone_marrow_failure"
    CHRONIC_KIDNEY_DISEASE = "chronic_kidney_disease"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class AnemiaProfile:
    hemoglobin_g_dl: float
    mcv_fl: float
    mch_pg: float
    rdw_cv: float
    ferritin_ng_ml: float
    iron_mcg_dl: float
    tibc_mcg_dl: float
    transferrin_saturation: float
    b12_pg_ml: float
    folate_ng_ml: float
    reticulocyte_percent: float
    creatinine_mg_dl: float
    signs_of_hemolysis: bool = False
    chronic_disease: bool = False
    pregnancy: bool = False


@dataclass
class AnemiaResult:
    anemia_present: bool
    severity: str
    morphological_type: AnemiaType
    most_likely_causes: List[AnemiaCause]
    iron_study_interpretation: str
    recommendations: List[str]
    follow_up_tests: List[str]


class AnemiaCalculator:
    """Anemia classification based on CBC and iron studies."""

    def calculate(self, profile: AnemiaProfile) -> AnemiaResult:
        # Anemia severity (WHO criteria, slightly modified)
        if profile.pregnancy:
            anemia_threshold = 11.0 if profile.pregnancy else 12.0
        else:
            anemia_threshold = 12.0

        anemia_present = profile.hemoglobin_g_dl < anemia_threshold
        if not anemia_present:
            hgb = profile.hemoglobin_g_dl
            if hgb >= 12.0:
                severity = "None"
            else:
                severity = "Mild"
        elif profile.hemoglobin_g_dl < 8.0:
            severity = "Severe"
        elif profile.hemoglobin_g_dl < 10.0:
            severity = "Moderate"
        else:
            severity = "Mild"

        # Morphology by MCV
        if profile.mcv_fl < 80:
            morph = AnemiaType.MICROCYTIC
        elif profile.mcv_fl > 100:
            morph = AnemiaType.MACROCYTIC
        else:
            morph = AnemiaType.NORMOCYTIC

        causes = []
        iron_interp = ""

        # Iron studies
        if profile.ferritin_ng_ml < 15:
            iron_interp = "Iron deficiency likely (ferritin < 15)"
            causes.append(AnemiaCause.IRON_DEFICIENCY)
        elif profile.ferritin_ng_ml < 30 and profile.transferrin_saturation < 20:
            iron_interp = "Iron deficiency possible (ferritin < 30, low TSAT)"
            causes.append(AnemiaCause.IRON_DEFICIENCY)
        elif profile.ferritin_ng_ml > 100 and profile.transferrin_saturation < 20 and profile.chronic_disease:
            iron_interp = "Functional iron deficiency (anemia of chronic disease)"
            causes.append(AnemiaCause.ANEMIA_OF_CHRONIC_DISEASE)
        elif profile.ferritin_ng_ml > 200 and profile.transferrin_saturation > 50:
            iron_interp = "Iron overload pattern — sideroblastic anemia possible"
            causes.append(AnemiaCause.SIDEROBLASTIC)

        # MCV-based differentials
        if morph == AnemiaType.MICROCYTIC:
            if profile.ferritin_ng_ml < 30:
                causes.append(AnemiaCause.IRON_DEFICIENCY)
            if profile.ferritin_ng_ml > 50 and profile.rdw_cv < 14:
                causes.append(AnemiaCause.THALASSEMIA)
            if profile.chronic_disease:
                causes.append(AnemiaCause.ANEMIA_OF_CHRONIC_DISEASE)
            if profile.iron_mcg_dl > 100 and profile.transferrin_saturation > 50:
                causes.append(AnemiaCause.SIDEROBLASTIC)
        elif morph == AnemiaType.MACROCYTIC:
            if profile.b12_pg_ml < 200:
                causes.append(AnemiaCause.B12_FOLATE_DEFICIENCY)
            if profile.folate_ng_ml < 4:
                causes.append(AnemiaCause.B12_FOLATE_DEFICIENCY)
            if profile.reticulocyte_percent > 2:
                causes.append(AnemiaCause.HEMOLYSIS)
            if profile.creatinine_mg_dl > 2.0:
                causes.append(AnemiaCause.CHRONIC_KIDNEY_DISEASE)
        else:  # Normocytic
            if profile.chronic_disease:
                causes.append(AnemiaCause.ANEMIA_OF_CHRONIC_DISEASE)
            if profile.creatinine_mg_dl > 2.0:
                causes.append(AnemiaCause.CHRONIC_KIDNEY_DISEASE)
            if profile.signs_of_hemolysis or profile.reticulocyte_percent > 2:
                causes.append(AnemiaCause.HEMOLYSIS)
            if profile.reticulocyte_percent < 0.5:
                causes.append(AnemiaCause.APLASTIC)
                causes.append(AnemiaCause.BONE_MARROW_FAILURE)

        # Remove duplicates
        causes = list(dict.fromkeys(causes))
        if not causes:
            causes = [AnemiaCause.UNKNOWN]

        recs = ["Treat underlying cause", "Transfuse if Hgb < 7 or symptomatic"]
        if AnemiaCause.IRON_DEFICIENCY in causes:
            recs += ["Oral iron 65mg elemental daily (ferrous sulfate)", "Recheck CBC in 8-12 weeks"]
        if AnemiaCause.B12_FOLATE_DEFICIENCY in causes:
            recs += ["B12 1000mcg IM weekly x4 then monthly, or 1000mcg oral daily", "Folate 1mg daily if deficient"]
        if AnemiaCause.CHRONIC_KIDNEY_DISEASE in causes:
            recs.append("ESA if Hgb < 10 and symptomatic on dialysis")
        if AnemiaCause.HEMOLYSIS in causes:
            recs += ["Haptoglobin, LDH, bilirubin, peripheral smear", "Coombs test"]

        follow_up = ["Peripheral smear", "Reticulocyte count", "Iron panel if microcytic"]
        if AnemiaCause.B12_FOLATE_DEFICIENCY in causes:
            follow_up += ["MMA, homocysteine", "Intrinsic factor antibodies (pernicious anemia)"]
        if AnemiaCause.HEMOLYSIS in causes:
            follow_up += ["LDH, haptoglobin, indirect bilirubin", "Direct antiglobulin test (Coombs)"]

        return AnemiaResult(
            anemia_present=anemia_present,
            severity=severity,
            morphological_type=morph,
            most_likely_causes=causes,
            iron_study_interpretation=iron_interp,
            recommendations=recs,
            follow_up_tests=follow_up
        )


def run():
    calc = AnemiaCalculator()

    print("=" * 60)
    print("Anemia Classification Calculator")
    print("=" * 60)

    profile = AnemiaProfile(
        hemoglobin_g_dl=9.2, mcv_fl=72, mch_pg=22, rdw_cv=16.5,
        ferritin_ng_ml=8, iron_mcg_dl=35, tibc_mcg_dl=480,
        transferrin_saturation=7, b12_pg_ml=350, folate_ng_ml=8,
        reticulocyte_percent=0.8, creatinine_mg_dl=1.0
    )

    result = calc.calculate(profile)
    print(f"\nAnemia present: {result.anemia_present}, Severity: {result.severity}")
    print(f"Morphology: {result.morphological_type.value}")
    print(f"Likely causes: {[c.value for c in result.most_likely_causes]}")
    print(f"Iron studies: {result.iron_study_interpretation}")
    print(f"Recommendations: {result.recommendations}")
    print(f"Follow-up: {result.follow_up_tests}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
