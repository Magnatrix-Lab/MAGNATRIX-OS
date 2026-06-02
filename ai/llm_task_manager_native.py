"""Task Manager — Advanced task planning, decomposition, priority scheduling, and tracking.

Modul ini menyediakan:
- TaskPlanner untuk decompose goals into subtasks
- TaskScheduler untuk priority-based scheduling dengan deadlines
- TaskTracker untuk progress tracking dan dependency management
- TaskExecutor untuk execute tasks dengan retry dan timeout
- TaskManager untuk end-to-end task orchestration
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum, auto


class TaskPriority(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    BACKGROUND = 0


class TaskStatus(Enum):
    PENDING = auto()
    SCHEDULED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    BLOCKED = auto()
    RETRYING = auto()


@dataclass
class Subtask:
    """Single subtask in a decomposed plan."""
    subtask_id: str
    name: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    deadline: Optional[float] = None
    assigned_to: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TaskPlan:
    """Decomposed plan for a goal."""
    plan_id: str
    goal: str
    subtasks: List[Subtask] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class TaskPlanner:
    """Decompose goals into actionable subtasks."""

    def __init__(self):
        self._patterns: Dict[str, List[str]] = {
            "research": ["Identify sources", "Gather information", "Analyze data", "Synthesize findings", "Report results"],
            "development": ["Design architecture", "Implement core features", "Write tests", "Debug issues", "Deploy solution"],
            "analysis": ["Define metrics", "Collect data", "Process data", "Analyze patterns", "Draw conclusions"],
            "writing": ["Outline structure", "Draft content", "Review and edit", "Format output", "Publish"],
        }

    def plan(self, goal: str, priority: TaskPriority = TaskPriority.MEDIUM,
             planner_fn: Optional[Callable[[str], List[str]]] = None) -> TaskPlan:
        planner_fn = planner_fn or self._default_planner
        steps = planner_fn(goal)
        subtasks = []
        for i, step in enumerate(steps):
            subtasks.append(Subtask(
                subtask_id=f"st-{i}",
                name=step,
                description=f"Step {i+1}: {step}",
                priority=priority,
                dependencies=[f"st-{i-1}"] if i > 0 else [],
                estimated_duration=10.0,
            ))
        return TaskPlan(
            plan_id=str(uuid.uuid4())[:12],
            goal=goal,
            subtasks=subtasks,
        )

    def _default_planner(self, goal: str) -> List[str]:
        goal_lower = goal.lower()
        for pattern, steps in self._patterns.items():
            if pattern in goal_lower:
                return steps
        # Default decomposition
        return [f"Understand goal", f"Plan approach for: {goal[:50]}", f"Execute plan", f"Verify results"]


class TaskScheduler:
    """Priority-based task scheduling with deadlines."""

    def __init__(self):
        self._queue: List[Subtask] = []
        self._running: Dict[str, Subtask] = {}

    def schedule(self, subtasks: List[Subtask], max_concurrent: int = 3) -> List[Subtask]:
        # Sort by priority then deadline
        def sort_key(st: Subtask) -> Tuple[int, float, float]:
            return (-st.priority.value, st.deadline or float('inf'), st.created_at)
        queue = sorted(subtasks, key=sort_key)
        # Mark ready tasks
        for st in queue:
            if st.status == TaskStatus.PENDING:
                st.status = TaskStatus.SCHEDULED
        self._queue = queue
        return queue

    def get_ready(self) -> List[Subtask]:
        """Get subtasks whose dependencies are met."""
        ready = []
        completed_ids = set()
        for st in self._queue:
            if st.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                completed_ids.add(st.subtask_id)
        for st in self._queue:
            if st.status == TaskStatus.SCHEDULED:
                deps_met = all(d in completed_ids for d in st.dependencies)
                if deps_met:
                    ready.append(st)
        return ready

    def start_task(self, subtask_id: str) -> Optional[Subtask]:
        for st in self._queue:
            if st.subtask_id == subtask_id and st.status == TaskStatus.SCHEDULED:
                st.status = TaskStatus.RUNNING
                st.started_at = time.time()
                self._running[subtask_id] = st
                return st
        return None

    def complete_task(self, subtask_id: str, result: Any, success: bool = True) -> Optional[Subtask]:
        st = self._running.pop(subtask_id, None)
        if not st:
            for s in self._queue:
                if s.subtask_id == subtask_id:
                    st = s
                    break
        if st:
            st.completed_at = time.time()
            if success:
                st.status = TaskStatus.COMPLETED
                st.result = result
            else:
                st.status = TaskStatus.FAILED
                st.error = str(result)
                if st.retry_count < st.max_retries:
                    st.status = TaskStatus.RETRYING
                    st.retry_count += 1
            return st
        return None

    def get_stats(self) -> Dict[str, int]:
        return {
            "pending": sum(1 for s in self._queue if s.status == TaskStatus.PENDING),
            "scheduled": sum(1 for s in self._queue if s.status == TaskStatus.SCHEDULED),
            "running": sum(1 for s in self._queue if s.status == TaskStatus.RUNNING),
            "completed": sum(1 for s in self._queue if s.status == TaskStatus.COMPLETED),
            "failed": sum(1 for s in self._queue if s.status == TaskStatus.FAILED),
            "retrying": sum(1 for s in self._queue if s.status == TaskStatus.RETRYING),
        }


class TaskTracker:
    """Track progress and manage dependencies."""

    def __init__(self):
        self._plans: Dict[str, TaskPlan] = {}

    def track(self, plan: TaskPlan) -> None:
        self._plans[plan.plan_id] = plan

    def get_progress(self, plan_id: str) -> Dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            return {}
        total = len(plan.subtasks)
        completed = sum(1 for s in plan.subtasks if s.status == TaskStatus.COMPLETED)
        failed = sum(1 for s in plan.subtasks if s.status == TaskStatus.FAILED)
        return {
            "plan_id": plan_id,
            "goal": plan.goal,
            "total": total,
            "completed": completed,
            "failed": failed,
            "progress": completed / max(total, 1),
            "status": plan.status.name,
        }

    def get_blocked_tasks(self, plan_id: str) -> List[Subtask]:
        plan = self._plans.get(plan_id)
        if not plan:
            return []
        completed_ids = {s.subtask_id for s in plan.subtasks if s.status == TaskStatus.COMPLETED}
        blocked = []
        for st in plan.subtasks:
            if st.status == TaskStatus.PENDING or st.status == TaskStatus.SCHEDULED:
                deps_incomplete = [d for d in st.dependencies if d not in completed_ids]
                if deps_incomplete:
                    blocked.append(st)
        return blocked

    def get_critical_path(self, plan_id: str) -> List[Subtask]:
        """Get the longest dependency chain."""
        plan = self._plans.get(plan_id)
        if not plan:
            return []
        # Build adjacency
        adj: Dict[str, List[str]] = {}
        for st in plan.subtasks:
            adj[st.subtask_id] = []
        for st in plan.subtasks:
            for dep in st.dependencies:
                if dep in adj:
                    adj[dep].append(st.subtask_id)
        # Find longest path via DFS
        memo: Dict[str, int] = {}
        def dfs(node: str) -> int:
            if node in memo:
                return memo[node]
            max_len = 0
            for nxt in adj.get(node, []):
                max_len = max(max_len, 1 + dfs(nxt))
            memo[node] = max_len
            return max_len
        max_path = 0
        start_node = None
        for st in plan.subtasks:
            if not st.dependencies:
                pl = dfs(st.subtask_id)
                if pl > max_path:
                    max_path = pl
                    start_node = st.subtask_id
        # Reconstruct path
        path = []
        if start_node:
            current = start_node
            path.append(next(s for s in plan.subtasks if s.subtask_id == current))
            while adj.get(current):
                next_node = max(adj[current], key=lambda n: dfs(n))
                path.append(next(s for s in plan.subtasks if s.subtask_id == next_node))
                current = next_node
        return path


class TaskExecutor:
    """Execute tasks with retry and timeout."""

    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout

    def execute(self, subtask: Subtask, executor_fn: Optional[Callable[[Subtask], Any]] = None) -> Tuple[bool, Any]:
        executor_fn = executor_fn or self._default_executor
        try:
            result = executor_fn(subtask)
            return True, result
        except Exception as e:
            return False, str(e)

    def _default_executor(self, subtask: Subtask) -> Any:
        # Simulated: return task name as result
        time.sleep(0.01)
        return f"Completed: {subtask.name}"


class TaskManager:
    """End-to-end task orchestration."""

    def __init__(self, max_concurrent: int = 3):
        self.planner = TaskPlanner()
        self.scheduler = TaskScheduler()
        self.tracker = TaskTracker()
        self.executor = TaskExecutor()
        self.max_concurrent = max_concurrent
        self._history: List[TaskPlan] = []

    def create_plan(self, goal: str, priority: TaskPriority = TaskPriority.MEDIUM) -> TaskPlan:
        plan = self.planner.plan(goal, priority)
        self.tracker.track(plan)
        return plan

    def execute_plan(self, plan: TaskPlan, executor_fn: Optional[Callable[[Subtask], Any]] = None) -> TaskPlan:
        plan.status = TaskStatus.RUNNING
        self.scheduler.schedule(plan.subtasks, self.max_concurrent)

        while True:
            ready = self.scheduler.get_ready()
            if not ready:
                # Check if all done
                all_done = all(s.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED) for s in plan.subtasks)
                if all_done:
                    break
                break

            for st in ready[:self.max_concurrent]:
                self.scheduler.start_task(st.subtask_id)
                success, result = self.executor.execute(st, executor_fn)
                self.scheduler.complete_task(st.subtask_id, result, success)

        plan.status = TaskStatus.COMPLETED if all(s.status == TaskStatus.COMPLETED for s in plan.subtasks) else TaskStatus.FAILED
        plan.completed_at = time.time()
        self._history.append(plan)
        return plan

    def get_progress(self, plan_id: str) -> Dict[str, Any]:
        return self.tracker.get_progress(plan_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._history)
        completed = sum(1 for p in self._history if p.status == TaskStatus.COMPLETED)
        return {
            "total_plans": total,
            "completed": completed,
            "success_rate": completed / max(total, 1),
            "scheduler": self.scheduler.get_stats(),
        }

    def export_plan(self, plan_id: str, path: str) -> None:
        plan = self.tracker._plans.get(plan_id)
        if plan:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "plan_id": plan.plan_id,
                    "goal": plan.goal,
                    "status": plan.status.name,
                    "subtasks": [
                        {
                            "id": s.subtask_id,
                            "name": s.name,
                            "status": s.status.name,
                            "duration": (s.completed_at - s.started_at) if s.completed_at and s.started_at else 0,
                        }
                        for s in plan.subtasks
                    ],
                }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("TASK MANAGER DEMO")
    print("=" * 70)

    # 1. Create plan
    print("\n[1] Create Plan")
    manager = TaskManager(max_concurrent=2)
    plan = manager.create_plan("Build a REST API for a todo app", TaskPriority.HIGH)
    print(f"  Plan: {plan.plan_id}")
    print(f"  Goal: {plan.goal}")
    for st in plan.subtasks:
        print(f"    {st.subtask_id}: {st.name} (deps={st.dependencies})")

    # 2. Execute
    print("\n[2] Execute Plan")
    manager.execute_plan(plan)
    for st in plan.subtasks:
        print(f"    {st.name}: {st.status.name} -> {st.result}")

    # 3. Progress
    print(f"\n[3] Progress")
    print(f"  {manager.get_progress(plan.plan_id)}")

    # 4. Critical path
    print("\n[4] Critical Path")
    cp = manager.tracker.get_critical_path(plan.plan_id)
    print(f"  Length: {len(cp)}")
    for st in cp:
        print(f"    -> {st.name}")

    # 5. Multiple plans
    print("\n[5] Multiple Plans")
    plans = [
        manager.create_plan("Analyze sales data", TaskPriority.MEDIUM),
        manager.create_plan("Write documentation", TaskPriority.LOW),
        manager.create_plan("Fix critical bug", TaskPriority.CRITICAL),
    ]
    for p in plans:
        manager.execute_plan(p)
    print(f"  Total plans: {len(manager._history)}")
    print(f"  Stats: {manager.get_stats()}")

    # 6. Export
    print("\n[6] Export")
    manager.export_plan(plan.plan_id, "/tmp/task_plan.json")
    print("  Exported to /tmp/task_plan.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
