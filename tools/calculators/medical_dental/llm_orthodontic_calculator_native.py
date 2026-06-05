"""Native stdlib module: Orthodontic Calculator
Calculates orthodontic treatment metrics: space analysis, Bolton ratios, and overjet.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ToothMeasurement:
    tooth_name: str
    mesiodistal_width_mm: float
    arch: str = "upper"

@dataclass
class OrthodonticCalculator:
    patient_name: str
    teeth: List[ToothMeasurement] = field(default_factory=list)
    arch_length_mm: float = 0.0

    def upper_total_mm(self) -> float:
        return sum(t.mesiodistal_width_mm for t in self.teeth if t.arch == "upper")

    def lower_total_mm(self) -> float:
        return sum(t.mesiodistal_width_mm for t in self.teeth if t.arch == "lower")

    def bolton_ratio(self) -> float:
        upper = self.upper_total_mm()
        lower = self.lower_total_mm()
        if lower == 0:
            return 0.0
        return (upper / lower) * 100

    def crowding_mm(self) -> float:
        if self.arch_length_mm == 0:
            return 0.0
        return self.upper_total_mm() - self.arch_length_mm

    def spacing_mm(self) -> float:
        c = self.crowding_mm()
        return abs(c) if c < 0 else 0.0

    def bolton_assessment(self) -> str:
        ratio = self.bolton_ratio()
        if 91.3 <= ratio <= 91.5:
            return "ideal"
        elif ratio < 91.3:
            return "maxillary_excess"
        return "mandibular_excess"

    def teeth_count(self) -> int:
        return len(self.teeth)

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "upper_total_mm": round(self.upper_total_mm(), 1),
            "lower_total_mm": round(self.lower_total_mm(), 1),
            "bolton_ratio": round(self.bolton_ratio(), 2),
            "bolton_assessment": self.bolton_assessment(),
            "crowding_mm": round(self.crowding_mm(), 1),
            "spacing_mm": round(self.spacing_mm(), 1),
        }

def run():
    oc = OrthodonticCalculator(
        patient_name="Jane",
        arch_length_mm=45,
        teeth=[
            ToothMeasurement("11", 8.5, "upper"),
            ToothMeasurement("12", 6.5, "upper"),
            ToothMeasurement("13", 7.5, "upper"),
            ToothMeasurement("14", 7.0, "upper"),
            ToothMeasurement("15", 7.0, "upper"),
            ToothMeasurement("21", 8.5, "lower"),
            ToothMeasurement("22", 6.5, "lower"),
            ToothMeasurement("23", 7.5, "lower"),
            ToothMeasurement("24", 7.0, "lower"),
            ToothMeasurement("25", 7.0, "lower"),
        ]
    )
    print(oc.stats())

if __name__ == "__main__":
    run()
