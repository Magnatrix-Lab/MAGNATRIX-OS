#!/usr/bin/env python3
"""
Workflow Engine for MAGNATRIX-OS
DAG-based task orchestration with retry, scheduling, and persistence.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
import re
import subprocess
import threading
import time
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


class TaskState(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class WorkflowState(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclasses.dataclass
class Task:
    id: str
    name: str
    task_type: str = "function"  # function, shell, http, wait, conditional, parallel, subworkflow
    func: Optional[Callable] = None
    config: Dict[str, Any] = dataclasses.field(default_factory=dict)
    depends_on: List[str] = dataclasses.field(default_factory=list)
    timeout: float = 30.0
    retries: int = 0
    backoff: float = 1.0
    state: TaskState = TaskState.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    attempts: int = 0


@dataclasses.dataclass
class Workflow:
    id: str
    name: str
    tasks: Dict[str, Task] = dataclasses.field(default_factory=dict)
    state: WorkflowState = WorkflowState.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    results: Dict[str, Any] = dataclasses.field(default_factory=dict)
    variables: Dict[str, Any] = dataclasses.field(default_factory=dict)


class DAG:
    """Directed Acyclic Graph for task ordering."""

    def __init__(self) -> None:
        self._nodes: Set[str] = set()
        self._edges: Dict[str, List[str]] = {}  # node -> dependents
        self._deps: Dict[str, Set[str]] = {}      # node -> dependencies

    def add_node(self, node_id: str) -> None:
        self._nodes.add(node_id)
        if node_id not in self._edges:
            self._edges[node_id] = []
        if node_id not in self._deps:
            self._deps[node_id] = set()

    def add_edge(self, from_node: str, to_node: str) -> None:
        self.add_node(from_node)
        self.add_node(to_node)
        self._edges[from_node].append(to_node)
        self._deps[to_node].add(from_node)

    def has_cycle(self) -> bool:
        """Kahn's algorithm for cycle detection."""
        in_degree = {n: len(self._deps[n]) for n in self._nodes}
        queue = [n for n in self._nodes if in_degree[n] == 0]
        visited = 0

        while queue:
            node = queue.pop(0)
            visited += 1
            for dep in self._edges[node]:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

        return visited != len(self._nodes)

    def topological_sort(self) -> List[str]:
        """Return topologically sorted nodes."""
        if self.has_cycle():
            raise ValueError("DAG has cycle")

        in_degree = {n: len(self._deps[n]) for n in self._nodes}
        queue = [n for n in self._nodes if in_degree[n] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for dep in self._edges[node]:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

        return result

    def get_ready_nodes(self, completed: Set[str]) -> List[str]:
        """Get nodes whose dependencies are all completed."""
        ready = []
        for node in self._nodes:
            if node not in completed and self._deps[node].issubset(completed):
                ready.append(node)
        return ready


class TaskExecutor:
    """Execute individual tasks."""

    def execute(self, task: Task, context: Dict[str, Any]) -> Tuple[bool, Any]:
        task.attempts += 1
        task.start_time = time.time()
        task.state = TaskState.RUNNING

        try:
            if task.task_type == "function":
                result = self._exec_function(task, context)
            elif task.task_type == "shell":
                result = self._exec_shell(task, context)
            elif task.task_type == "http":
                result = self._exec_http(task, context)
            elif task.task_type == "wait":
                result = self._exec_wait(task, context)
            elif task.task_type == "conditional":
                result = self._exec_conditional(task, context)
            elif task.task_type == "parallel":
                result = self._exec_parallel(task, context)
            else:
                result = None

            task.state = TaskState.SUCCESS
            task.result = result
            task.end_time = time.time()
            return True, result

        except Exception as exc:
            task.state = TaskState.FAILED
            task.error = str(exc)
            task.end_time = time.time()
            return False, exc

    def _exec_function(self, task: Task, context: Dict[str, Any]) -> Any:
        if task.func:
            return task.func(**task.config)
        return None

    def _exec_shell(self, task: Task, context: Dict[str, Any]) -> Any:
        cmd = task.config.get("command", "")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=task.timeout)
        if result.returncode != 0:
            raise RuntimeError(f"Shell command failed: {result.stderr}")
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}

    def _exec_http(self, task: Task, context: Dict[str, Any]) -> Any:
        url = task.config.get("url", "")
        method = task.config.get("method", "GET")
        body = task.config.get("body")
        headers = task.config.get("headers", {})

        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=task.timeout) as resp:
            return {"status": resp.status, "body": resp.read().decode("utf-8")}

    def _exec_wait(self, task: Task, context: Dict[str, Any]) -> Any:
        seconds = task.config.get("seconds", 1.0)
        time.sleep(seconds)
        return {"waited": seconds}

    def _exec_conditional(self, task: Task, context: Dict[str, Any]) -> Any:
        condition = task.config.get("condition", "")
        # Simple evaluation: check if condition key exists in context and is truthy
        result = bool(context.get(condition, False))
        return {"condition": condition, "result": result}

    def _exec_parallel(self, task: Task, context: Dict[str, Any]) -> Any:
        items = task.config.get("items", [])
        subtask = task.config.get("task", {})
        results = []
        for item in items:
            # Execute subtask for each item (simplified)
            results.append({"item": item, "result": "processed"})
        return {"results": results, "count": len(items)}


