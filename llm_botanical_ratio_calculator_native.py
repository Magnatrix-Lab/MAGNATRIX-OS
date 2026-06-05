"""Native stdlib module: Botanical Ratio Calculator
Balances gin botanicals, maceration ratios, and flavor profiles.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Botanical:
    name: str
    weight_g: float
    flavor_category: str  # citrus, floral, spice, herbal, root, berry
    intensity: float  # 1-10 scale
    maceration_days: int

@dataclass
class BotanicalRatioCalculator:
    botanicals: List[Botanical]
    base_spirit_volume_l: float = 1.0

    def total_botanical_weight_g(self) -> float:
        return sum(b.weight_g for b in self.botanicals)

    def botanicals_per_l(self) -> float:
        if self.base_spirit_volume_l == 0:
            return 0
        return self.total_botanical_weight_g() / self.base_spirit_volume_l

    def juniper_ratio_pct(self) -> float:
        juniper = sum(b.weight_g for b in self.botanicals if b.name.lower() == "juniper")
        if self.total_botanical_weight_g() == 0:
            return 0
        return (juniper / self.total_botanical_weight_g()) * 100

    def flavor_balance(self) -> Dict[str, float]:
        total = self.total_botanical_weight_g()
        if total == 0:
            return {}
        balance = {}
        for b in self.botanicals:
            balance[b.flavor_category] = balance.get(b.flavor_category, 0) + b.weight_g
        return {k: (v / total) * 100 for k, v in balance.items()}

    def max_maceration_days(self) -> int:
        return max(b.maceration_days for b in self.botanicals) if self.botanicals else 0

    def avg_intensity(self) -> float:
        if not self.botanicals:
            return 0
        return sum(b.intensity * b.weight_g for b in self.botanicals) / self.total_botanical_weight_g()

    def complexity_score(self) -> float:
        categories = len(self.flavor_balance())
        return categories * 15 + self.avg_intensity() * 3

    def stats(self) -> Dict:
        return {
            "total_botanical_weight_g": round(self.total_botanical_weight_g(), 1),
            "botanicals_per_l": round(self.botanicals_per_l(), 1),
            "juniper_ratio_pct": round(self.juniper_ratio_pct(), 1),
            "flavor_balance": {k: round(v, 1) for k, v in self.flavor_balance().items()},
            "max_maceration_days": self.max_maceration_days(),
            "avg_intensity": round(self.avg_intensity(), 1),
            "complexity_score": round(self.complexity_score(), 1),
        }

def run():
    botanicals = [
        Botanical("juniper", 30, "herbal", 7, 14),
        Botanical("coriander", 10, "citrus", 5, 7),
        Botanical("angelica", 5, "root", 6, 14),
        Botanical("cardamom", 3, "spice", 8, 7),
        Botanical("lemon_peel", 5, "citrus", 4, 5),
    ]
    brc = BotanicalRatioCalculator(botanicals=botanicals, base_spirit_volume_l=1)
    print(brc.stats())

if __name__ == "__main__":
    run()
