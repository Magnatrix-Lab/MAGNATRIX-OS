"""Shift Optimizer — staffing, workload, fatigue, coverage, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Nurse:
    id: str
    skills: Set[str]
    max_hours: float = 12.0
    hours_worked: float = 0.0

class ShiftOptimizer:
    def __init__(self):
        self.nurses: List[Nurse] = []
        self.patient_load: int = 20
        self.required_ratio: float = 1.0 / 5.0

    def add_nurse(self, n: Nurse):
        self.nurses.append(n)

    def required_nurses(self) -> int:
        return int(self.patient_load * self.required_ratio) + 1

    def available_nurses(self, skill: str = None) -> List[Nurse]:
        if skill:
            return [n for n in self.nurses if skill in n.skills and n.hours_worked < n.max_hours]
        return [n for n in self.nurses if n.hours_worked < n.max_hours]

    def understaffed(self, skill: str = None) -> bool:
        available = len(self.available_nurses(skill))
        required = self.required_nurses()
        return available < required

    def workload_index(self) -> float:
        available = len(self.available_nurses())
        if available == 0:
            return float('inf')
        return self.patient_load / available

    def fatigue_risk(self, avg_hours: float = None) -> str:
        avg = avg_hours or sum(n.hours_worked for n in self.nurses) / len(self.nurses) if self.nurses else 0
        if avg > 10: return "high"
        elif avg > 8: return "moderate"
        return "low"

    def shift_recommendation(self) -> Dict:
        return {
            "required": self.required_nurses(),
            "available": len(self.available_nurses()),
            "understaffed": self.understaffed(),
            "workload_index": round(self.workload_index(), 2)
        }

    def stats(self) -> Dict:
        return self.shift_recommendation()

def run():
    so = ShiftOptimizer()
    so.patient_load = 30
    so.add_nurse(Nurse("N1", {"ICU", "meds"}, 12, 0))
    so.add_nurse(Nurse("N2", {"meds"}, 12, 8))
    so.add_nurse(Nurse("N3", {"ICU"}, 12, 2))
    so.add_nurse(Nurse("N4", {"meds", "pediatric"}, 12, 4))
    print(so.stats())
    print("Fatigue:", so.fatigue_risk())

if __name__ == "__main__":
    run()
