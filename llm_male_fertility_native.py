"""
Male Fertility Assessment — Men's Health
Semen analysis interpretation, hormonal assessment, and recommendations.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class SemenQuality(Enum):
    NORMAL = "normal"
    MILD_ABNORMALITY = "mild_abnormality"
    MODERATE_ABNORMALITY = "moderate_abnormality"
    SEVERE_ABNORMALITY = "severe_abnormality"
    AZOOSPERMIA = "azoospermia"


@dataclass
class FertilityProfile:
    volume_ml: float
    concentration_millions_ml: float
    total_motility_percent: float
    progressive_motility_percent: float
    normal_morphology_percent: float
    ph: float
    leukocytes_millions_ml: float
    sperm_agglutination: bool = False
    fructose_present: bool = True
    fsh_miu_ml: float = 0.0
    lh_miu_ml: float = 0.0
    testosterone_ng_dl: float = 0.0
    prolactin_ng_ml: float = 0.0
    estradiol_pg_ml: float = 0.0
    age: int = 35
    abstinence_days: int = 2
    previous_vasectomy: bool = False
    varicocele: bool = False
    cryptorchidism_history: bool = False
    infections_history: List[str] = None
    medications: List[str] = None

    def __post_init__(self):
        if self.infections_history is None:
            self.infections_history = []
        if self.medications is None:
            self.medications = []


@dataclass
class FertilityResult:
    semen_quality: SemenQuality
    total_sperm_count_millions: float
    total_motile_count_millions: float
    who_2010_compliant: bool
    primary_infertility_factor: str
    hormonal_status: str
    recommendations: List[str]
    follow_up_tests: List[str]
    icsi_recommended: bool
    notes: List[str]


class FertilityCalculator:
    """Male fertility assessment based on semen analysis and hormones."""

    def calculate(self, profile: FertilityProfile) -> FertilityResult:
        notes = []
        total_count = profile.volume_ml * profile.concentration_millions_ml
        motile_count = total_count * (profile.total_motility_percent / 100)

        # WHO 2010 criteria:
        # Volume >= 1.5mL, Concentration >= 15M/mL, Total motility >= 40%, Progressive >= 32%, Morphology >= 4%
        compliant = (profile.volume_ml >= 1.5 and profile.concentration_millions_ml >= 15 and
                     profile.total_motility_percent >= 40 and profile.progressive_motility_percent >= 32 and
                     profile.normal_morphology_percent >= 4)

        if profile.concentration_millions_ml == 0:
            quality = SemenQuality.AZOOSPERMIA
            factor = "Azoospermia — obstructive vs non-obstructive evaluation"
            icsi = False
        elif total_count < 5:
            quality = SemenQuality.SEVERE_ABNORMALITY
            factor = "Severe oligospermia"
            icsi = True
        elif total_count < 15 or profile.total_motility_percent < 30 or profile.normal_morphology_percent < 3:
            quality = SemenQuality.MODERATE_ABNORMALITY
            factor = "Moderate oligo/astheno/teratospermia"
            icsi = True
        elif total_count < 39 or not compliant:
            quality = SemenQuality.MILD_ABNORMALITY
            factor = "Mild abnormality"
            icsi = False
        else:
            quality = SemenQuality.NORMAL
            factor = "No significant male factor identified"
            icsi = False

        # Hormonal assessment
        if profile.fsh_miu_ml > 10 and profile.testosterone_ng_dl < 300:
            hormonal = "Hypergonadotropic hypogonadism (primary testicular failure)"
        elif profile.fsh_miu_ml < 3 and profile.lh_miu_ml < 3 and profile.testosterone_ng_dl < 300:
            hormonal = "Hypogonadotropic hypogonadism (secondary)"
        elif profile.prolactin_ng_ml > 20:
            hormonal = "Hyperprolactinemia — evaluate pituitary"
        elif profile.testosterone_ng_dl < 300 and profile.fsh_miu_ml < 10:
            hormonal = "Low testosterone with normal FSH — mixed/functional hypogonadism"
        else:
            hormonal = "Hormonal profile appropriate for semen quality"

        # Specific findings
        if profile.leukocytes_millions_ml > 1:
            notes.append("Leukocytospermia — infection/inflammation may impair fertility. Semen culture recommended.")
        if not profile.fructose_present:
            notes.append("Absent fructose — ejaculatory duct obstruction or seminal vesicle agenesis.")
        if profile.sperm_agglutination:
            notes.append("Sperm agglutination — anti-sperm antibodies suspected. MAR test recommended.")
        if profile.ph < 7.0:
            notes.append("Low semen pH — possible ejaculatory duct obstruction or CBAVD.")
        if profile.varicocele:
            notes.append("Varicocele present — may contribute to oligospermia, consider surgical repair if symptomatic.")
        if profile.cryptorchidism_history:
            notes.append("History of cryptorchidism — increased risk of testicular failure and malignancy.")
        if profile.previous_vasectomy:
            notes.append("Previous vasectomy — reversal or sperm retrieval for ICSI if desired.")
        if any(m in ["testosterone", "anabolic steroids"] for m in profile.medications):
            notes.append("Exogenous testosterone/anabolic steroids suppress spermatogenesis — discontinue if fertility desired.")

        recs = ["Repeat semen analysis in 2-3 months (spermatogenesis cycle)", "Avoid heat exposure (saunas, hot tubs, tight clothing)"]
        if quality in [SemenQuality.MODERATE_ABNORMALITY, SemenQuality.SEVERE_ABNORMALITY]:
            recs += ["Fertility specialist / reproductive urology referral", "Consider antioxidant supplementation (vitamin C, E, CoQ10, zinc)"]
        if quality == SemenQuality.AZOOSPERMIA:
            recs += ["Karyotype and Y-chromosome microdeletion testing", "Testicular biopsy vs. sperm retrieval evaluation", "Genetic counseling"]
        if icsi:
            recs.append("ICSI may be required for fertilization with this semen quality")
        if profile.varicocele and quality != SemenQuality.NORMAL:
            recs.append("Varicocelectomy may improve semen parameters in 60-80% of cases")
        if "mumps" in [h.lower() for h in profile.infections_history]:
            recs.append("Post-mumps orchitis — testicular atrophy risk, sperm retrieval may be needed")

        follow_up = ["Repeat semen analysis x2", "Hormonal panel (FSH, LH, testosterone, prolactin, estradiol)", "Scrotal ultrasound"]
        if quality == SemenQuality.AZOOSPERMIA:
            follow_up += ["Post-ejaculatory urinalysis (retrograde ejaculation)", "Genetic testing (karyotype, Y microdeletions, CFTR)"]
        if profile.leukocytes_millions_ml > 1:
            follow_up.append("Semen culture and antibiotic trial if positive")
        if profile.sperm_agglutination:
            follow_up.append("MAR test / sperm antibody testing")

        return FertilityResult(
            semen_quality=quality,
            total_sperm_count_millions=round(total_count, 2),
            total_motile_count_millions=round(motile_count, 2),
            who_2010_compliant=compliant,
            primary_infertility_factor=factor,
            hormonal_status=hormonal,
            recommendations=recs,
            follow_up_tests=follow_up,
            icsi_recommended=icsi,
            notes=notes
        )


def run():
    calc = FertilityCalculator()

    print("=" * 60)
    print("Male Fertility Assessment")
    print("=" * 60)

    profile = FertilityProfile(
        volume_ml=2.5, concentration_millions_ml=8, total_motility_percent=35,
        progressive_motility_percent=25, normal_morphology_percent=2,
        ph=7.2, leukocytes_millions_ml=0.5,
        fsh_miu_ml=8, testosterone_ng_dl=450, varicocele=True,
        abstinence_days=3, age=34
    )

    result = calc.calculate(profile)
    print(f"\nQuality: {result.semen_quality.value}")
    print(f"Total count: {result.total_sperm_count_millions} million")
    print(f"Motile count: {result.total_motile_count_millions} million")
    print(f"WHO compliant: {result.who_2010_compliant}")
    print(f"Primary factor: {result.primary_infertility_factor}")
    print(f"Hormonal status: {result.hormonal_status}")
    print(f"ICSI recommended: {result.icsi_recommended}")
    print(f"Recommendations: {result.recommendations}")
    print(f"Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
