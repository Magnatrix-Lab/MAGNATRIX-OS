"""Native stdlib module: Color Vision Calculator
Interprets color vision test scores and calculates deficiency types.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ColorDeficiencyType(Enum):
    NORMAL = "normal"
    DEUTAN = "deutan"
    PROTAN = "protan"
    TRITAN = "tritan"
    ACHROMAT = "achromat"

@dataclass
class IshiharaPlateResult:
    plate_number: int
    correct_response: str
    patient_response: str

@dataclass
class ColorVisionCalculator:
    patient_name: str
    plate_results: List[IshiharaPlateResult] = field(default_factory=list)

    def errors(self) -> int:
        return sum(1 for p in self.plate_results if p.correct_response != p.patient_response)

    def error_rate_pct(self) -> float:
        if not self.plate_results:
            return 0.0
        return (self.errors() / len(self.plate_results)) * 100

    def classification(self) -> ColorDeficiencyType:
        if self.error_rate_pct() < 10:
            return ColorDeficiencyType.NORMAL
        elif self.error_rate_pct() < 30:
            return ColorDeficiencyType.DEUTAN
        elif self.error_rate_pct() < 60:
            return ColorDeficiencyType.PROTAN
        elif self.error_rate_pct() < 90:
            return ColorDeficiencyType.TRITAN
        return ColorDeficiencyType.ACHROMAT

    def severity(self) -> str:
        rate = self.error_rate_pct()
        if rate < 10:
            return "none"
        elif rate < 30:
            return "mild"
        elif rate < 60:
            return "moderate"
        return "severe"

    def plates_tested(self) -> int:
        return len(self.plate_results)

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "plates_tested": self.plates_tested(),
            "errors": self.errors(),
            "error_rate_pct": round(self.error_rate_pct(), 1),
            "classification": self.classification().value,
            "severity": self.severity(),
        }

def run():
    cvc = ColorVisionCalculator(
        patient_name="John",
        plate_results=[
            IshiharaPlateResult(1, "12", "12"),
            IshiharaPlateResult(2, "8", "8"),
            IshiharaPlateResult(3, "6", "5"),
            IshiharaPlateResult(4, "29", "70"),
            IshiharaPlateResult(5, "57", "57"),
            IshiharaPlateResult(6, "5", "2"),
            IshiharaPlateResult(7, "3", "3"),
            IshiharaPlateResult(8, "15", "15"),
            IshiharaPlateResult(9, "74", "21"),
            IshiharaPlateResult(10, "2", "2"),
        ]
    )
    print(cvc.stats())

if __name__ == "__main__":
    run()
