"""Feed Ration Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class FeedRation:
    animal_type: str
    animal_weight_kg: float
    production_stage: str = "maintenance"
    feed_components: Dict[str, float] = field(default_factory=dict)

    def dry_matter_intake_kg(self) -> float:
        factors = {
            "dairy_cow": 0.03, "beef_cattle": 0.025, "pig": 0.04,
            "sheep": 0.035, "goat": 0.035, "chicken": 0.05
        }
        factor = factors.get(self.animal_type, 0.03)
        prod_factor = {"maintenance": 1.0, "growth": 1.2, "lactation": 1.4, "finishing": 1.1}
        return round(self.animal_weight_kg * factor * prod_factor.get(self.production_stage, 1.0), 2)

    def total_feed_kg(self) -> float:
        return round(sum(self.feed_components.values()), 2)

    def feed_composition_percent(self) -> Dict[str, float]:
        total = self.total_feed_kg()
        if total <= 0:
            return {}
        return {k: round(v / total * 100, 2) for k, v in self.feed_components.items()}

    def protein_requirement_kg(self) -> float:
        requirements = {
            "dairy_cow": 0.12, "beef_cattle": 0.10, "pig": 0.14,
            "sheep": 0.10, "goat": 0.10, "chicken": 0.18
        }
        req = requirements.get(self.animal_type, 0.12)
        return round(self.dry_matter_intake_kg() * req, 3)

    def energy_requirement_mj(self) -> float:
        base = self.animal_weight_kg ** 0.75 * 0.5
        prod_factor = {"maintenance": 1.0, "growth": 1.5, "lactation": 2.0, "finishing": 1.3}
        return round(base * prod_factor.get(self.production_stage, 1.0), 2)

    def cost_per_animal(self, prices: Dict[str, float]) -> float:
        cost = 0.0
        for feed, qty in self.feed_components.items():
            cost += qty * prices.get(feed, 0.5)
        return round(cost, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "dry_matter_intake_kg": self.dry_matter_intake_kg(),
            "total_feed_kg": self.total_feed_kg(),
            "protein_requirement_kg": self.protein_requirement_kg(),
        }

    def run(self):
        print("=" * 60)
        print("FEED RATION CALCULATOR")
        print("=" * 60)
        fr = FeedRation(
            animal_type="dairy_cow", animal_weight_kg=600, production_stage="lactation",
            feed_components={"hay": 8, "grain": 6, "silage": 12, "protein": 1.5}
        )
        print(f"Animal: {fr.animal_type} ({fr.animal_weight_kg} kg)")
        print(f"Stage: {fr.production_stage}")
        print(f"DMI: {fr.dry_matter_intake_kg():.2f} kg")
        print(f"Total feed: {fr.total_feed_kg():.2f} kg")
        print(f"Composition: {fr.feed_composition_percent()}")
        print(f"Protein req: {fr.protein_requirement_kg():.3f} kg")
        print(f"Energy req: {fr.energy_requirement_mj():.2f} MJ")
        print(f"Stats: {fr.stats()}")

if __name__ == "__main__":
    FeedRation("cattle", 0).run()
