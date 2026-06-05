"""Rehab Assessor -- FIM, Barthel, MMT, progress, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class RehabAssessor:
    fim_scores: Dict[str, int] = field(default_factory=dict)

    def fim_total(self) -> int:
        return sum(self.fim_scores.values())

    def fim_level(self) -> str:
        total = self.fim_total()
        if total >= 108: return "independent"
        elif total >= 80: return "modified independence"
        elif total >= 54: return "supervision"
        elif total >= 36: return "assistance"
        return "total assistance"

    def barthel_index(self, items: Dict[str, int]) -> int:
        return sum(items.values())

    def barthel_level(self, score: int) -> str:
        if score >= 100: return "independent"
        elif score >= 60: return "mild dependence"
        elif score >= 40: return "moderate dependence"
        elif score >= 20: return "severe dependence"
        return "total dependence"

    def mmt_grade(self, muscle: str, force_pct: float) -> int:
        if force_pct >= 100: return 5
        elif force_pct >= 75: return 4
        elif force_pct >= 50: return 3
        elif force_pct >= 25: return 2
        elif force_pct > 0: return 1
        return 0

    def progress_rate(self, scores: List[int]) -> float:
        if len(scores) < 2:
            return 0.0
        return (scores[-1] - scores[0]) / len(scores)

    def stats(self) -> Dict:
        return {"fim_total": self.fim_total(), "fim_level": self.fim_level(), "fim_items": len(self.fim_scores)}

def run():
    ra = RehabAssessor({"self-care": 6, "sphincter": 6, "mobility": 5, "locomotion": 5, "communication": 7, "social": 7})
    print(ra.stats())
    print("MMT 75%:", ra.mmt_grade("biceps", 75))
    print("Progress:", ra.progress_rate([40, 50, 60, 70]))

if __name__ == "__main__":
    run()
