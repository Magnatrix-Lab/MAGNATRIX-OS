"""Native stdlib module: Depreciation Calculator
Computes straight-line and declining balance depreciation schedules.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class DepreciationMethod(Enum):
    STRAIGHT_LINE = "straight_line"
    DECLINING_BALANCE = "declining_balance"
    SUM_OF_YEARS = "sum_of_years"

@dataclass
class DepreciationCalculator:
    asset_name: str
    cost: float
    salvage_value: float
    useful_life_years: int
    method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE

    def annual_depreciation(self) -> float:
        if self.method == DepreciationMethod.STRAIGHT_LINE:
            return max(0, (self.cost - self.salvage_value) / max(1, self.useful_life_years))
        elif self.method == DepreciationMethod.DECLINING_BALANCE:
            rate = 2 / max(1, self.useful_life_years)
            return self.cost * rate
        else:
            total_years = sum(range(1, self.useful_life_years + 1))
            return max(0, (self.cost - self.salvage_value) * self.useful_life_years / total_years)

    def book_value_end_year(self, year: int) -> float:
        if self.method == DepreciationMethod.STRAIGHT_LINE:
            return max(self.salvage_value, self.cost - (self.annual_depreciation() * year))
        elif self.method == DepreciationMethod.DECLINING_BALANCE:
            rate = 2 / max(1, self.useful_life_years)
            return max(self.salvage_value, self.cost * ((1 - rate) ** year))
        else:
            total = sum(range(1, self.useful_life_years + 1))
            depreciated = 0.0
            for y in range(1, year + 1):
                depreciated += (self.cost - self.salvage_value) * (self.useful_life_years - y + 1) / total
            return max(self.salvage_value, self.cost - depreciated)

    def full_schedule(self) -> List[Dict]:
        schedule = []
        for y in range(1, self.useful_life_years + 1):
            schedule.append({
                "year": y,
                "book_value": round(self.book_value_end_year(y), 2),
            })
        return schedule

    def stats(self) -> Dict:
        return {
            "asset": self.asset_name,
            "annual_depreciation": round(self.annual_depreciation(), 2),
            "method": self.method.value,
            "useful_life": self.useful_life_years,
        }

def run():
    dc = DepreciationCalculator(asset_name="Server Rack", cost=50000, salvage_value=5000, useful_life_years=5, method=DepreciationMethod.STRAIGHT_LINE)
    print(dc.stats())
    print(dc.full_schedule())

if __name__ == "__main__":
    run()
