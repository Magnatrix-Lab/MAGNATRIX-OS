"""Native stdlib module: Contrast Media Calculator
Calculates contrast dose, injection rate, and timing for imaging studies.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ContrastType(Enum):
    IODINATED = "iodinated"
    GADOLINIUM = "gadolinium"
    BARIUM = "barium"
    ULTRASOUND = "ultrasound_microbubble"

class ExamType(Enum):
    CT = "ct"
    MRI = "mri"
    XRAY = "xray"
    ULTRASOUND = "ultrasound"

@dataclass
class ContrastMediaCalculator:
    contrast_type: ContrastType
    exam_type: ExamType
    patient_weight_kg: float
    concentration_mg_ml: float
    injection_duration_sec: float

    def standard_dose_ml_kg(self) -> float:
        doses = {
            (ContrastType.IODINATED, ExamType.CT): 1.5,
            (ContrastType.GADOLINIUM, ExamType.MRI): 0.2,
            (ContrastType.BARIUM, ExamType.XRAY): 1.0,
            (ContrastType.ULTRASOUND, ExamType.ULTRASOUND): 0.05,
        }
        return doses.get((self.contrast_type, self.exam_type), 1.0)

    def total_volume_ml(self) -> float:
        return self.standard_dose_ml_kg() * self.patient_weight_kg

    def total_iodine_g(self) -> float:
        if self.contrast_type != ContrastType.IODINATED:
            return 0.0
        return (self.total_volume_ml() * self.concentration_mg_ml) / 1000

    def injection_rate_ml_sec(self) -> float:
        if self.injection_duration_sec == 0:
            return 0.0
        return self.total_volume_ml() / self.injection_duration_sec

    def injection_rate_ml_sec_power(self) -> float:
        weight_power = self.patient_weight_kg ** 0.75
        if weight_power == 0:
            return 0.0
        return (self.total_volume_ml() / self.injection_duration_sec) / weight_power

    def stats(self) -> Dict:
        return {
            "contrast": self.contrast_type.value,
            "exam": self.exam_type.value,
            "weight_kg": self.patient_weight_kg,
            "dose_ml_kg": self.standard_dose_ml_kg(),
            "total_volume_ml": round(self.total_volume_ml(), 1),
            "total_iodine_g": round(self.total_iodine_g(), 2) if self.contrast_type == ContrastType.IODINATED else None,
            "injection_rate_ml_sec": round(self.injection_rate_ml_sec(), 2),
            "injection_duration_sec": self.injection_duration_sec,
        }

def run():
    cmc = ContrastMediaCalculator(contrast_type=ContrastType.IODINATED, exam_type=ExamType.CT, patient_weight_kg=70, concentration_mg_ml=350, injection_duration_sec=30)
    print(cmc.stats())

if __name__ == "__main__":
    run()
