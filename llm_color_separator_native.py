"""Native stdlib module: Color Separator
Calculates CMYK color separations and ink coverage for print jobs.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class InkCoverage:
    cyan_pct: float
    magenta_pct: float
    yellow_pct: float
    black_pct: float

@dataclass
class ColorSeparator:
    job_name: str
    page_count: int
    coverage_per_page: InkCoverage = field(default_factory=lambda: InkCoverage(30, 25, 20, 40))
    ink_cost_per_pct: float = 0.05

    def total_ink_units(self) -> Dict[str, float]:
        return {
            "cyan": self.page_count * self.coverage_per_page.cyan_pct,
            "magenta": self.page_count * self.coverage_per_page.magenta_pct,
            "yellow": self.page_count * self.coverage_per_page.yellow_pct,
            "black": self.page_count * self.coverage_per_page.black_pct,
        }

    def ink_cost(self) -> float:
        units = self.total_ink_units()
        return sum(units.values()) * self.ink_cost_per_pct

    def total_coverage_pct(self) -> float:
        c = self.coverage_per_page
        return c.cyan_pct + c.magenta_pct + c.yellow_pct + c.black_pct

    def stats(self) -> Dict:
        return {
            "job": self.job_name,
            "pages": self.page_count,
            "total_ink_units": {k: round(v, 1) for k, v in self.total_ink_units().items()},
            "ink_cost": round(self.ink_cost(), 2),
            "total_coverage_pct": round(self.total_coverage_pct(), 1),
        }

def run():
    cs = ColorSeparator(job_name="Brochure", page_count=5000, coverage_per_page=InkCoverage(35, 30, 25, 45))
    print(cs.stats())

if __name__ == "__main__":
    run()
