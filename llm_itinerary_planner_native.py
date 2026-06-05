"""Itinerary Planner — route, time, budget, constraints, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import heapq

@dataclass
class Activity:
    name: str
    duration: float
    cost: float
    score: float
    open_time: float
    close_time: float

class ItineraryPlanner:
    def __init__(self):
        self.activities: List[Activity] = []

    def add_activity(self, a: Activity):
        self.activities.append(a)

    def knapsack_plan(self, budget: float, max_time: float) -> List[Activity]:
        n = len(self.activities)
        dp = [[0.0] * (int(max_time) + 1) for _ in range(int(budget) + 1)]
        chosen = [[[] for _ in range(int(max_time) + 1)] for _ in range(int(budget) + 1)]
        for i, a in enumerate(self.activities):
            for b in range(int(budget), int(a.cost) - 1, -1):
                for t in range(int(max_time), int(a.duration) - 1, -1):
                    if dp[b - int(a.cost)][t - int(a.duration)] + a.score > dp[b][t]:
                        dp[b][t] = dp[b - int(a.cost)][t - int(a.duration)] + a.score
                        chosen[b][t] = chosen[b - int(a.cost)][t - int(a.duration)] + [a]
        return chosen[int(budget)][int(max_time)]

    def schedule(self, start_time: float, end_time: float) -> List[Activity]:
        available = [a for a in self.activities if a.open_time <= start_time and a.close_time >= end_time]
        available.sort(key=lambda a: a.score / a.duration, reverse=True)
        result = []
        current = start_time
        for a in available:
            if current + a.duration <= end_time:
                result.append(a)
                current += a.duration
        return result

    def stats(self) -> Dict:
        return {"activities": len(self.activities), "total_score": sum(a.score for a in self.activities)}

def run():
    ip = ItineraryPlanner()
    ip.add_activity(Activity("Museum", 2, 20, 8, 9, 17))
    ip.add_activity(Activity("Park", 3, 0, 7, 6, 20))
    ip.add_activity(Activity("Restaurant", 1.5, 30, 9, 11, 22))
    plan = ip.schedule(9, 18)
    print([a.name for a in plan])
    print(ip.stats())

if __name__ == "__main__":
    run()
