"""Planning Engine — Hierarchical Task Network (HTN) planner, goal decomposition, plan execution, replanning.

Modul ini menyediakan:
- HTNPlanner untuk dekomposisi task hierarkis
- GoalDecomposer untuk breaking down complex goals
- PlanExecutor untuk eksekusi plan dengan monitoring
- ReplanningEngine untuk handling failures dengan plan repair
- PlanLibrary untuk pre-built plan templates

Arsitektur: Goal → Decompose → Plan → Execute → Monitor → (Success / Replan)
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class PlanStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    REPLANNING = auto()
    CANCELLED = auto()


class TaskType(Enum):
    PRIMITIVE = auto()
    COMPOUND = auto()


@dataclass
class Task:
    """Task in a plan."""
    task_id: str
    name: str
    task_type: TaskType
    preconditions: List[Callable[[Dict[str, Any]], bool]] = field(default_factory=list)
    effects: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = field(default_factory=list)
    subtasks: List[Task] = field(default_factory=list)
    executor: Optional[Callable[[Dict[str, Any]], Any]] = None
    cost: float = 1.0
    duration_estimate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_primitive(self) -> bool:
        return self.task_type == TaskType.PRIMITIVE

    def is_compound(self) -> bool:
        return self.task_type == TaskType.COMPOUND


@dataclass
class Plan:
    """Execution plan."""
    plan_id: str
    goal: str
    tasks: List[Task] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    world_state: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    total_cost: float = 0.0
    execution_trace: List[Dict[str, Any]] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)
        self.total_cost += task.cost


@dataclass
class ExecutionResult:
    """Result of executing a task."""
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    new_state: Dict[str, Any] = field(default_factory=dict)


class GoalDecomposer:
    """Decompose high-level goals into actionable tasks."""

    def __init__(self):
        self._methods: Dict[str, List[Callable[[Dict[str, Any]], List[Task]]]] = {}

    def add_method(self, goal_pattern: str, method: Callable[[Dict[str, Any]], List[Task]]) -> None:
        self._methods.setdefault(goal_pattern, []).append(method)

    def decompose(self, goal: str, context: Dict[str, Any]) -> List[Task]:
        for pattern, methods in self._methods.items():
            if pattern in goal.lower():
                for method in methods:
                    try:
                        tasks = method(context)
                        if tasks:
                            return tasks
                    except Exception:
                        continue
        # Default: create single primitive task
        return [Task(
            task_id=str(uuid.uuid4())[:12],
            name=goal,
            task_type=TaskType.PRIMITIVE,
            executor=lambda ctx: f"Executed: {goal}"
        )]


class HTNPlanner:
    """Hierarchical Task Network planner."""

    def __init__(self, decomposer: GoalDecomposer):
        self.decomposer = decomposer

    def plan(self, goal: str, initial_state: Dict[str, Any]) -> Plan:
        plan = Plan(
            plan_id=str(uuid.uuid4())[:12],
            goal=goal,
            world_state=dict(initial_state)
        )
        tasks = self.decomposer.decompose(goal, initial_state)
        for task in tasks:
            plan.add_task(task)
            if task.is_compound():
                self._expand(plan, task, initial_state)
        return plan

    def _expand(self, plan: Plan, task: Task, state: Dict[str, Any]) -> None:
        subtasks = self.decomposer.decompose(task.name, state)
        task.subtasks = subtasks
        for st in subtasks:
            plan.add_task(st)
            if st.is_compound():
                self._expand(plan, st, state)

    def get_all_primitive_tasks(self, plan: Plan) -> List[Task]:
        primitives = []
        for task in plan.tasks:
            if task.is_primitive():
                primitives.append(task)
            else:
                primitives.extend(self._get_primitives(task))
        return primitives

    def _get_primitives(self, task: Task) -> List[Task]:
        primitives = []
        for st in task.subtasks:
            if st.is_primitive():
                primitives.append(st)
            else:
                primitives.extend(self._get_primitives(st))
        return primitives


class PlanExecutor:
    """Execute plans with state tracking and monitoring."""

    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._callbacks: List[Callable[[str, ExecutionResult], None]] = []

    def execute(self, plan: Plan, state: Optional[Dict[str, Any]] = None) -> Plan:
        plan.status = PlanStatus.RUNNING
        plan.started_at = time.time()
        if state:
            plan.world_state.update(state)

        primitives = self._get_execution_order(plan)
        for task in primitives:
            # Check preconditions
            if task.preconditions and not all(p(plan.world_state) for p in task.preconditions):
                result = ExecutionResult(task.task_id, False, error="Preconditions not met")
                plan.execution_trace.append({"task": task.task_id, "result": result.__dict__})
                plan.status = PlanStatus.FAILED
                for cb in self._callbacks:
                    cb(plan.plan_id, result)
                return plan

            # Execute
            start = time.time()
            try:
                if task.executor:
                    output = task.executor(plan.world_state)
                else:
                    output = None
                duration = time.time() - start

                # Apply effects
                for effect in task.effects:
                    plan.world_state = effect(plan.world_state)

                result = ExecutionResult(task.task_id, True, output, duration=duration, new_state=dict(plan.world_state))
            except Exception as e:
                result = ExecutionResult(task.task_id, False, error=str(e), duration=time.time() - start)

            plan.execution_trace.append({"task": task.task_id, "result": result.__dict__})
            for cb in self._callbacks:
                cb(plan.plan_id, result)

            if not result.success:
                plan.status = PlanStatus.FAILED
                return plan

        plan.status = PlanStatus.COMPLETED
        plan.completed_at = time.time()
        return plan

    def _get_execution_order(self, plan: Plan) -> List[Task]:
        # Simple sequential execution for now
        return [t for t in plan.tasks if t.is_primitive()]

    def on_execute(self, callback: Callable[[str, ExecutionResult], None]) -> None:
        self._callbacks.append(callback)

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)

    def save_plan(self, plan: Plan) -> None:
        self._plans[plan.plan_id] = plan


class ReplanningEngine:
    """Handle plan failures by replanning."""

    def __init__(self, planner: HTNPlanner, executor: PlanExecutor):
        self.planner = planner
        self.executor = executor
        self._replan_count: Dict[str, int] = {}
        self._max_replans: int = 3

    def replan(self, failed_plan: Plan, failure_reason: str) -> Optional[Plan]:
        count = self._replan_count.get(failed_plan.plan_id, 0)
        if count >= self._max_replans:
            return None
        self._replan_count[failed_plan.plan_id] = count + 1

        # Adjust state based on what was accomplished
        new_state = dict(failed_plan.world_state)
        new_state["failure_reason"] = failure_reason
        new_state["replan_attempt"] = count + 1

        new_plan = self.planner.plan(failed_plan.goal, new_state)
        new_plan.status = PlanStatus.REPLANNING
        return new_plan

    def execute_with_fallback(self, goal: str, initial_state: Dict[str, Any]) -> Tuple[Plan, int]:
        plan = self.planner.plan(goal, initial_state)
        replan_count = 0
        while True:
            result = self.executor.execute(plan, dict(initial_state))
            if result.status == PlanStatus.COMPLETED:
                return result, replan_count
            if replan_count >= self._max_replans:
                return result, replan_count
            new_plan = self.replan(result, "Execution failed")
            if not new_plan:
                return result, replan_count
            plan = new_plan
            replan_count += 1


class PlanLibrary:
    """Pre-built plan templates."""

    @staticmethod
    def travel_plan(destination: str = "{destination}") -> List[Task]:
        return [
            Task("book-flight", "Book flight", TaskType.PRIMITIVE, executor=lambda ctx: f"Booked flight to {destination}"),
            Task("book-hotel", "Book hotel", TaskType.PRIMITIVE, executor=lambda ctx: f"Booked hotel in {destination}"),
            Task("pack-luggage", "Pack luggage", TaskType.PRIMITIVE, executor=lambda ctx: "Packed luggage"),
        ]

    @staticmethod
    def research_plan(topic: str = "{topic}") -> List[Task]:
        return [
            Task("gather-sources", "Gather sources", TaskType.PRIMITIVE, executor=lambda ctx: f"Gathered sources on {topic}"),
            Task("read-sources", "Read sources", TaskType.PRIMITIVE, executor=lambda ctx: "Read and summarized sources"),
            Task("write-report", "Write report", TaskType.PRIMITIVE, executor=lambda ctx: f"Wrote report on {topic}"),
        ]

    @staticmethod
    def code_plan(project: str = "{project}") -> List[Task]:
        return [
            Task("design", "Design architecture", TaskType.PRIMITIVE, executor=lambda ctx: "Designed architecture"),
            Task("implement", "Implement code", TaskType.PRIMITIVE, executor=lambda ctx: f"Implemented {project}"),
            Task("test", "Write tests", TaskType.PRIMITIVE, executor=lambda ctx: "Tests passing"),
        ]


class PlanningEngine:
    """End-to-end planning engine."""

    def __init__(self):
        self.decomposer = GoalDecomposer()
        self.planner = HTNPlanner(self.decomposer)
        self.executor = PlanExecutor()
        self.replanner = ReplanningEngine(self.planner, self.executor)
        self.library = PlanLibrary()
        self._setup_default_methods()

    def _setup_default_methods(self) -> None:
        self.decomposer.add_method("travel", lambda ctx: self.library.travel_plan())
        self.decomposer.add_method("research", lambda ctx: self.library.research_plan())
        self.decomposer.add_method("code", lambda ctx: self.library.code_plan())
        self.decomposer.add_method("build", lambda ctx: self.library.code_plan())

    def create_plan(self, goal: str, initial_state: Optional[Dict[str, Any]] = None) -> Plan:
        return self.planner.plan(goal, initial_state or {})

    def execute(self, plan: Plan) -> Plan:
        return self.executor.execute(plan)

    def execute_with_replanning(self, goal: str, initial_state: Optional[Dict[str, Any]] = None) -> Tuple[Plan, int]:
        return self.replanner.execute_with_fallback(goal, initial_state or {})

    def add_method(self, goal_pattern: str, method: Callable[[Dict[str, Any]], List[Task]]) -> None:
        self.decomposer.add_method(goal_pattern, method)

    def get_primitive_count(self, plan: Plan) -> int:
        return len(self.planner.get_all_primitive_tasks(plan))


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("PLANNING ENGINE DEMO")
    print("=" * 70)

    engine = PlanningEngine()

    # 1. Create plan
    print("\n[1] Create Plan")
    plan = engine.create_plan("Travel to Paris", {"budget": 1000})
    print(f"  Plan: {plan.plan_id}")
    print(f"  Goal: {plan.goal}")
    print(f"  Tasks: {len(plan.tasks)}")
    print(f"  Primitive tasks: {engine.get_primitive_count(plan)}")
    print(f"  Cost: {plan.total_cost}")

    # 2. Execute plan
    print("\n[2] Execute Plan")
    result = engine.execute(plan)
    print(f"  Status: {result.status.name}")
    print(f"  World state: {result.world_state}")
    for trace in result.execution_trace:
        res = trace["result"]
        print(f"    {trace['task']}: {'✅' if res['success'] else '❌'} {str(res['output'])[:50]}")

    # 3. Research plan
    print("\n[3] Research Plan")
    plan2 = engine.create_plan("Research quantum computing", {})
    result2 = engine.execute(plan2)
    print(f"  Status: {result2.status.name}")
    print(f"  Trace entries: {len(result2.execution_trace)}")

    # 4. Custom plan with preconditions
    print("\n[4] Plan with Preconditions")
    custom_engine = PlanningEngine()
    task = Task(
        task_id="deploy",
        name="Deploy to production",
        task_type=TaskType.PRIMITIVE,
        preconditions=[lambda state: state.get("tests_passed", False)],
        executor=lambda ctx: "Deployed successfully"
    )
    custom_engine.decomposer.add_method("deploy", lambda ctx: [task])
    plan3 = custom_engine.create_plan("deploy", {"tests_passed": False})
    result3 = custom_engine.execute(plan3)
    print(f"  With tests_passed=False: {result3.status.name}")
    plan4 = custom_engine.create_plan("deploy", {"tests_passed": True})
    result4 = custom_engine.execute(plan4)
    print(f"  With tests_passed=True: {result4.status.name}")

    # 5. Replanning
    print("\n[5] Replanning")
    failing_engine = PlanningEngine()
    failing_task = Task(
        task_id="fail",
        name="Always fails",
        task_type=TaskType.PRIMITIVE,
        executor=lambda ctx: (_ for _ in ()).throw(RuntimeError("Simulated failure"))
    )
    failing_engine.decomposer.add_method("fail", lambda ctx: [failing_task])
    plan5, replans = failing_engine.execute_with_replanning("fail")
    print(f"  Final status: {plan5.status.name}")
    print(f"  Replan attempts: {replans}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
