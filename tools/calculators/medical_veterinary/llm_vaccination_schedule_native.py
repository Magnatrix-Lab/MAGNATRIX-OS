"""Native stdlib module: Vaccination Schedule Calculator
Manages animal vaccination schedules and intervals.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class VaccineDose:
    vaccine_name: str
    dose_number: int
    age_weeks: float
    booster_interval_months: int

@dataclass
class VaccinationScheduleCalculator:
    animal_name: str
    species: str
    birth_date: str
    doses: List[VaccineDose] = field(default_factory=list)

    def completed_doses(self, current_weeks: float) -> List[VaccineDose]:
        return [d for d in self.doses if d.age_weeks <= current_weeks]

    def upcoming_doses(self, current_weeks: float) -> List[VaccineDose]:
        return [d for d in self.doses if d.age_weeks > current_weeks]

    def next_dose(self, current_weeks: float) -> str:
        upcoming = self.upcoming_doses(current_weeks)
        if not upcoming:
            return "all_complete"
        return upcoming[0].vaccine_name

    def overdue_doses(self, current_weeks: float) -> List[VaccineDose]:
        completed = self.completed_doses(current_weeks)
        return [d for d in self.doses if d not in completed]

    def stats(self, current_weeks: float = 12) -> Dict:
        return {
            "animal": self.animal_name,
            "species": self.species,
            "total_doses": len(self.doses),
            "completed": len(self.completed_doses(current_weeks)),
            "upcoming": len(self.upcoming_doses(current_weeks)),
            "next_dose": self.next_dose(current_weeks),
        }

def run():
    vsc = VaccinationScheduleCalculator(
        animal_name="Max",
        species="dog",
        birth_date="2024-03-01",
        doses=[
            VaccineDose("Distemper", 1, 6, 12),
            VaccineDose("Distemper", 2, 10, 12),
            VaccineDose("Parvovirus", 1, 6, 12),
            VaccineDose("Parvovirus", 2, 10, 12),
            VaccineDose("Rabies", 1, 16, 36),
        ]
    )
    print(vsc.stats(current_weeks=14))

if __name__ == "__main__":
    run()
