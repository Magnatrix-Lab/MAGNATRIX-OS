"""Native stdlib module: Dental Age Estimator
Estimates age from dental eruption and development stages.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ToothDevelopment:
    tooth_name: str
    stage: str
    estimated_age_months: float

@dataclass
class DentalAgeEstimator:
    patient_name: str
    teeth: List[ToothDevelopment] = field(default_factory=list)

    def avg_estimated_age_months(self) -> float:
        if not self.teeth:
            return 0.0
        return sum(t.estimated_age_months for t in self.teeth) / len(self.teeth)

    def estimated_age_years(self) -> float:
        return self.avg_estimated_age_months() / 12

    def min_estimated_age_months(self) -> float:
        if not self.teeth:
            return 0.0
        return min(t.estimated_age_months for t in self.teeth)

    def max_estimated_age_months(self) -> float:
        if not self.teeth:
            return 0.0
        return max(t.estimated_age_months for t in self.teeth)

    def age_range_years(self) -> tuple:
        return (round(self.min_estimated_age_months() / 12, 1), round(self.max_estimated_age_months() / 12, 1))

    def erupted_teeth_count(self) -> int:
        return sum(1 for t in self.teeth if t.stage in ["erupted", "complete"])

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "teeth_assessed": len(self.teeth),
            "erupted_teeth": self.erupted_teeth_count(),
            "estimated_age_years": round(self.estimated_age_years(), 1),
            "age_range_years": self.age_range_years(),
        }

def run():
    dae = DentalAgeEstimator(
        patient_name="Child-A",
        teeth=[
            ToothDevelopment("central_incisor", "erupted", 8),
            ToothDevelopment("lateral_incisor", "erupted", 10),
            ToothDevelopment("first_molar", "erupted", 16),
            ToothDevelopment("canine", "erupting", 20),
            ToothDevelopment("second_molar", "developing", 28),
        ]
    )
    print(dae.stats())

if __name__ == "__main__":
    run()
