"""Visitor Analytics — demographics, dwell, heatmap, conversion, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class VisitorAnalytics:
    visits: List[Dict] = field(default_factory=list)
    """Each: {time, zone, dwell_seconds, age_group, member}"""

    def add_visit(self, visit: Dict):
        self.visits.append(visit)

    def zone_popularity(self) -> Dict[str, int]:
        counts = {}
        for v in self.visits:
            z = v.get("zone", "unknown")
            counts[z] = counts.get(z, 0) + 1
        return counts

    def avg_dwell(self, zone: str = None) -> float:
        filtered = [v for v in self.visits if zone is None or v.get("zone") == zone]
        if not filtered:
            return 0.0
        return sum(v.get("dwell_seconds", 0) for v in filtered) / len(filtered)

    def member_ratio(self) -> float:
        members = sum(1 for v in self.visits if v.get("member", False))
        return members / len(self.visits) if self.visits else 0.0

    def age_distribution(self) -> Dict[str, int]:
        dist = {}
        for v in self.visits:
            ag = v.get("age_group", "unknown")
            dist[ag] = dist.get(ag, 0) + 1
        return dist

    def conversion_rate(self, gift_shop_visitors: int) -> float:
        total = len(self.visits)
        return gift_shop_visitors / total if total > 0 else 0.0

    def stats(self) -> Dict:
        return {"visits": len(self.visits), "avg_dwell_sec": round(self.avg_dwell(), 1), "member_ratio": round(self.member_ratio(), 3)}

def run():
    va = VisitorAnalytics()
    va.add_visit({"time": 10, "zone": "A", "dwell_seconds": 300, "age_group": "adult", "member": True})
    va.add_visit({"time": 11, "zone": "B", "dwell_seconds": 120, "age_group": "child", "member": False})
    va.add_visit({"time": 12, "zone": "A", "dwell_seconds": 450, "age_group": "adult", "member": True})
    print(va.stats())
    print("Zones:", va.zone_popularity())
    print("Age dist:", va.age_distribution())

if __name__ == "__main__":
    run()
