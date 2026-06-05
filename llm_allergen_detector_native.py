"""Allergen Detector — ingredient scan, cross-contamination, warnings, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class AllergenDetector:
    allergens: Set[str] = field(default_factory=lambda: {"peanut", "gluten", "dairy", "soy", "egg", "fish", "shellfish", "tree nut", "wheat"})
    cross_contamination: Dict[str, Set[str]] = field(default_factory=dict)

    def detect(self, ingredients: List[str]) -> Set[str]:
        found = set()
        for ing in ingredients:
            for allergen in self.allergens:
                if allergen in ing.lower():
                    found.add(allergen)
        return found

    def cross_risk(self, ingredient: str) -> Set[str]:
        return self.cross_contamination.get(ingredient.lower(), set())

    def safe_for(self, ingredients: List[str], known_allergies: Set[str]) -> bool:
        detected = self.detect(ingredients)
        for a in known_allergies:
            if a.lower() in detected:
                return False
        for ing in ingredients:
            risk = self.cross_risk(ing)
            if risk & known_allergies:
                return False
        return True

    def add_cross_contamination(self, ingredient: str, risks: List[str]):
        self.cross_contamination[ingredient.lower()] = set(r.lower() for r in risks)

    def stats(self, ingredients: List[str]) -> Dict:
        return {"allergens_found": list(self.detect(ingredients)), "count": len(self.detect(ingredients))}

def run():
    ad = AllergenDetector()
    ad.add_cross_contamination("chocolate", ["dairy", "soy"])
    ingredients = ["flour", "peanut butter", "chocolate", "sugar"]
    print(ad.stats(ingredients))
    print("Safe for dairy-free:", ad.safe_for(ingredients, {"dairy"}))

if __name__ == "__main__":
    run()
