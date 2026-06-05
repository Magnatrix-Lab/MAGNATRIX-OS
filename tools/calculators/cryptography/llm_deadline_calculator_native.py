"""Deadline Calculator — business days, critical path, slack, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
import time

@dataclass
class TaskNode:
    task_id: str
    duration: float
    dependencies: List[str] = field(default_factory=list)
    earliest_start: float = 0.0
    earliest_finish: float = 0.0
    latest_start: float = 0.0
    latest_finish: float = 0.0
    slack: float = 0.0

class DeadlineCalculator:
    def __init__(self, holidays: List[float] = None):
        self.holidays = set(holidays or [])

    def add_business_days(self, start: float, days: int) -> float:
        current = start
        count = 0
        while count < days:
            current += 86400
            t = time.localtime(current)
            if t.tm_wday < 5 and current not in self.holidays:
                count += 1
        return current

    def calculate_critical_path(self, tasks: Dict[str, TaskNode]) -> List[str]:
        # Forward pass
        for tid in tasks:
            task = tasks[tid]
            max_finish = 0
            for dep in task.dependencies:
                if dep in tasks:
                    max_finish = max(max_finish, tasks[dep].earliest_finish)
            task.earliest_start = max_finish
            task.earliest_finish = max_finish + task.duration
        # Backward pass
        max_finish = max(t.earliest_finish for t in tasks.values()) if tasks else 0
        for tid in list(tasks.keys()):
            task = tasks[tid]
            task.latest_finish = max_finish
            task.latest_start = max_finish - task.duration
        # Slack
        for task in tasks.values():
            task.slack = task.latest_start - task.earliest_start
        # Critical path
        critical = [tid for tid, t in tasks.items() if t.slack == 0]
        return critical

    def stats(self) -> Dict:
        return {"holidays": len(self.holidays)}

def run():
    calc = DeadlineCalculator()
    tasks = {
        "A": TaskNode("A", 3, []),
        "B": TaskNode("B", 2, ["A"]),
        "C": TaskNode("C", 4, ["A"]),
        "D": TaskNode("D", 1, ["B", "C"]),
    }
    cp = calc.calculate_critical_path(tasks)
    print("Critical path:", cp)
    for t in tasks.values():
        print(f"{t.task_id}: ES={t.earliest_start}, EF={t.earliest_finish}, slack={t.slack}")
    print(calc.stats())

if __name__ == "__main__":
    run()
