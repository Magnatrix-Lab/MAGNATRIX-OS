"""Perfume Blender — top, middle, base notes, accords, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class PerfumeBlender:
    top_notes: List[str] = field(default_factory=list)
    middle_notes: List[str] = field(default_factory=list)
    base_notes: List[str] = field(default_factory=list)
    concentrations: Dict[str, float] = field(default_factory=dict)

    def accord(self, notes: List[str]) -> str:
        if len(notes) >= 3:
            return f"complex accord with {', '.join(notes[:3])}"
        return f"simple {'-'.join(notes)} accord"

    def longevity_estimate(self) -> float:
        base_weight = len(self.base_notes) * 2
        mid_weight = len(self.middle_notes) * 1.5
        top_weight = len(self.top_notes) * 0.5
        total = base_weight + mid_weight + top_weight
        return total * 0.5

    def sillage_score(self) -> float:
        top_weight = len(self.top_notes) * 2
        return min(10, top_weight + len(self.middle_notes))

    def formula_pct(self) -> Dict[str, float]:
        total = sum(self.concentrations.values())
        if total == 0:
            return {}
        return {k: v / total * 100 for k, v in self.concentrations.items()}

    def stats(self) -> Dict:
        return {"notes": len(self.top_notes) + len(self.middle_notes) + len(self.base_notes), "longevity": round(self.longevity_estimate(), 1), "sillage": self.sillage_score()}

def run():
    pb = PerfumeBlender(top_notes=["bergamot", "lemon"], middle_notes=["rose", "jasmine"], base_notes=["vanilla", "musk"], concentrations={"ethanol": 80, "fragrance": 20})
    print(pb.stats())
    print("Formula:", pb.formula_pct())

if __name__ == "__main__":
    run()
