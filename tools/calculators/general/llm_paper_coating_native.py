"""Native stdlib module: Paper Coating Calculator
Calculates coating recipes, coat weights, and coverage for coated papers.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class CoatingIngredient:
    name: str
    weight_pct: float
    solids_pct: float

@dataclass
class PaperCoatingCalculator:
    coating_name: str
    target_coat_weight_g_m2: float
    target_solids_pct: float
    ingredients: List[CoatingIngredient] = field(default_factory=list)
    base_paper_absorbency_g_m2: float = 10.0

    def total_formulation_pct(self) -> float:
        return sum(i.weight_pct for i in self.ingredients)

    def wet_coat_weight_g_m2(self) -> float:
        if self.target_solids_pct == 0:
            return 0.0
        return self.target_coat_weight_g_m2 / (self.target_solids_pct / 100)

    def water_content_g_m2(self) -> float:
        return self.wet_coat_weight_g_m2() - self.target_coat_weight_g_m2

    def dry_ingredient_weight_g_m2(self, ingredient: CoatingIngredient) -> float:
        if self.total_formulation_pct() == 0:
            return 0.0
        return self.target_coat_weight_g_m2 * (ingredient.weight_pct / self.total_formulation_pct()) * (ingredient.solids_pct / 100)

    def coverage_pct(self, paper_area_m2: float = 1) -> float:
        if paper_area_m2 == 0:
            return 0.0
        return 100.0

    def binder_to_pigment_ratio(self) -> float:
        pigment = sum(i.weight_pct for i in self.ingredients if "pigment" in i.name.lower() or "clay" in i.name.lower() or "tio2" in i.name.lower())
        binder = sum(i.weight_pct for i in self.ingredients if "binder" in i.name.lower() or "latex" in i.name.lower() or "starch" in i.name.lower())
        if pigment == 0:
            return 0.0
        return binder / pigment

    def stats(self) -> Dict:
        return {
            "coating": self.coating_name,
            "target_coat_weight": self.target_coat_weight_g_m2,
            "wet_coat_weight": round(self.wet_coat_weight_g_m2(), 1),
            "water_content_g_m2": round(self.water_content_g_m2(), 1),
            "binder_pigment_ratio": round(self.binder_to_pigment_ratio(), 3),
            "ingredients": len(self.ingredients),
        }

def run():
    pcc = PaperCoatingCalculator(
        coating_name="Matte Coating",
        target_coat_weight_g_m2=12,
        target_solids_pct=65,
        ingredients=[
            CoatingIngredient("kaolin_clay", 60, 100),
            CoatingIngredient("calcium_carbonate", 20, 100),
            CoatingIngredient("latex_binder", 12, 50),
            CoatingIngredient("starch", 5, 100),
            CoatingIngredient("dispersant", 3, 40),
        ]
    )
    print(pcc.stats())

if __name__ == "__main__":
    run()
