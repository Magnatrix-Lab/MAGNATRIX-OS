"""Native stdlib module: Animal Reproduction Calculator
Calculates gestation periods, breeding calendars, and fertility windows.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class AnimalType(Enum):
    CATTLE = "cattle"
    HORSE = "horse"
    PIG = "pig"
    SHEEP = "sheep"
    GOAT = "goat"
    DOG = "dog"
    CAT = "cat"
    RABBIT = "rabbit"

@dataclass
class AnimalReproductionCalculator:
    animal_type: AnimalType
    last_breeding_date: str
    estrous_cycle_days: int = 21

    def gestation_days(self) -> int:
        periods = {AnimalType.CATTLE: 283, AnimalType.HORSE: 340, AnimalType.PIG: 114, AnimalType.SHEEP: 147, AnimalType.GOAT: 150, AnimalType.DOG: 63, AnimalType.CAT: 65, AnimalType.RABBIT: 31}
        return periods.get(self.animal_type, 150)

    def due_date(self) -> str:
        from datetime import datetime, timedelta
        try:
            start = datetime.strptime(self.last_breeding_date, "%Y-%m-%d")
            due = start + timedelta(days=self.gestation_days())
            return due.strftime("%Y-%m-%d")
        except ValueError:
            return "invalid_date"

    def days_pregnant(self, current_date: str) -> int:
        from datetime import datetime
        try:
            start = datetime.strptime(self.last_breeding_date, "%Y-%m-%d")
            current = datetime.strptime(current_date, "%Y-%m-%d")
            return (current - start).days
        except ValueError:
            return 0

    def fertility_window(self, estrous_start: str) -> tuple:
        from datetime import datetime, timedelta
        try:
            start = datetime.strptime(estrous_start, "%Y-%m-%d")
            end = start + timedelta(days=2)
            return (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        except ValueError:
            return ("invalid", "invalid")

    def next_estrous(self, last_estrous: str) -> str:
        from datetime import datetime, timedelta
        try:
            last = datetime.strptime(last_estrous, "%Y-%m-%d")
            next_estrous = last + timedelta(days=self.estrous_cycle_days)
            return next_estrous.strftime("%Y-%m-%d")
        except ValueError:
            return "invalid_date"

    def stats(self, current_date: str = "2024-06-05") -> Dict:
        return {
            "animal": self.animal_type.value,
            "gestation_days": self.gestation_days(),
            "due_date": self.due_date(),
            "days_pregnant": self.days_pregnant(current_date),
            "estrous_cycle_days": self.estrous_cycle_days,
        }

def run():
    arc = AnimalReproductionCalculator(animal_type=AnimalType.CATTLE, last_breeding_date="2024-03-15", estrous_cycle_days=21)
    print(arc.stats())

if __name__ == "__main__":
    run()
