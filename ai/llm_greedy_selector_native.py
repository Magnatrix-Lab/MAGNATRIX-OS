"""Greedy Selector - Greedy algorithms for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum, auto

class GreedyProblem(Enum):
    ACTIVITY = auto(); HUFFMAN = auto(); INTERVAL = auto()

@dataclass
class GreedySelector:
    problem_type: GreedyProblem = GreedyProblem.ACTIVITY

    def activity_selection(self, activities: List[Tuple[int,int]]) -> List[int]:
        sorted_acts = sorted(enumerate(activities), key=lambda x: x[1][1])
        selected = [sorted_acts[0][0]]
        last_end = sorted_acts[0][1][1]
        for idx, (s, e) in sorted_acts[1:]:
            if s >= last_end: selected.append(idx); last_end = e
        return selected

    def interval_cover(self, intervals: List[Tuple[int,int]]) -> List[int]:
        sorted_int = sorted(enumerate(intervals), key=lambda x: x[1][1])
        points = []; covered = set()
        for idx, (s, e) in sorted_int:
            if not any(s <= p <= e for p in points):
                points.append(e)
        return points

    def solve(self, *args):
        if self.problem_type == GreedyProblem.ACTIVITY: return self.activity_selection(args[0])
        if self.problem_type == GreedyProblem.INTERVAL: return self.interval_cover(args[0])
        return []

    def stats(self, *args) -> dict:
        return {"problem": self.problem_type.name, "result": self.solve(*args)}

def run():
    gs = GreedySelector(GreedyProblem.ACTIVITY)
    acts = [(1,4),(3,5),(0,6),(5,7),(3,8),(5,9),(6,10),(8,11),(8,12),(2,13),(12,14)]
    print("Selected:", gs.solve(acts))
    print("Stats:", gs.stats(acts))

if __name__ == "__main__": run()
