"""Native stdlib module: Glaze Calculator
Calculates glaze recipes, expansion coefficients, and viscosity.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class GlazeIngredient:
    name: str
    weight_g: float
    expansion_coefficient: float
    melting_point_c: float

@dataclass
class GlazeCalculator:
    glaze_name: str
    ingredients: List[GlazeIngredient] = field(default_factory=list)
    target_expansion: float = 5.0

    def total_weight_g(self) -> float:
        return sum(i.weight_g for i in self.ingredients)

    def weighted_expansion(self) -> float:
        if self.total_weight_g() == 0:
            return 0.0
        return sum(i.weight_g * i.expansion_coefficient for i in self.ingredients) / self.total_weight_g()

    def weighted_melting_point(self) -> float:
        if self.total_weight_g() == 0:
            return 0.0
        return sum(i.weight_g * i.melting_point_c for i in self.ingredients) / self.total_weight_g()

    def expansion_match(self) -> float:
        return self.target_expansion - self.weighted_expansion()

    def silica_to_alumina_ratio(self) -> float:
        silica = sum(i.weight_g for i in self.ingredients if "silica" in i.name.lower())
        alumina = sum(i.weight_g for i in self.ingredients if "alumina" in i.name.lower() or "kaolin" in i.name.lower())
        if alumina == 0:
            return 0.0
        return silica / alumina

    def stats(self) -> Dict:
        return {
            "glaze": self.glaze_name,
            "total_weight_g": round(self.total_weight_g(), 1),
            "weighted_expansion": round(self.weighted_expansion(), 3),
            "weighted_melting_c": round(self.weighted_melting_point(), 1),
            "expansion_match": round(self.expansion_match(), 3),
            "silica_alumina_ratio": round(self.silica_to_alumina_ratio(), 2),
        }

def run():
    gc = GlazeCalculator(
        glaze_name="Celadon",
        target_expansion=5.0,
        ingredients=[
            GlazeIngredient("silica", 300, 0.35, 1700),
            GlazeIngredient("kaolin", 250, 0.2, 1700),
            GlazeIngredient("feldspar", 350, 0.25, 1200),
            GlazeIngredient("whiting", 100, 0.3, 900),
        ]
    )
    print(gc.stats())

if __name__ == "__main__":
    run()
