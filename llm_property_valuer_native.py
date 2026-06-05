"""Native stdlib module: Property Valuer
Estimates property value using comparable sales and adjustment factors.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ComparableSale:
    address: str
    sale_price: float
    sqft: float
    bedrooms: int
    bathrooms: float
    age_years: int

@dataclass
class PropertyValuer:
    subject_address: str
    subject_sqft: float
    subject_bedrooms: int
    subject_bathrooms: float
    subject_age: int
    comparables: List[ComparableSale] = field(default_factory=list)

    def _adjust_price(self, comp: ComparableSale) -> float:
        price_per_sqft = comp.sale_price / max(1, comp.sqft)
        adjusted = comp.sale_price
        adjusted += (self.subject_sqft - comp.sqft) * price_per_sqft
        adjusted += (self.subject_bedrooms - comp.bedrooms) * 15000
        adjusted += (self.subject_bathrooms - comp.bathrooms) * 10000
        adjusted -= (self.subject_age - comp.age_years) * 500
        return adjusted

    def estimated_value(self) -> float:
        if not self.comparables:
            return 0.0
        adjusted = [self._adjust_price(c) for c in self.comparables]
        return sum(adjusted) / len(adjusted)

    def price_per_sqft(self) -> float:
        val = self.estimated_value()
        if val == 0 or self.subject_sqft == 0:
            return 0.0
        return val / self.subject_sqft

    def stats(self) -> Dict[str, float]:
        return {
            "estimated_value": round(self.estimated_value(), 2),
            "price_per_sqft": round(self.price_per_sqft(), 2),
            "comparables_used": len(self.comparables),
        }

def run():
    pv = PropertyValuer(
        subject_address="123 Main St",
        subject_sqft=2100,
        subject_bedrooms=4,
        subject_bathrooms=2.5,
        subject_age=15,
        comparables=[
            ComparableSale("111 Oak", 420000, 2000, 3, 2, 12),
            ComparableSale("222 Pine", 480000, 2200, 4, 3, 18),
            ComparableSale("333 Elm", 450000, 2100, 4, 2.5, 14),
        ]
    )
    print(pv.stats())

if __name__ == "__main__":
    run()
