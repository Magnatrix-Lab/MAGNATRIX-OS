"""Event Planner — capacity, catering, seating, timeline, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class EventPlanner:
    guests: int = 100
    venue_capacity: int = 120
    course_type: str = "buffet"
    duration_hours: float = 4.0

    def capacity_ok(self) -> bool:
        return self.guests <= self.venue_capacity

    def catering_units(self) -> int:
        if self.course_type == "buffet":
            return max(1, self.guests // 50)
        elif self.course_type == "plated":
            return self.guests
        return self.guests // 8

    def staff_needed(self) -> int:
        base = self.guests // 25
        if self.course_type == "plated":
            base += self.guests // 15
        return base

    def timeline(self) -> List[Dict]:
        events = [
            {"time": 0, "event": "setup"},
            {"time": 0.5, "event": "guest arrival"},
            {"time": 1.0, "event": "service"},
            {"time": self.duration_hours - 0.5, "event": "last call"},
            {"time": self.duration_hours, "event": "cleanup"}
        ]
        return events

    def cost_estimate(self, per_person: float = 50, venue_cost: float = 1000) -> float:
        return self.guests * per_person + venue_cost + self.staff_needed() * 200

    def stats(self) -> Dict:
        return {"guests": self.guests, "capacity_ok": self.capacity_ok(), "staff": self.staff_needed(), "catering_units": self.catering_units()}

def run():
    ep = EventPlanner(guests=80, venue_capacity=100, course_type="plated", duration_hours=3)
    print(ep.stats())
    print("Cost:", ep.cost_estimate())
    print("Timeline:", ep.timeline())

if __name__ == "__main__":
    run()
