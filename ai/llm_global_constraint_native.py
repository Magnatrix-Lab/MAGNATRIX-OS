"""Global Constraint - All-different, cumulative for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto

@dataclass
class GlobalConstraint:

    def all_different(self, values: List[int]) -> bool:
        return len(values) == len(set(values))

    def cumulative(self, starts: List[float], durations: List[float], demands: List[float], capacity: float) -> bool:
        if not starts: return True
        end_time = max(starts[i] + durations[i] for i in range(len(starts)))
        for t in range(int(end_time) + 1):
            total = sum(demands[i] for i in range(len(starts)) if starts[i] <= t < starts[i] + durations[i])
            if total > capacity: return False
        return True

    def element(self, index: int, values: List[int], result: int) -> bool:
        if 0 <= index < len(values):
            return values[index] == result
        return False

    def stats(self, constraint_type: str, **kwargs) -> dict:
        if constraint_type == "all_different":
            return {"type": constraint_type, "satisfied": self.all_different(kwargs.get("values", []))}
        elif constraint_type == "cumulative":
            return {"type": constraint_type, "satisfied": self.cumulative(kwargs.get("starts", []), kwargs.get("durations", []), kwargs.get("demands", []), kwargs.get("capacity", 0))}
        return {"type": constraint_type}

def run():
    gc = GlobalConstraint()
    print("All different [1,2,3]:", gc.all_different([1, 2, 3]))
    print("All different [1,2,2]:", gc.all_different([1, 2, 2]))
    print("Cumulative:", gc.cumulative([0, 2, 4], [3, 3, 3], [1, 1, 1], 2))
    print("Stats:", gc.stats("all_different", values=[1, 2, 3]))

if __name__ == "__main__": run()
