"""Native stdlib module: Guest List Manager
Manages RSVP status, dietary restrictions, and seating preferences for events.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set
from enum import Enum

class RSVPStatus(Enum):
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"
    PENDING = "pending"

@dataclass
class GuestEntry:
    name: str
    email: str
    rsvp: RSVPStatus
    dietary: List[str] = field(default_factory=list)
    plus_one: bool = False
    table_preference: str = ""

@dataclass
class GuestListManager:
    event_name: str
    guests: List[GuestEntry] = field(default_factory=list)
    max_capacity: int = 0

    def rsvp_counts(self) -> Dict[str, int]:
        counts = {}
        for g in self.guests:
            counts[g.rsvp.value] = counts.get(g.rsvp.value, 0) + 1
        return counts

    def attending_count(self) -> int:
        return sum(1 for g in self.guests if g.rsvp == RSVPStatus.YES) + sum(1 for g in self.guests if g.rsvp == RSVPStatus.YES and g.plus_one)

    def dietary_restrictions(self) -> Dict[str, int]:
        restrictions = {}
        for g in self.guests:
            for d in g.dietary:
                restrictions[d] = restrictions.get(d, 0) + 1
        return restrictions

    def at_capacity(self) -> bool:
        if self.max_capacity == 0:
            return False
        return self.attending_count() >= self.max_capacity

    def stats(self) -> Dict:
        return {
            "event": self.event_name,
            "total_invited": len(self.guests),
            "attending": self.attending_count(),
            "rsvp_counts": self.rsvp_counts(),
            "dietary": self.dietary_restrictions(),
            "at_capacity": self.at_capacity(),
        }

def run():
    glm = GuestListManager(
        event_name="Summer Party",
        max_capacity=100,
        guests=[
            GuestEntry("Alice", "alice@example.com", RSVPStatus.YES, ["vegetarian"], plus_one=True),
            GuestEntry("Bob", "bob@example.com", RSVPStatus.YES, ["gluten_free"]),
            GuestEntry("Carol", "carol@example.com", RSVPStatus.MAYBE),
            GuestEntry("Dave", "dave@example.com", RSVPStatus.NO),
            GuestEntry("Eve", "eve@example.com", RSVPStatus.PENDING, ["nut_allergy"]),
        ]
    )
    print(glm.stats())

if __name__ == "__main__":
    run()
