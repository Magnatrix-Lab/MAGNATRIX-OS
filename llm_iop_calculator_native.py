"""Native stdlib module: IOP Calculator
Calculates intraocular pressure, corrected values, and glaucoma risk.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class CornealThicknessCategory(Enum):
    THIN = "thin"
    AVERAGE = "average"
    THICK = "thick"

@dataclass
class IOPCalculator:
    measured_iop_mmhg: float
    central_corneal_thickness_um: float
    age: int
    family_history_glaucoma: bool = False

    def cct_category(self) -> CornealThicknessCategory:
        if self.central_corneal_thickness_um < 520:
            return CornealThicknessCategory.THIN
        elif self.central_corneal_thickness_um > 580:
            return CornealThicknessCategory.THICK
        return CornealThicknessCategory.AVERAGE

    def corrected_iop_mmhg(self) -> float:
        cct = self.central_corneal_thickness_um
        diff = cct - 550
        return self.measured_iop_mmhg - (diff / 25) * 1.5

    def glaucoma_risk_score(self) -> int:
        score = 0
        if self.corrected_iop_mmhg() > 21:
            score += 2
        elif self.corrected_iop_mmhg() > 18:
            score += 1
        if self.age > 60:
            score += 1
        if self.age > 80:
            score += 1
        if self.family_history_glaucoma:
            score += 2
        if self.cct_category() == CornealThicknessCategory.THIN:
            score += 1
        return score

    def risk_level(self) -> str:
        score = self.glaucoma_risk_score()
        if score <= 1:
            return "low"
        elif score <= 3:
            return "moderate"
        return "high"

    def recommended_followup_months(self) -> int:
        level = self.risk_level()
        if level == "low":
            return 24
        elif level == "moderate":
            return 12
        return 6

    def stats(self) -> Dict:
        return {
            "measured_iop_mmhg": self.measured_iop_mmhg,
            "corrected_iop_mmhg": round(self.corrected_iop_mmhg(), 1),
            "cct_um": self.central_corneal_thickness_um,
            "cct_category": self.cct_category().value,
            "risk_score": self.glaucoma_risk_score(),
            "risk_level": self.risk_level(),
            "followup_months": self.recommended_followup_months(),
        }

def run():
    iop = IOPCalculator(measured_iop_mmhg=24, central_corneal_thickness_um=490, age=65, family_history_glaucoma=True)
    print(iop.stats())

if __name__ == "__main__":
    run()
