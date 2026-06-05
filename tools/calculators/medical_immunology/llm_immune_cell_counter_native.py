"""
Immune Cell Counter — Immunology
Absolute counts, CD4/CD8 ratio, and immunophenotyping reference.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class ImmuneProfile:
    wbc_k_u_l: float
    lymphocyte_percent: float
    cd4_percent: float
    cd8_percent: float
    cd4_absolute_u_l: float
    cd8_absolute_u_l: float
    cd19_percent: float = 0.0
    cd16_56_percent: float = 0.0
    age_years: int = 35


@dataclass
class ImmuneResult:
    cd4_cd8_ratio: float
    cd4_category: str
    cd8_category: str
    ratio_category: str
    immune_status: str
    hiv_monitoring_applicable: bool
    reference_range_cd4: List[int]
    recommendations: List[str]


class ImmuneCellCalculator:
    """Immunophenotyping and CD4/CD8 ratio assessment."""

    def calculate(self, profile: ImmuneProfile) -> ImmuneResult:
        ratio = profile.cd4_absolute_u_l / profile.cd8_absolute_u_l if profile.cd8_absolute_u_l > 0 else 0

        # CD4 categories
        if profile.cd4_absolute_u_l < 200:
            cd4_cat = "Severe immunodeficiency (AIDS-defining)"
        elif profile.cd4_absolute_u_l < 350:
            cd4_cat = "Moderate immunodeficiency"
        elif profile.cd4_absolute_u_l < 500:
            cd4_cat = "Mild immunodeficiency"
        else:
            cd4_cat = "Normal"

        # CD8 categories
        if profile.cd8_absolute_u_l > 1200:
            cd8_cat = "Elevated (reactive/viral infection)"
        elif profile.cd8_absolute_u_l < 200:
            cd8_cat = "Low (immunodeficiency)"
        else:
            cd8_cat = "Normal"

        # Ratio categories
        if ratio < 0.4:
            ratio_cat = "Inverted (immunodeficiency/viral)"
        elif ratio < 1.0:
            ratio_cat = "Low"
        elif ratio <= 2.5:
            ratio_cat = "Normal"
        else:
            ratio_cat = "Elevated (autoimmune/thymic)"

        # Overall status
        if profile.cd4_absolute_u_l < 200 or ratio < 0.4:
            status = "Immunocompromised"
        elif profile.cd4_absolute_u_l < 500 or ratio < 1.0:
            status = "Immunodeficient risk"
        else:
            status = "Immunocompetent"

        # Reference ranges by age
        if profile.age_years < 6:
            ref_cd4 = [500, 1400]
        elif profile.age_years < 18:
            ref_cd4 = [500, 1200]
        else:
            ref_cd4 = [500, 1400]

        recs = []
        if profile.cd4_absolute_u_l < 200:
            recs += ["Pneumocystis pneumonia (PCP) prophylaxis (TMP-SMX)", "OI prophylaxis assessment", "HIV testing if not known positive"]
        if profile.cd4_absolute_u_l < 350:
            recs += ["Enhanced infection surveillance", "MAC prophylaxis if CD4 < 50"]
        if ratio < 0.4:
            recs.append("Inverted CD4/CD8 ratio — chronic viral infection or immunodeficiency likely")
        if status == "Immunocompetent":
            recs.append("Routine health maintenance")

        return ImmuneResult(
            cd4_cd8_ratio=round(ratio, 2),
            cd4_category=cd4_cat,
            cd8_category=cd8_cat,
            ratio_category=ratio_cat,
            immune_status=status,
            hiv_monitoring_applicable=profile.cd4_absolute_u_l < 500,
            reference_range_cd4=ref_cd4,
            recommendations=recs
        )

    def opportunistic_infection_risk(self, cd4_count: int) -> Dict[str, str]:
        """OI risk stratification by CD4 count."""
        risks = {
            "Pneumocystis jirovecii": "High" if cd4 < 200 else "Low",
            "Toxoplasma gondii": "High" if cd4 < 100 else "Low",
            "Mycobacterium avium complex": "High" if cd4 < 50 else "Low",
            "Cytomegalovirus": "High" if cd4 < 50 else "Low",
            "Cryptococcus neoformans": "High" if cd4 < 100 else "Low",
            "Mycobacterium tuberculosis": "Variable (always screen)",
            "Kaposi sarcoma (HHV-8)": "High" if cd4 < 200 else "Moderate",
            "Non-Hodgkin lymphoma": "High" if cd4 < 100 else "Moderate",
        }
        return risks


def run():
    calc = ImmuneCellCalculator()

    print("=" * 60)
    print("Immune Cell Counter")
    print("=" * 60)

    profile = ImmuneProfile(
        wbc_k_u_l=4.5, lymphocyte_percent=30,
        cd4_percent=18, cd8_percent=35,
        cd4_absolute_u_l=243, cd8_absolute_u_l=472,
        age_years=38
    )

    result = calc.calculate(profile)
    print(f"\nCD4/CD8 ratio: {result.cd4_cd8_ratio}")
    print(f"CD4 status: {result.cd4_category}")
    print(f"CD8 status: {result.cd8_category}")
    print(f"Ratio: {result.ratio_category}")
    print(f"Immune status: {result.immune_status}")
    print(f"Recommendations: {result.recommendations}")
    print(f"OI risk (CD4=243): {calc.opportunistic_infection_risk(243)}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
