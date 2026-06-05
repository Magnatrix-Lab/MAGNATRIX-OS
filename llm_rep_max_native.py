"""Native stdlib module: Rep Max Calculator
Estimates one-rep max and training loads from submaximal lifts.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class RepMaxCalculator:
    weight_lifted_kg: float
    reps_performed: int

    def epley_1rm(self) -> float:
        return self.weight_lifted_kg * (1 + self.reps_performed / 30)

    def brzycki_1rm(self) -> float:
        if self.reps_performed >= 37:
            return self.weight_lifted_kg
        return self.weight_lifted_kg / (1.0278 - 0.0278 * self.reps_performed)

    def lombardi_1rm(self) -> float:
        return self.weight_lifted_kg * (self.reps_performed ** 0.10)

    def training_load(self, percentage: float, formula: str = "epley") -> float:
        if formula == "epley":
            rm = self.epley_1rm()
        elif formula == "brzycki":
            rm = self.brzycki_1rm()
        else:
            rm = self.lombardi_1rm()
        return rm * (percentage / 100)

    def stats(self) -> Dict:
        return {
            "weight_lifted_kg": self.weight_lifted_kg,
            "reps": self.reps_performed,
            "epley_1rm": round(self.epley_1rm(), 1),
            "brzycki_1rm": round(self.brzycki_1rm(), 1),
            "lombardi_1rm": round(self.lombardi_1rm(), 1),
            "80pct_load_epley": round(self.training_load(80, "epley"), 1),
        }

def run():
    rm = RepMaxCalculator(weight_lifted_kg=100, reps_performed=5)
    print(rm.stats())

if __name__ == "__main__":
    run()
