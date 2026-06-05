"""Dental Chart — tooth numbering, conditions, treatment plan, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

@dataclass
class Tooth:
    number: int
    surface: str
    condition: str
    treatment: str = ""

class DentalChart:
    def __init__(self):
        self.teeth: Dict[int, List[Tooth]] = {}

    def add_tooth(self, t: Tooth):
        self.teeth.setdefault(t.number, []).append(t)

    def teeth_with_condition(self, condition: str) -> List[int]:
        return [num for num, teeth in self.teeth.items() if any(t.condition == condition for t in teeth)]

    def treatment_plan(self) -> List[str]:
        plan = []
        for num, teeth in self.teeth.items():
            for t in teeth:
                if t.treatment:
                    plan.append(f"Tooth {num} ({t.surface}): {t.treatment}")
        return plan

    def dmft_score(self) -> int:
        decayed = len(self.teeth_with_condition("decay"))
        missing = len(self.teeth_with_condition("missing"))
        filled = len(self.teeth_with_condition("filled"))
        return decayed + missing + filled

    def risk_assessment(self) -> str:
        decay_count = len(self.teeth_with_condition("decay"))
        if decay_count >= 5: return "high"
        elif decay_count >= 2: return "moderate"
        return "low"

    def stats(self) -> Dict:
        return {"charted_teeth": len(self.teeth), "dmft": self.dmft_score(), "risk": self.risk_assessment()}

def run():
    dc = DentalChart()
    dc.add_tooth(Tooth(16, "occlusal", "decay", "filling"))
    dc.add_tooth(Tooth(36, "mesial", "decay", "filling"))
    dc.add_tooth(Tooth(11, "labial", "intact", ""))
    dc.add_tooth(Tooth(46, "distal", "missing", "implant"))
    print(dc.stats())
    print("Treatment plan:", dc.treatment_plan())

if __name__ == "__main__":
    run()
