"""Guest Profiler — segmentation, preferences, CLV, RFM, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Guest:
    id: str
    stays: int = 0
    total_spend: float = 0.0
    last_stay_days: int = 0
    preferences: List[str] = field(default_factory=list)

class GuestProfiler:
    def __init__(self):
        self.guests: Dict[str, Guest] = {}

    def add_guest(self, g: Guest):
        self.guests[g.id] = g

    def rfm_score(self, guest_id: str) -> Tuple[int, int, int]:
        g = self.guests.get(guest_id)
        if not g:
            return 0, 0, 0
        r = max(1, 5 - g.last_stay_days // 30)
        f = min(5, g.stays)
        m = min(5, int(g.total_spend / 500) + 1)
        return r, f, m

    def segment(self, guest_id: str) -> str:
        r, f, m = self.rfm_score(guest_id)
        if r >= 4 and f >= 4 and m >= 4:
            return "champion"
        elif r >= 3 and f >= 3 and m >= 3:
            return "loyal"
        elif r >= 3:
            return "potential"
        elif f <= 2:
            return "new"
        return "at_risk"

    def clv(self, guest_id: str, margin: float = 0.3, retention: float = 0.7, horizon: int = 5) -> float:
        g = self.guests.get(guest_id)
        if not g or g.stays == 0:
            return 0.0
        avg_spend = g.total_spend / g.stays
        return avg_spend * margin * sum(retention ** i for i in range(horizon))

    def stats(self) -> Dict:
        segs = {}
        for g in self.guests:
            s = self.segment(g)
            segs[s] = segs.get(s, 0) + 1
        return {"guests": len(self.guests), "segments": segs}

def run():
    gp = GuestProfiler()
    gp.add_guest(Guest("G1", 10, 5000, 15, ["suite", "late_checkout"]))
    gp.add_guest(Guest("G2", 2, 300, 90, ["standard"]))
    print(gp.stats())
    print("G1 segment:", gp.segment("G1"))
    print("G1 CLV:", gp.clv("G1"))

if __name__ == "__main__":
    run()
