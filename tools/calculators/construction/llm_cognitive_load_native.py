"""Cognitive Load Calculator — intrinsic, extraneous, germane, task demand, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class CognitiveLoad:
    elements: int = 0
    interactions: int = 0
    time_pressure: float = 0.0
    expertise: float = 5.0

    def intrinsic_load(self) -> float:
        return min(10, self.elements * self.interactions / 10)

    def extraneous_load(self) -> float:
        return self.time_pressure * 2

    def germane_load(self) -> float:
        return min(10, self.expertise * 0.5)

    def total_load(self) -> float:
        return self.intrinsic_load() + self.extraneous_load() + self.germane_load()

    def overload(self) -> bool:
        return self.total_load() > 10

    def optimize(self, task: Dict) -> Dict:
        return {
            "chunk": task.get("elements", 0) > 5,
            "reduce_interactions": task.get("interactions", 0) > 3,
            "extend_time": self.time_pressure > 3,
        }

    def stats(self) -> Dict:
        return {
            "intrinsic": round(self.intrinsic_load(), 2),
            "extraneous": round(self.extraneous_load(), 2),
            "germane": round(self.germane_load(), 2),
            "total": round(self.total_load(), 2),
            "overload": self.overload()
        }

def run():
    cl = CognitiveLoad(elements=7, interactions=4, time_pressure=2, expertise=6)
    print(cl.stats())
    print("Optimize:", cl.optimize({"elements": 7, "interactions": 4}))

if __name__ == "__main__":
    run()
