"""Hotel Ranker — reviews, amenities, location, price, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Hotel:
    name: str
    rating: float
    review_count: int
    price: float
    amenities: List[str]
    distance_to_center: float

class HotelRanker:
    def __init__(self):
        self.hotels: List[Hotel] = []

    def add_hotel(self, h: Hotel):
        self.hotels.append(h)

    def score(self, h: Hotel, weights: Dict[str, float] = None) -> float:
        w = weights or {"rating": 0.3, "reviews": 0.1, "price": 0.2, "amenities": 0.2, "location": 0.2}
        price_score = max(0, 1 - h.price / 500)
        amenity_score = min(1, len(h.amenities) / 10)
        location_score = max(0, 1 - h.distance_to_center / 5)
        review_score = min(1, h.review_count / 1000)
        return (h.rating / 5) * w["rating"] + review_score * w["reviews"] + price_score * w["price"] + amenity_score * w["amenities"] + location_score * w["location"]

    def rank(self, weights: Dict[str, float] = None) -> List[Tuple[str, float]]:
        scored = [(h.name, self.score(h, weights)) for h in self.hotels]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def filter_by_budget(self, max_price: float) -> List[Hotel]:
        return [h for h in self.hotels if h.price <= max_price]

    def stats(self) -> Dict:
        return {"hotels": len(self.hotels), "avg_rating": sum(h.rating for h in self.hotels) / len(self.hotels) if self.hotels else 0}

def run():
    hr = HotelRanker()
    hr.add_hotel(Hotel("A", 4.5, 500, 120, ["pool", "wifi", "gym"], 0.5))
    hr.add_hotel(Hotel("B", 3.8, 200, 80, ["wifi"], 2.0))
    hr.add_hotel(Hotel("C", 4.8, 1200, 200, ["pool", "spa", "gym", "restaurant"], 0.2))
    print(hr.stats())
    print("Rank:", hr.rank())
    print("Budget <100:", [h.name for h in hr.filter_by_budget(100)])

if __name__ == "__main__":
    run()
