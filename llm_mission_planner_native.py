"""Mission Planner — task sequencing, resource allocation, timeline, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import defaultdict

class TaskStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    BLOCKED = auto()

class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class MissionTask:
    id: str
    name: str
    duration: timedelta
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    earliest_start: Optional[datetime] = None
    latest_start: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None

@dataclass
class MissionResource:
    id: str
    name: str
    capacity: float = 1.0
    available_from: datetime = field(default_factory=lambda: datetime.min)
    available_until: datetime = field(default_factory=lambda: datetime.max)

@dataclass
class MissionTimeline:
    tasks: List[MissionTask] = field(default_factory=list)
    resources: List[MissionResource] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)

    def add_task(self, task: MissionTask) -> None:
        self.tasks.append(task)

    def add_resource(self, resource: MissionResource) -> None:
        self.resources.append(resource)

    def dependency_graph(self) -> Dict[str, List[str]]:
        graph = defaultdict(list)
        for task in self.tasks:
            for dep in task.dependencies:
                graph[task.id].append(dep)
        return graph

    def topological_sort(self) -> Optional[List[str]]:
        in_degree = {t.id: 0 for t in self.tasks}
        graph = defaultdict(list)
        for task in self.tasks:
            for dep in task.dependencies:
                graph[dep].append(task.id)
                in_degree[task.id] += 1
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            queue.sort(key=lambda tid: next(t.priority.value for t in self.tasks if t.id == tid))
            tid = queue.pop(0)
            order.append(tid)
            for neighbor in graph[tid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        if len(order) != len(self.tasks):
            return None  # cycle detected
        return order

    def schedule(self) -> Dict[str, Tuple[datetime, datetime]]:
        order = self.topological_sort()
        if order is None:
            return {}
        schedule = {}
        end_times = {}
        for tid in order:
            task = next(t for t in self.tasks if t.id == tid)
            earliest = self.start_time
            for dep in task.dependencies:
                if dep in end_times:
                    earliest = max(earliest, end_times[dep])
            if task.earliest_start:
                earliest = max(earliest, task.earliest_start)
            schedule[tid] = (earliest, earliest + task.duration)
            end_times[tid] = earliest + task.duration
            task.actual_start = earliest
            task.actual_end = end_times[tid]
        return schedule

    def critical_path(self) -> List[str]:
        order = self.topological_sort()
        if not order:
            return []
        earliest = {tid: timedelta(0) for tid in order}
        for tid in order:
            task = next(t for t in self.tasks if t.id == tid)
            for dep in task.dependencies:
                earliest[tid] = max(earliest[tid], earliest.get(dep, timedelta(0)) + next(t.duration for t in self.tasks if t.id == dep))
        total_duration = max(earliest[tid] + next(t.duration for t in self.tasks if t.id == tid) for tid in order)
        latest = {tid: total_duration for tid in order}
        for tid in reversed(order):
            task = next(t for t in self.tasks if t.id == tid)
            for t in self.tasks:
                if tid in t.dependencies:
                    latest[tid] = min(latest[tid], latest[t.id] - task.duration)
        critical = [tid for tid in order if earliest[tid] == latest[tid]]
        return critical

    def resource_utilization(self) -> Dict[str, float]:
        total_duration = max((t.actual_end - self.start_time).total_seconds() for t in self.tasks if t.actual_end)
        util = {}
        for r in self.resources:
            used = sum(t.duration.total_seconds() for t in self.tasks if r.id in t.resources and t.actual_start)
            util[r.id] = used / total_duration if total_duration > 0 else 0.0
        return util

    def stats(self) -> Dict[str, float]:
        schedule = self.schedule()
        if not schedule:
            return {}
        end = max(e for _, e in schedule.values())
        total = (end - self.start_time).total_seconds() / 3600
        return {
            "total_duration_hours": total,
            "task_count": len(self.tasks),
            "critical_path_length": len(self.critical_path()),
            "resource_count": len(self.resources)
        }

def run():
    timeline = MissionTimeline(start_time=datetime(2024, 6, 1, 8, 0, 0))
    timeline.add_resource(MissionResource("R1", "Astronaut A", capacity=1.0))
    timeline.add_resource(MissionResource("R2", "Rover", capacity=1.0))
    timeline.add_task(MissionTask("T1", "Pre-launch check", timedelta(hours=2), TaskPriority.CRITICAL, resources=["R1"]))
    timeline.add_task(MissionTask("T2", "Launch", timedelta(hours=1), TaskPriority.CRITICAL, dependencies=["T1"], resources=["R1"]))
    timeline.add_task(MissionTask("T3", "Transit", timedelta(days=2), TaskPriority.HIGH, dependencies=["T2"], resources=["R1"]))
    timeline.add_task(MissionTask("T4", "Landing", timedelta(hours=3), TaskPriority.CRITICAL, dependencies=["T3"], resources=["R1", "R2"]))
    timeline.add_task(MissionTask("T5", "Surface ops", timedelta(hours=8), TaskPriority.MEDIUM, dependencies=["T4"], resources=["R2"]))
    schedule = timeline.schedule()
    print(f"Scheduled {len(schedule)} tasks")
    for tid, (s, e) in schedule.items():
        print(f"  {tid}: {s.strftime('%m-%d %H:%M')} → {e.strftime('%m-%d %H:%M')}")
    print(f"Critical path: {timeline.critical_path()}")
    print(timeline.stats())

if __name__ == "__main__":
    run()
