"""Bridge Inspector — condition rating, deterioration, load rating, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class BridgeElement:
    name: str
    condition: int
    """1-9 scale, 9 is excellent"""
    age_years: int

class BridgeInspector:
    def __init__(self):
        self.elements: List[BridgeElement] = []

    def add_element(self, e: BridgeElement):
        self.elements.append(e)

    def overall_rating(self) -> float:
        if not self.elements:
            return 0.0
        return sum(e.condition for e in self.elements) / len(self.elements)

    def deterioration_rate(self, e: BridgeElement) -> float:
        return (9 - e.condition) / max(1, e.age_years)

    def load_rating(self, design_load: float) -> float:
        rating = self.overall_rating()
        return design_load * (rating / 9) ** 2

    def priority_repair(self) -> List[str]:
        return [e.name for e in sorted(self.elements, key=lambda x: x.condition)[:3]]

    def stats(self) -> Dict:
        return {"elements": len(self.elements), "rating": round(self.overall_rating(), 2), "priority": self.priority_repair()}

def run():
    bi = BridgeInspector()
    bi.add_element(BridgeElement("Deck", 6, 15))
    bi.add_element(BridgeElement("Girders", 5, 20))
    bi.add_element(BridgeElement("Bearings", 7, 15))
    bi.add_element(BridgeElement("Approach", 4, 25))
    print(bi.stats())
    print("Load rating:", bi.load_rating(40))

if __name__ == "__main__":
    run()
