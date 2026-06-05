"""Tourist Flow — density, heatmap, capacity, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class TouristFlow:
    locations: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    visitor_counts: Dict[str, int] = field(default_factory=dict)
    capacities: Dict[str, int] = field(default_factory=dict)

    def add_location(self, name: str, x: float, y: float, capacity: int):
        self.locations[name] = (x, y)
        self.capacities[name] = capacity

    def density(self, location: str) -> float:
        return self.visitor_counts.get(location, 0) / self.capacities.get(location, 1)

    def overcrowded(self, threshold: float = 0.8) -> List[str]:
        return [name for name in self.locations if self.density(name) > threshold]

    def heatmap_value(self, x: float, y: float, radius: float = 5.0) -> float:
        total = 0.0
        for name, (lx, ly) in self.locations.items():
            dist = ((x - lx) ** 2 + (y - ly) ** 2) ** 0.5
            if dist < radius:
                total += self.visitor_counts.get(name, 0) / (1 + dist)
        return total

    def recommend_reroute(self, from_loc: str) -> Optional[str]:
        fx, fy = self.locations.get(from_loc, (0, 0))
        candidates = [(name, self.density(name)) for name in self.locations if name != from_loc]
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0] if candidates else None

    def stats(self) -> Dict:
        return {"locations": len(self.locations), "total_visitors": sum(self.visitor_counts.values()), "overcrowded": len(self.overcrowded())}

def run():
    tf = TouristFlow()
    tf.add_location("Entrance", 0, 0, 500)
    tf.add_location("Museum", 10, 5, 200)
    tf.add_location("Garden", 5, 10, 300)
    tf.visitor_counts = {"Entrance": 450, "Museum": 180, "Garden": 290}
    print(tf.stats())
    print("Overcrowded:", tf.overcrowded())
    print("Reroute from Entrance:", tf.recommend_reroute("Entrance"))

if __name__ == "__main__":
    run()
