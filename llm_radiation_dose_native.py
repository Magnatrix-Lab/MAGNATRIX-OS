"""Native stdlib module: Radiation Dose Calculator
Calculates effective dose, organ dose, and exposure metrics for radiology.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ExamType(Enum):
    CHEST_XRAY = "chest_xray"
    CT_HEAD = "ct_head"
    CT_ABDOMEN = "ct_abdomen"
    MAMMOGRAPHY = "mammography"
    DEXA = "dexa"
    PET_CT = "pet_ct"
    FLUOROSCOPY = "fluoroscopy"

@dataclass
class RadiationDoseCalculator:
    exam_type: ExamType
    num_exposures: int
    patient_age: int
    patient_weight_kg: float

    def _base_dose_msv(self) -> float:
        doses = {
            ExamType.CHEST_XRAY: 0.1,
            ExamType.CT_HEAD: 2.0,
            ExamType.CT_ABDOMEN: 8.0,
            ExamType.MAMMOGRAPHY: 0.4,
            ExamType.DEXA: 0.001,
            ExamType.PET_CT: 14.0,
            ExamType.FLUOROSCOPY: 3.0,
        }
        return doses.get(self.exam_type, 1.0)

    def effective_dose_msv(self) -> float:
        return self._base_dose_msv() * self.num_exposures

    def age_factor(self) -> float:
        if self.patient_age < 10:
            return 3.0
        elif self.patient_age < 18:
            return 1.5
        elif self.patient_age < 40:
            return 1.0
        elif self.patient_age < 60:
            return 0.8
        return 0.6

    def risk_weighted_dose(self) -> float:
        return self.effective_dose_msv() * self.age_factor()

    def equivalent_chest_xrays(self) -> float:
        if self.effective_dose_msv() == 0:
            return 0.0
        return self.effective_dose_msv() / 0.1

    def cancer_risk_increase_pct(self) -> float:
        return self.effective_dose_msv() * 0.005

    def stats(self) -> Dict:
        return {
            "exam": self.exam_type.value,
            "exposures": self.num_exposures,
            "effective_dose_msv": round(self.effective_dose_msv(), 3),
            "age_factor": self.age_factor(),
            "risk_weighted_dose": round(self.risk_weighted_dose(), 3),
            "equivalent_chest_xrays": round(self.equivalent_chest_xrays(), 1),
            "cancer_risk_increase_pct": round(self.cancer_risk_increase_pct(), 6),
        }

def run():
    rdc = RadiationDoseCalculator(exam_type=ExamType.CT_ABDOMEN, num_exposures=1, patient_age=35, patient_weight_kg=70)
    print(rdc.stats())

if __name__ == "__main__":
    run()
