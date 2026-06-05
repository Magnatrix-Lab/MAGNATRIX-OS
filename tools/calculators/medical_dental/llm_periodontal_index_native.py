"""Native stdlib module: Periodontal Index Calculator
Calculates periodontal indices: CPI, PBI, and plaque scores.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class SextantScore:
    sextant: int
    pocket_depth_mm: float
    bleeding_sites: int
    total_sites: int
    calculus_present: bool

@dataclass
class PeriodontalIndexCalculator:
    patient_name: str
    sextants: List[SextantScore] = field(default_factory=list)

    def cpi_score(self) -> int:
        if not self.sextants:
            return 0
        scores = []
        for s in self.sextants:
            if s.pocket_depth_mm >= 6:
                scores.append(4)
            elif s.pocket_depth_mm >= 4:
                scores.append(3)
            elif s.calculus_present:
                scores.append(2)
            elif s.bleeding_sites > 0:
                scores.append(1)
            else:
                scores.append(0)
        return max(scores)

    def pbi_pct(self) -> float:
        total_sites = sum(s.total_sites for s in self.sextants)
        if total_sites == 0:
            return 0.0
        bleeding = sum(s.bleeding_sites for s in self.sextants)
        return (bleeding / total_sites) * 100

    def avg_pocket_depth_mm(self) -> float:
        if not self.sextants:
            return 0.0
        return sum(s.pocket_depth_mm for s in self.sextants) / len(self.sextants)

    def periodontal_status(self) -> str:
        cpi = self.cpi_score()
        if cpi == 0:
            return "healthy"
        elif cpi == 1:
            return "gingivitis"
        elif cpi == 2:
            return "calculus"
        elif cpi == 3:
            return "shallow_pockets"
        return "deep_pockets"

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "cpi_score": self.cpi_score(),
            "pbi_pct": round(self.pbi_pct(), 1),
            "avg_pocket_depth_mm": round(self.avg_pocket_depth_mm(), 1),
            "status": self.periodontal_status(),
        }

def run():
    pic = PeriodontalIndexCalculator(
        patient_name="Bob",
        sextants=[
            SextantScore(1, 2.5, 1, 6, True),
            SextantScore(2, 3.0, 2, 6, True),
            SextantScore(3, 4.5, 2, 6, True),
            SextantScore(4, 2.0, 0, 6, False),
            SextantScore(5, 3.5, 1, 6, True),
            SextantScore(6, 2.5, 0, 6, True),
        ]
    )
    print(pic.stats())

if __name__ == "__main__":
    run()
