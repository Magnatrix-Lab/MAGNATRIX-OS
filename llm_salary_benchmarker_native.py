"""Native stdlib module: Salary Benchmarker
Benchmarks salary ranges against market data by role, location, and experience.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class SalaryDataPoint:
    role: str
    location: str
    years_exp: int
    salary_usd: float

@dataclass
class SalaryBenchmarker:
    target_role: str
    target_location: str
    target_years: int
    market_data: List[SalaryDataPoint] = field(default_factory=list)

    def matching_data(self) -> List[SalaryDataPoint]:
        return [d for d in self.market_data if d.role == self.target_role and d.location == self.target_location]

    def percentile(self, offered_salary: float) -> float:
        matches = sorted([d.salary_usd for d in self.matching_data()])
        if not matches:
            return 0.0
        below = sum(1 for s in matches if s < offered_salary)
        return (below / len(matches)) * 100

    def range_usd(self) -> Dict[str, float]:
        matches = [d.salary_usd for d in self.matching_data()]
        if not matches:
            return {"min": 0, "max": 0, "median": 0}
        matches.sort()
        mid = len(matches) // 2
        median = matches[mid] if len(matches) % 2 == 1 else (matches[mid - 1] + matches[mid]) / 2
        return {
            "min": matches[0],
            "max": matches[-1],
            "median": median,
        }

    def stats(self, offered_salary: float = 0) -> Dict:
        r = self.range_usd()
        return {
            "role": self.target_role,
            "location": self.target_location,
            "range": r,
            "data_points": len(self.matching_data()),
            "percentile": round(self.percentile(offered_salary), 1) if offered_salary else None,
        }

def run():
    sb = SalaryBenchmarker(
        target_role="Software Engineer",
        target_location="San Francisco",
        target_years=5,
        market_data=[
            SalaryDataPoint("Software Engineer", "San Francisco", 5, 160000),
            SalaryDataPoint("Software Engineer", "San Francisco", 5, 175000),
            SalaryDataPoint("Software Engineer", "San Francisco", 5, 155000),
            SalaryDataPoint("Software Engineer", "San Francisco", 5, 190000),
            SalaryDataPoint("Software Engineer", "New York", 5, 140000),
        ]
    )
    print(sb.stats(offered_salary=170000))

if __name__ == "__main__":
    run()
