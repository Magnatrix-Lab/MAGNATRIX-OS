"""Native stdlib module: Tea Blend Calculator
Balances tea blend ratios, flavor profiles, and cost.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class TeaBlendComponent:
    name: str
    weight_g: float
    cost_per_g: float
    flavor_profile: str  # floral, earthy, sweet, astringent, vegetal
    caffeine_pct: float = 3.0

@dataclass
class TeaBlendCalculator:
    components: List[TeaBlendComponent]

    def total_weight_g(self) -> float:
        return sum(c.weight_g for c in self.components)

    def component_pcts(self) -> Dict[str, float]:
        total = self.total_weight_g()
        if total == 0:
            return {}
        return {c.name: (c.weight_g / total) * 100 for c in self.components}

    def total_cost(self) -> float:
        return sum(c.weight_g * c.cost_per_g for c in self.components)

    def cost_per_g(self) -> float:
        if self.total_weight_g() == 0:
            return 0
        return self.total_cost() / self.total_weight_g()

    def caffeine_pct(self) -> float:
        total = self.total_weight_g()
        if total == 0:
            return 0
        return sum(c.weight_g * c.caffeine_pct for c in self.components) / total

    def flavor_balance(self) -> Dict[str, float]:
        total = self.total_weight_g()
        if total == 0:
            return {}
        profiles = {}
        for c in self.components:
            profiles[c.flavor_profile] = profiles.get(c.flavor_profile, 0) + c.weight_g
        return {k: (v / total) * 100 for k, v in profiles.items()}

    def blend_complexity(self) -> float:
        return len(self.components) * 20

    def stats(self) -> Dict:
        return {
            "total_weight_g": round(self.total_weight_g(), 1),
            "component_pcts": {k: round(v, 1) for k, v in self.component_pcts().items()},
            "total_cost": round(self.total_cost(), 2),
            "cost_per_g": round(self.cost_per_g(), 2),
            "caffeine_pct": round(self.caffeine_pct(), 2),
            "flavor_balance": {k: round(v, 1) for k, v in self.flavor_balance().items()},
            "blend_complexity": round(self.blend_complexity(), 1),
        }

def run():
    comps = [
        TeaBlendComponent("keemun", 30, 0.08, "earthy", 3.5),
        TeaBlendComponent("darjeeling", 20, 0.12, "floral", 3.2),
        TeaBlendComponent("rose_petals", 5, 0.15, "floral", 0),
    ]
    tbc = TeaBlendCalculator(components=comps)
    print(tbc.stats())

if __name__ == "__main__":
    run()
