"""Stratigraphy Mapper — layers, dating, correlation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Layer:
    id: str
    depth_top: float
    depth_bottom: float
    estimated_age: float
    material: str

class StratigraphyMapper:
    def __init__(self):
        self.layers: List[Layer] = []

    def add_layer(self, l: Layer):
        self.layers.append(l)

    def thickness(self, layer_id: str) -> float:
        l = next((x for x in self.layers if x.id == layer_id), None)
        return l.depth_bottom - l.depth_top if l else 0.0

    def chronological_order(self) -> List[str]:
        return [l.id for l in sorted(self.layers, key=lambda x: x.estimated_age, reverse=True)]

    def find_at_depth(self, depth: float) -> Optional[str]:
        for l in self.layers:
            if l.depth_top <= depth <= l.depth_bottom:
                return l.id
        return None

    def correlation_score(self, site1: List[Layer], site2: List[Layer]) -> float:
        if not site1 or not site2:
            return 0.0
        matches = 0
        for l1 in site1:
            for l2 in site2:
                if abs(l1.estimated_age - l2.estimated_age) < 100 and l1.material == l2.material:
                    matches += 1
        return matches / max(len(site1), len(site2))

    def stats(self) -> Dict:
        return {"layers": len(self.layers), "total_depth": max(l.depth_bottom for l in self.layers) if self.layers else 0}

def run():
    sm = StratigraphyMapper()
    sm.add_layer(Layer("A", 0, 0.5, 1000, "clay"))
    sm.add_layer(Layer("B", 0.5, 1.5, 2000, "sand"))
    sm.add_layer(Layer("C", 1.5, 3.0, 5000, "rock"))
    print(sm.stats())
    print("Order:", sm.chronological_order())
    print("At 1.0m:", sm.find_at_depth(1.0))

if __name__ == "__main__":
    run()
