"""Phase Diagram — Gibbs phase rule, lever rule, coexistence, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Phase:
    name: str
    composition: Dict[str, float] = field(default_factory=dict)
    temperature: float = 0.0

@dataclass
class PhaseDiagram:
    phases: List[Phase] = field(default_factory=list)
    components: int = 2

    def gibbs_phase_rule(self, pressure_fixed: bool = False) -> int:
        variables = 2 if not pressure_fixed else 1
        return self.components - len(self.phases) + variables + 1

    def lever_rule(self, overall: float, left: float, right: float) -> Tuple[float, float]:
        if left == right:
            return 0.5, 0.5
        w_left = (right - overall) / (right - left)
        w_right = (overall - left) / (right - left)
        return w_left, w_right

    def eutectic_point(self, temps: List[float], comps: List[float]) -> Optional[Tuple[float, float]]:
        if len(temps) < 3 or len(comps) != len(temps):
            return None
        min_t = min(temps)
        idx = temps.index(min_t)
        if 0 < idx < len(temps) - 1:
            return comps[idx], temps[idx]
        return None

    def stats(self) -> Dict:
        return {"phases": len(self.phases), "components": self.components, "degrees_of_freedom": self.gibbs_phase_rule()}

def run():
    pd = PhaseDiagram([Phase("alpha", {"A":0.9,"B":0.1}, 500), Phase("beta", {"A":0.1,"B":0.9}, 600)])
    print(pd.stats())
    print("Lever:", pd.lever_rule(0.5, 0.2, 0.8))
    print("Eutectic:", pd.eutectic_point([600,500,400,500], [0,0.2,0.5,1]))

if __name__ == "__main__":
    run()