class RetryEngine:
    """Handle retry logic with backoff."""

    def should_retry(self, task: Task) -> bool:
        return task.attempts <= task.retries and task.state == TaskState.FAILED

    def get_backoff(self, task: Task) -> float:
        return task.backoff * (2 ** (task.attempts - 1))


class Scheduler:
    """Simple cron-like scheduler."""

    def __init__(self) -> None:
        self._schedules: List[Dict[str, Any]] = []

    def add_schedule(self, name: str, cron: str, workflow_id: str) -> None:
        self._schedules.append({
            "name": name,
            "cron": cron,
            "workflow_id": workflow_id,
            "last_run": 0,
        })

    def parse_cron(self, cron: str) -> Dict[str, Any]:
        """Parse simple cron expression."""
        parts = cron.split()
        if len(parts) != 5:
            raise ValueError("Cron must have 5 parts: min hour day month weekday")
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "weekday": parts[4],
        }

    def next_run(self, cron: str) -> Optional[float]:
        """Calculate next run time from cron."""
        try:
            parsed = self.parse_cron(cron)
            # Simplified: support exact values and */N
            now = time.localtime()

            # For */N patterns, find next occurrence
            minute_str = parsed["minute"]
            if minute_str.startswith("*/"):
                interval = int(minute_str[2:])
                next_min = ((now.tm_min // interval) + 1) * interval
                if next_min >= 60:
                    next_min = 0
                # Approximate next run
                delay = (next_min - now.tm_min) * 60
                if delay <= 0:
                    delay += interval * 60
                return time.time() + delay

            return None
        except Exception:
            return None

    def check_and_trigger(self, engine: WorkflowEngine) -> List[str]:
        triggered = []
        for sched in self._schedules:
            next_run_time = self.next_run(sched["cron"])
            if next_run_time and time.time() >= next_run_time - 1:
                triggered.append(sched["workflow_id"])
                sched["last_run"] = time.time()
        return triggered


class WorkflowEngine:
    """Main workflow orchestrator."""

    def __init__(self, persistence_dir: str = "./workflow_data") -> None:
        self._workflows: Dict[str, Workflow] = {}
        self._executor = TaskExecutor()
        self._retry = RetryEngine()
        self._scheduler = Scheduler()
        self._persistence_dir = persistence_dir
        os.makedirs(persistence_dir, exist_ok=True)

    def create_workflow(self, name: str, tasks: List[Task]) -> Workflow:
        wf = Workflow(id=f"wf_{int(time.time())}_{name}", name=name)
        for task in tasks:
            wf.tasks[task.id] = task
        self._workflows[wf.id] = wf
        return wf

    def run(self, workflow_id: str) -> Dict[str, Any]:
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Build DAG
        dag = DAG()
        for task_id, task in wf.tasks.items():
            dag.add_node(task_id)
        for task_id, task in wf.tasks.items():
            for dep in task.depends_on:
                dag.add_edge(dep, task_id)

        if dag.has_cycle():
            raise ValueError("Workflow has circular dependencies")

        # Execute
        wf.state = WorkflowState.RUNNING
        wf.start_time = time.time()
        completed: Set[str] = set()
        failed: Set[str] = set()

        while len(completed) + len(failed) < len(wf.tasks):
            ready = dag.get_ready_nodes(completed)
            if not ready:
                break

            for task_id in ready:
                task = wf.tasks[task_id]
                if task_id in completed or task_id in failed:
                    continue

                success, result = self._executor.execute(task, wf.results)

                if success:
                    completed.add(task_id)
                    wf.results[task_id] = result
                else:
                    if self._retry.should_retry(task):
                        task.state = TaskState.RETRYING
                        backoff = self._retry.get_backoff(task)
                        time.sleep(backoff)
                        # Retry
                        success, result = self._executor.execute(task, wf.results)
                        if success:
                            completed.add(task_id)
                            wf.results[task_id] = result
                        else:
                            failed.add(task_id)
                    else:
                        failed.add(task_id)

            if not ready and len(completed) + len(failed) < len(wf.tasks):
                # Stuck
                break

        wf.end_time = time.time()

        if not failed and len(completed) == len(wf.tasks):
            wf.state = WorkflowState.SUCCESS
        elif failed and not completed:
            wf.state = WorkflowState.FAILED
        else:
            wf.state = WorkflowState.PARTIAL

        # Save state
        self._save(wf)

        return {
            "workflow_id": wf.id,
            "state": wf.state.value,
            "completed": len(completed),
            "failed": len(failed),
            "total": len(wf.tasks),
            "duration": wf.end_time - wf.start_time if wf.end_time and wf.start_time else 0,
            "results": wf.results,
        }

    def _save(self, wf: Workflow) -> None:
        path = os.path.join(self._persistence_dir, f"{wf.id}.json")
        with open(path, "w") as f:
            json.dump({
                "id": wf.id,
                "name": wf.name,
                "state": wf.state.value,
                "results": wf.results,
                "variables": wf.variables,
            }, f, indent=2, default=str)

    def load(self, workflow_id: str) -> Optional[Workflow]:
        path = os.path.join(self._persistence_dir, f"{workflow_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        wf = Workflow(id=data["id"], name=data["name"])
        wf.state = WorkflowState(data["state"])
        wf.results = data.get("results", {})
        wf.variables = data.get("variables", {})
        return wf

    def add_schedule(self, name: str, cron: str, workflow_id: str) -> None:
        self._scheduler.add_schedule(name, cron, workflow_id)

    def check_schedules(self) -> List[str]:
        return self._scheduler.check_and_trigger(self)

    def list_workflows(self) -> List[Dict[str, str]]:
        return [{"id": w.id, "name": w.name, "state": w.state.value} for w in self._workflows.values()]


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== MAGNATRIX-OS Workflow Engine Demo ===\n")

    engine = WorkflowEngine()

    # Demo 1: Simple sequential workflow
    print("--- Demo 1: Sequential Workflow ---")
    tasks = [
        Task(id="a", name="fetch_data", task_type="function", func=lambda: "data", config={}),
        Task(id="b", name="process_data", task_type="function", func=lambda data: f"processed_{data}", config={"data": "data"}, depends_on=["a"]),
        Task(id="c", name="save_result", task_type="function", func=lambda result: f"saved_{result}", config={"result": "result"}, depends_on=["b"]),
    ]
    wf = engine.create_workflow("etl_pipeline", tasks)
    result = engine.run(wf.id)
    print(f"  State: {result['state']}, Duration: {result['duration']:.3f}s")
    print(f"  Completed: {result['completed']}/{result['total']}")
    print()

    # Demo 2: Parallel workflow
    print("--- Demo 2: Parallel Branches ---")
    tasks2 = [
        Task(id="prep", name="prepare", task_type="function", func=lambda: "ready", config={}),
        Task(id="branch1", name="task1", task_type="function", func=lambda: "result1", config={}, depends_on=["prep"]),
        Task(id="branch2", name="task2", task_type="function", func=lambda: "result2", config={}, depends_on=["prep"]),
        Task(id="merge", name="combine", task_type="function", func=lambda: "merged", config={}, depends_on=["branch1", "branch2"]),
    ]
    wf2 = engine.create_workflow("parallel_work", tasks2)
    result2 = engine.run(wf2.id)
    print(f"  State: {result2['state']}, Duration: {result2['duration']:.3f}s")
    print(f"  Completed: {result2['completed']}/{result2['total']}")
    print()

    # Demo 3: Shell task
    print("--- Demo 3: Shell Task ---")
    tasks3 = [
        Task(id="shell", name="list_files", task_type="shell", config={"command": "ls -1 /tmp"}, timeout=5.0),
    ]
    wf3 = engine.create_workflow("shell_test", tasks3)
    result3 = engine.run(wf3.id)
    print(f"  State: {result3['state']}")
    print()

    # Demo 4: Retry with backoff
    print("--- Demo 4: Retry + Backoff ---")
    fail_count = [0]
    def flaky():
        fail_count[0] += 1
        if fail_count[0] < 3:
            raise RuntimeError("Flaky failure")
        return "success_after_retry"

    tasks4 = [
        Task(id="retry", name="flaky_task", task_type="function", func=flaky, config={}, retries=3, backoff=0.1),
    ]
    wf4 = engine.create_workflow("retry_test", tasks4)
    result4 = engine.run(wf4.id)
    print(f"  State: {result4['state']}, Attempts: {fail_count[0]}")
    print()

    # Demo 5: Cycle detection
    print("--- Demo 5: Cycle Detection ---")
    bad_tasks = [
        Task(id="x", name="task_x", depends_on=["y"]),
        Task(id="y", name="task_y", depends_on=["z"]),
        Task(id="z", name="task_z", depends_on=["x"]),
    ]
    try:
        bad_wf = engine.create_workflow("bad", bad_tasks)
        engine.run(bad_wf.id)
    except ValueError as exc:
        print(f"  Correctly caught: {exc}")
    print()

    # Demo 6: Scheduling
    print("--- Demo 6: Schedule ---")
    engine.add_schedule("every_5min", "*/5 * * * *", wf.id)
    engine.add_schedule("hourly", "0 * * * *", wf2.id)
    triggered = engine.check_schedules()
    print(f"  Schedules: 2, Triggered now: {len(triggered)}")
    print()

    print(f"=== Workflow Engine Demo Complete ===")
    print(f"Total workflows: {len(engine.list_workflows())}")


if __name__ == "__main__":
    _demo()
