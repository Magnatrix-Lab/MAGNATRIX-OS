"""Native stdlib module: Seating Arranger
Arranges seating by table size, group relationships, and constraints.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set

@dataclass
class Guest:
    name: str
    group: str
    vip: bool = False
    constraints: List[str] = field(default_factory=list)

@dataclass
class Table:
    table_id: int
    capacity: int
    guests: List[Guest] = field(default_factory=list)

@dataclass
class SeatingArranger:
    event_name: str
    guests: List[Guest] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)

    def total_capacity(self) -> int:
        return sum(t.capacity for t in self.tables)

    def guests_seated(self) -> int:
        return sum(len(t.guests) for t in self.tables)

    def vip_tables(self) -> List[int]:
        return [t.table_id for t in self.tables if any(g.vip for g in t.guests)]

    def remaining_capacity(self) -> int:
        return self.total_capacity() - self.guests_seated()

    def stats(self) -> Dict:
        groups = {}
        for g in self.guests:
            groups[g.group] = groups.get(g.group, 0) + 1
        return {
            "event": self.event_name,
            "total_guests": len(self.guests),
            "seated": self.guests_seated(),
            "remaining_capacity": self.remaining_capacity(),
            "vip_tables": self.vip_tables(),
            "groups": groups,
        }

def run():
    sa = SeatingArranger(
        event_name="Corporate Dinner",
        guests=[
            Guest("Alice", "executive", vip=True),
            Guest("Bob", "executive", vip=True),
            Guest("Carol", "engineering"),
            Guest("Dave", "engineering"),
            Guest("Eve", "sales"),
            Guest("Frank", "sales"),
            Guest("Grace", "marketing"),
            Guest("Heidi", "marketing"),
        ],
        tables=[
            Table(1, 4, [Guest("Alice", "executive", vip=True), Guest("Bob", "executive", vip=True)]),
            Table(2, 4, [Guest("Carol", "engineering"), Guest("Dave", "engineering"), Guest("Eve", "sales")]),
            Table(3, 4, [Guest("Frank", "sales"), Guest("Grace", "marketing"), Guest("Heidi", "marketing")]),
        ]
    )
    print(sa.stats())

if __name__ == "__main__":
    run()
