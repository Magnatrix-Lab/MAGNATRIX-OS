"""Native stdlib module: Berg Balance Calculator
Calculates Berg Balance Scale scores and fall risk categories.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ItemRating(Enum):
    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4

@dataclass
class BergItem:
    item_name: str
    rating: ItemRating

@dataclass
class BergBalanceCalculator:
    patient_name: str
    items: List[BergItem] = field(default_factory=list)

    def total_score(self) -> int:
        return sum(i.rating.value for i in self.items)

    def max_score(self) -> int:
        return len(self.items) * 4

    def score_pct(self) -> float:
        if self.max_score() == 0:
            return 0.0
        return (self.total_score() / self.max_score()) * 100

    def fall_risk(self) -> str:
        score = self.total_score()
        if score >= 45:
            return "low_fall_risk"
        elif score >= 36:
            return "medium_fall_risk"
        elif score >= 21:
            return "high_fall_risk"
        return "very_high_fall_risk"

    def recommended_aid(self) -> str:
        score = self.total_score()
        if score >= 45:
            return "independent"
        elif score >= 36:
            return "cane_or_walker_as_needed"
        elif score >= 21:
            return "walker_required"
        return "wheelchair_or_maximal_assist"

    def items_at_risk(self) -> List[str]:
        return [i.item_name for i in self.items if i.rating.value < 2]

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "items_tested": len(self.items),
            "total_score": self.total_score(),
            "max_score": self.max_score(),
            "score_pct": round(self.score_pct(), 1),
            "fall_risk": self.fall_risk(),
            "recommended_aid": self.recommended_aid(),
            "items_at_risk": self.items_at_risk(),
        }

def run():
    bbc = BergBalanceCalculator(
        patient_name="Patient-B",
        items=[
            BergItem("sit_to_stand", ItemRating.THREE),
            BergItem("standing_unsupported", ItemRating.THREE),
            BergItem("sitting_unsupported", ItemRating.FOUR),
            BergItem("stand_to_sit", ItemRating.THREE),
            BergItem("transfers", ItemRating.THREE),
            BergItem("standing_eyes_closed", ItemRating.TWO),
            BergItem("standing_feet_together", ItemRating.TWO),
            BergItem("reaching_forward", ItemRating.THREE),
            BergItem("picking_up_object", ItemRating.THREE),
            BergItem("turning_look_behind", ItemRating.TWO),
            BergItem("turning_360", ItemRating.TWO),
            BergItem("stool_stepping", ItemRating.ONE),
            BergItem("standing_one_foot", ItemRating.ZERO),
            BergItem("standing_narrow_base", ItemRating.ONE),
        ]
    )
    print(bbc.stats())

if __name__ == "__main__":
    run()
