"""Native stdlib module: Mortality Table Calculator
Calculates life expectancy and survival probabilities from mortality rates.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class MortalityRate:
    age: int
    qx: float
    lx: float

@dataclass
class MortalityTableCalculator:
    table_name: str
    rates: List[MortalityRate] = field(default_factory=list)

    def life_expectancy(self, age: int) -> float:
        rates = sorted(self.rates, key=lambda r: r.age)
        for i, r in enumerate(rates):
            if r.age == age:
                remaining = rates[i:]
                if not remaining:
                    return 0.0
                total_lx = sum(r.lx for r in remaining)
                return total_lx / max(1, r.lx)
        return 0.0

    def survival_probability(self, from_age: int, to_age: int) -> float:
        rates = sorted(self.rates, key=lambda r: r.age)
        from_rate = None
        to_rate = None
        for r in rates:
            if r.age == from_age:
                from_rate = r
            if r.age == to_age:
                to_rate = r
        if from_rate and to_rate and from_rate.lx > 0:
            return to_rate.lx / from_rate.lx
        return 0.0

    def death_probability(self, age: int) -> float:
        for r in self.rates:
            if r.age == age:
                return r.qx
        return 0.0

    def stats(self, age: int = 30) -> Dict:
        return {
            "table": self.table_name,
            "age": age,
            "life_expectancy": round(self.life_expectancy(age), 2),
            "death_prob": round(self.death_probability(age), 6),
            "survival_20yr": round(self.survival_probability(age, age + 20), 4),
        }

def run():
    mtc = MortalityTableCalculator(
        table_name="Standard Life",
        rates=[
            MortalityRate(30, 0.001, 100000),
            MortalityRate(40, 0.002, 99900),
            MortalityRate(50, 0.005, 99700),
            MortalityRate(60, 0.012, 99200),
            MortalityRate(70, 0.030, 98000),
            MortalityRate(80, 0.080, 95000),
        ]
    )
    print(mtc.stats(age=40))

if __name__ == "__main__":
    run()
