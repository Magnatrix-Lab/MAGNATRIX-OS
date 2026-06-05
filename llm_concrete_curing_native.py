"""Native stdlib module: Concrete Curing Calculator
Calculates curing time, maturity, and strength development for concrete.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class TemperatureRecord:
    age_hours: float
    temperature_c: float

@dataclass
class ConcreteCuringCalculator:
    concrete_name: str
    datum_temperature_c: float = -10.0
    records: List[TemperatureRecord] = field(default_factory=list)
    reference_temp_c: float = 20.0

    def maturity_index(self) -> float:
        if not self.records:
            return 0.0
        total = 0.0
        for i in range(1, len(self.records)):
            dt = self.records[i].age_hours - self.records[i-1].age_hours
            avg_temp = (self.records[i].temperature_c + self.records[i-1].temperature_c) / 2
            total += (avg_temp - self.datum_temperature_c) * dt
        return total

    def equivalent_age_hr(self) -> float:
        if self.reference_temp_c == self.datum_temperature_c:
            return 0.0
        return self.maturity_index() / (self.reference_temp_c - self.datum_temperature_c)

    def estimated_strength_pct(self, base_strength_mpa: float = 30) -> float:
        maturity = self.maturity_index()
        if maturity < 100:
            return 10.0
        elif maturity < 300:
            return 30.0 + (maturity - 100) / 10
        elif maturity < 600:
            return 50.0 + (maturity - 300) / 15
        elif maturity < 1000:
            return 70.0 + (maturity - 600) / 20
        return 95.0

    def curing_time_days(self) -> float:
        if not self.records:
            return 0.0
        return self.records[-1].age_hours / 24

    def stats(self) -> Dict:
        return {
            "concrete": self.concrete_name,
            "maturity_index": round(self.maturity_index(), 1),
            "equivalent_age_hr": round(self.equivalent_age_hr(), 1),
            "estimated_strength_pct": round(self.estimated_strength_pct(), 1),
            "curing_time_days": round(self.curing_time_days(), 2),
        }

def run():
    ccc = ConcreteCuringCalculator(
        concrete_name="C30",
        datum_temperature_c=-10,
        records=[
            TemperatureRecord(0, 20),
            TemperatureRecord(12, 22),
            TemperatureRecord(24, 25),
            TemperatureRecord(48, 23),
            TemperatureRecord(72, 20),
        ]
    )
    print(ccc.stats())

if __name__ == "__main__":
    run()
