"""Vector Clocks & Logical Clocks — native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum, auto
import copy

@dataclass
class VectorClock:
    node_id: str
    clock: Dict[str, int] = field(default_factory=dict)

    def increment(self) -> "VectorClock":
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1
        return self

    def merge(self, other: "VectorClock") -> "VectorClock":
        merged = copy.deepcopy(self)
        for k, v in other.clock.items():
            merged.clock[k] = max(merged.clock.get(k, 0), v)
        return merged

    def compare(self, other: "VectorClock") -> Optional[str]:
        gt = any(self.clock.get(k, 0) > other.clock.get(k, 0) for k in set(self.clock) | set(other.clock))
        lt = any(self.clock.get(k, 0) < other.clock.get(k, 0) for k in set(self.clock) | set(other.clock))
        if gt and lt:
            return "CONCURRENT"
        if gt:
            return "AFTER"
        if lt:
            return "BEFORE"
        return "EQUAL"

    def to_dict(self) -> Dict:
        return {"node": self.node_id, "clock": dict(self.clock)}

@dataclass
class LogicalClock:
    node_id: str
    time: int = 0

    def tick(self) -> int:
        self.time += 1
        return self.time

    def update(self, received_time: int) -> int:
        self.time = max(self.time, received_time) + 1
        return self.time

    def to_dict(self) -> Dict:
        return {"node": self.node_id, "time": self.time}

class VectorClockSystem:
    def __init__(self):
        self.clocks: Dict[str, VectorClock] = {}
        self.events: List[Dict] = []

    def add_node(self, node_id: str):
        self.clocks[node_id] = VectorClock(node_id)

    def event(self, node_id: str, event_name: str) -> VectorClock:
        if node_id not in self.clocks:
            self.add_node(node_id)
        self.clocks[node_id].increment()
        self.events.append({"node": node_id, "event": event_name, "clock": self.clocks[node_id].to_dict()})
        return self.clocks[node_id]

    def send(self, from_id: str, to_id: str, event_name: str) -> Tuple[VectorClock, VectorClock]:
        if from_id not in self.clocks:
            self.add_node(from_id)
        if to_id not in self.clocks:
            self.add_node(to_id)
        self.clocks[from_id].increment()
        self.clocks[to_id] = self.clocks[to_id].merge(self.clocks[from_id])
        self.clocks[to_id].increment()
        self.events.append({"from": from_id, "to": to_id, "event": event_name, "clocks": {from_id: self.clocks[from_id].to_dict(), to_id: self.clocks[to_id].to_dict()}})
        return self.clocks[from_id], self.clocks[to_id]

    def stats(self) -> Dict:
        return {"nodes": list(self.clocks.keys()), "events": len(self.events), "clocks": {k: v.to_dict() for k, v in self.clocks.items()}}

def run():
    vcs = VectorClockSystem()
    vcs.event("A", "init")
    vcs.event("B", "init")
    vcs.send("A", "B", "msg1")
    vcs.event("A", "work")
    vcs.send("B", "A", "msg2")
    print(vcs.stats())
    c1 = vcs.clocks["A"]
    c2 = vcs.clocks["B"]
    print("A vs B:", c1.compare(c2))

if __name__ == "__main__":
    run()
