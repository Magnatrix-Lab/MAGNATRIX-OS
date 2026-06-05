"""Native stdlib module: Drug Test Calculator
Estimates drug detection windows, cutoff levels, and confidence.
"""
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

class DrugType(Enum):
    THC = "THC (Cannabis)"
    COCAINE = "Cocaine"
    OPIATES = "Opiates"
    AMPHETAMINE = "Amphetamine"
    METHAMPHETAMINE = "Methamphetamine"
    BENZODIAZEPINE = "Benzodiazepine"
    BARBITURATE = "Barbiturate"
    PCP = "PCP"

@dataclass
class DrugTestCalculator:
    drug: DrugType
    test_type: str  # urine, blood, saliva, hair
    half_life_hours: float
    dose_mg: float = 100.0
    body_weight_kg: float = 70.0
    hydration_level: str = "normal"  # low, normal, high
    metabolic_rate: str = "normal"  # slow, normal, fast
    frequency: str = "occasional"  # single, occasional, chronic

    _DETECTION_WINDOWS = {
        "THC (Cannabis)": {"urine": (3, 30), "blood": (1, 7), "saliva": (1, 3), "hair": (90, 365)},
        "Cocaine": {"urine": (2, 4), "blood": (1, 2), "saliva": (1, 2), "hair": (90, 365)},
        "Opiates": {"urine": (2, 4), "blood": (0.5, 2), "saliva": (1, 4), "hair": (90, 365)},
        "Amphetamine": {"urine": (2, 4), "blood": (1, 2), "saliva": (1, 3), "hair": (90, 365)},
        "Methamphetamine": {"urine": (3, 6), "blood": (1, 3), "saliva": (1, 4), "hair": (90, 365)},
        "Benzodiazepine": {"urine": (3, 6), "blood": (1, 3), "saliva": (1, 10), "hair": (90, 365)},
        "Barbiturate": {"urine": (2, 4), "blood": (1, 2), "saliva": (1, 3), "hair": (90, 365)},
        "PCP": {"urine": (7, 14), "blood": (1, 3), "saliva": (1, 3), "hair": (90, 365)},
    }

    _CUTOFFS_NG_ML = {
        "THC (Cannabis)": 50,
        "Cocaine": 150,
        "Opiates": 2000,
        "Amphetamine": 1000,
        "Methamphetamine": 1000,
        "Benzodiazepine": 200,
        "Barbiturate": 200,
        "PCP": 25,
    }

    def detection_window_days(self) -> tuple:
        base = self._DETECTION_WINDOWS.get(self.drug.value, {}).get(self.test_type, (1, 3))
        freq_multiplier = {"single": 0.5, "occasional": 1.0, "chronic": 2.0}
        meta_multiplier = {"slow": 1.5, "normal": 1.0, "fast": 0.7}
        mult = freq_multiplier.get(self.frequency, 1.0) * meta_multiplier.get(self.metabolic_rate, 1.0)
        return (round(base[0] * mult, 1), round(base[1] * mult, 1))

    def cutoff_ng_ml(self) -> int:
        return self._CUTOFFS_NG_ML.get(self.drug.value, 50)

    def estimated_clearance_hours(self) -> float:
        half_lives_needed = 5.0
        if self.frequency == "chronic":
            half_lives_needed = 7.0
        elif self.frequency == "single":
            half_lives_needed = 3.5
        return self.half_life_hours * half_lives_needed

    def confidence_pass_after_hours(self, hours_since_last_use: float) -> float:
        clearance = self.estimated_clearance_hours()
        if hours_since_last_use >= clearance * 1.5:
            return 95.0
        elif hours_since_last_use >= clearance:
            return 75.0
        elif hours_since_last_use >= clearance * 0.5:
            return 40.0
        return 10.0

    def stats(self, hours_since_last_use: Optional[float] = None) -> Dict:
        window = self.detection_window_days()
        result = {
            "drug": self.drug.value,
            "test_type": self.test_type,
            "cutoff_ng_ml": self.cutoff_ng_ml(),
            "detection_window_days": window,
            "estimated_clearance_hours": round(self.estimated_clearance_hours(), 1),
        }
        if hours_since_last_use is not None:
            result["confidence_pass_pct"] = round(self.confidence_pass_after_hours(hours_since_last_use), 1)
        return result

def run():
    dtc = DrugTestCalculator(
        drug=DrugType.THC,
        test_type="urine",
        half_life_hours=20,
        frequency="occasional",
        metabolic_rate="normal",
    )
    print(dtc.stats(hours_since_last_use=72))

if __name__ == "__main__":
    run()
