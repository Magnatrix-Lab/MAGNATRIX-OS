"""Native stdlib module: Essential Oil Safety Calculator
Checks max dermal limits, phototoxicity, and dilution safety.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class EssentialOilSafetyCalculator:
    oil_name: str
    dilution_pct: float
    application_area_ml: float  # area of skin in ml (approx)
    age_group: str = "adult"  # adult, child, elderly, pregnant

    _MAX_DERMAL_LIMITS = {
        "bergamot": 0.4, "lemon": 2.0, "lime": 0.7, "grapefruit": 4.0,
        "cinnamon_bark": 0.07, "clove": 0.5, "oregano": 1.1, "thyme": 1.3,
        "peppermint": 5.4, "tea_tree": 15.0, "lavender": 100.0, "rose": 100.0,
    }

    _PHOTOTOXIC = {
        "bergamot": True, "lemon": True, "lime": True, "grapefruit": True,
        "bitter_orange": True, "mandarin": False, "sweet_orange": False,
    }

    _AGE_FACTORS = {"adult": 1.0, "child": 0.5, "elderly": 0.7, "pregnant": 0.5}

    def max_dermal_limit_pct(self) -> float:
        base = self._MAX_DERMAL_LIMITS.get(self.oil_name, 5.0)
        return base * self._AGE_FACTORS.get(self.age_group, 1.0)

    def is_safe_dilution(self) -> bool:
        return self.dilution_pct <= self.max_dermal_limit_pct()

    def is_phototoxic(self) -> bool:
        return self._PHOTOTOXIC.get(self.oil_name, False)

    def safety_margin(self) -> float:
        limit = self.max_dermal_limit_pct()
        if limit == 0:
            return 0
        return (limit - self.dilution_pct) / limit * 100

    def max_safe_drops_per_10ml(self) -> float:
        if self.max_dermal_limit_pct() == 0:
            return 0
        return self.max_dermal_limit_pct() * 2  # approx 20 drops per ml, 1% ~ 2 drops per 10ml

    def recommendation(self) -> str:
        if not self.is_safe_dilution():
            return "exceeds_safe_limit_reduce_dilution"
        if self.is_phototoxic() and self.dilution_pct > 0.1:
            return "safe_but_avoid_sun_if_applied_to_skin"
        if self.age_group == "pregnant" and self.oil_name in ["clove", "cinnamon_bark"]:
            return "avoid_during_pregnancy"
        return "safe_for_use"

    def stats(self) -> Dict:
        return {
            "oil_name": self.oil_name,
            "dilution_pct": self.dilution_pct,
            "age_group": self.age_group,
            "max_dermal_limit_pct": round(self.max_dermal_limit_pct(), 2),
            "is_safe": self.is_safe_dilution(),
            "is_phototoxic": self.is_phototoxic(),
            "safety_margin_pct": round(self.safety_margin(), 1),
            "max_safe_drops_per_10ml": round(self.max_safe_drops_per_10ml(), 1),
            "recommendation": self.recommendation(),
        }

def run():
    eosc = EssentialOilSafetyCalculator(oil_name="bergamot", dilution_pct=0.3, application_area_ml=5, age_group="adult")
    print(eosc.stats())

if __name__ == "__main__":
    run()
