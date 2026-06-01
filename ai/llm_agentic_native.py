"""
ai/llm_agentic_native.py — MAGNATRIX-OS
Agentic Loop Engine for the LLM Arena

Provides an end-to-end agentic loop:
  Planner      → decompose request into DAG subtasks with complexity estimates
  Executor     → run subtasks in parallel where dependencies allow
  Observer     → verify outputs, detect failure modes, score quality
  SelfCorrector→ retry with alternate strategy or escalate
  Memory       → persist task state, intermediate results, resume capability
  AgentLoop    → orchestrate plan → execute → observe → correct → complete

Pure Python ≥3.9, stdlib only. Native simulation style — no external AI APIs.
Consistent with MAGNATRIX codebase conventions.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ───────────────────────────────────────────────
# Data Models
# ───────────────────────────────────────────────


class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    CORRECTED = auto()


@dataclass
class Task:
    """A single node in the agentic task DAG."""
    task_id: str = field(default_factory=lambda: f"t_{uuid.uuid4().hex[:6]}")
    description: str = ""
    task_type: str = "generic"  # e.g. weather, math, write, search
    dependencies: List[str] = field(default_factory=list)
    estimated_complexity: int = 5  # 1–10
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    attempts: int = 0
    max_attempts: int = 3
    error_log: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_ready(self, completed_ids: Set[str]) -> bool:
        """True if all dependencies are satisfied."""
        return all(d in completed_ids for d in self.dependencies)


@dataclass
class Observation:
    """Result of observing a completed task."""
    task_id: str = ""
    success: bool = False
    quality_score: float = 0.0  # 0.0–1.0
    failure_mode: str = ""  # empty, timeout, bad_format, missing_data, hallucination
    notes: List[str] = field(default_factory=list)


@dataclass
class AgentResult:
    """Final output of the agentic loop."""
    request: str = ""
    tasks: List[Task] = field(default_factory=list)
    final_output: Any = None
    duration_ms: float = 0.0
    iterations: int = 0
    completed: bool = False


# ───────────────────────────────────────────────
# Memory — Task State & Resume Capability
# ───────────────────────────────────────────────


class AgentMemory:
    """Tracks task state across iterations and stores intermediate results."""

    def __init__(self) -> None:
        self._results: Dict[str, Any] = {}
        self._snapshots: List[Dict[str, Any]] = []
        self._start_time: float = time.time()

    def store(self, task_id: str, result: Any) -> None:
        self._results[task_id] = result

    def get(self, task_id: str) -> Any:
        return self._results.get(task_id)

    def snapshot(self, tasks: List[Task], iteration: int) -> None:
        """Save a resume-capable snapshot."""
        state = {
            "iteration": iteration,
            "timestamp": time.time(),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "status": t.status.name,
                    "result": t.result,
                    "attempts": t.attempts,
                    "error_log": t.error_log,
                }
                for t in tasks
            ],
        }
        self._snapshots.append(state)

    def resume_state(self, snapshot_index: int = -1) -> Dict[str, Any]:
        """Return a snapshot for replay/resume."""
        if not self._snapshots:
            return {}
        return self._snapshots[snapshot_index]

    def elapsed_ms(self) -> float:
        return (time.time() - self._start_time) * 1000


# ───────────────────────────────────────────────
# Planner — Request Decomposition & DAG Estimation
# ───────────────────────────────────────────────


class Planner:
    """Decomposes a user request into a DAG of subtasks with complexity estimates."""

    # Simple keyword→task-type mapping for native simulation
    _TYPE_HINTS: Dict[str, str] = {
        "weather": "weather",
        "temperature": "weather",
        "forecast": "weather",
        "celsius": "math",
        "fahrenheit": "math",
        "calculate": "math",
        "compute": "math",
        "write": "write",
        "summary": "write",
        "summarize": "write",
        "report": "write",
        "search": "search",
        "find": "search",
        "lookup": "search",
    }

    def plan(self, request: str) -> List[Task]:
        """Decompose request into subtasks and wire dependencies."""
        raw_steps = self._extract_steps(request)
        tasks: List[Task] = []
        prev_ids: List[str] = []

        for idx, step_text in enumerate(raw_steps):
            task_type = self._infer_type(step_text)
            complexity = self._estimate_complexity(step_text, task_type)
            deps = list(prev_ids) if idx > 0 else []
            task = Task(
                description=step_text,
                task_type=task_type,
                dependencies=deps,
                estimated_complexity=complexity,
            )
            tasks.append(task)
            prev_ids = [task.task_id]

        # Upgrade to richer DAG when keywords indicate parallel opportunities
        tasks = self._upgrade_dag(request, tasks)
        return tasks

    def _extract_steps(self, request: str) -> List[str]:
        """Naïve sentence split into ordered steps."""
        sentences = [s.strip() for s in request.replace(",", ".").split(".") if s.strip()]
        # If the request is a single compound sentence, break on verbs
        if len(sentences) == 1:
            text = sentences[0]
            # Look for conjunctions that suggest multiple actions
            for conj in (" and ", " then ", " followed by ", "; "):
                if conj in text.lower():
                    parts = [p.strip() for p in text.lower().split(conj) if p.strip()]
                    if len(parts) > 1:
                        return parts
        return sentences

    def _infer_type(self, step: str) -> str:
        low = step.lower()
        for keyword, task_type in self._TYPE_HINTS.items():
            if keyword in low:
                return task_type
        return "generic"

    def _estimate_complexity(self, step: str, task_type: str) -> int:
        """Estimate 1–10 based on heuristics."""
        base = {"weather": 2, "math": 3, "write": 4, "search": 5, "generic": 5}.get(task_type, 5)
        modifiers = step.lower().count("and") + step.count(",")
        return min(10, base + modifiers)

    def _upgrade_dag(self, request: str, tasks: List[Task]) -> List[Task]:
        """Detect parallelizable branches and adjust dependencies."""
        low = request.lower()
        # Example heuristic: if user asks for weather + conversion, conversion depends on weather
        # but two independent searches can run in parallel.
        weather_idx = next((i for i, t in enumerate(tasks) if t.task_type == "weather"), None)
        math_idx = next((i for i, t in enumerate(tasks) if t.task_type == "math"), None)

        if weather_idx is not None and math_idx is not None and math_idx > weather_idx:
            tasks[math_idx].dependencies = [tasks[weather_idx].task_id]

        return tasks


# ───────────────────────────────────────────────
# Tool Registry — Simulated Tool Suite
# ───────────────────────────────────────────────


ToolFn = Callable[..., Any]


class ToolRegistry:
    """Lightweight tool registry for native simulation."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolFn] = {}
        self._register_defaults()

    def register(self, name: str, fn: ToolFn) -> None:
        self._tools[name] = fn

    def get(self, name: str) -> ToolFn:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        return self._tools[name]

    def _register_defaults(self) -> None:
        self.register("weather", self._mock_weather)
        self.register("math", self._mock_math)
        self.register("write", self._mock_write)
        self.register("search", self._mock_search)

    @staticmethod
    def _mock_weather(location: str = "Tokyo", **_kwargs: Any) -> Dict[str, Any]:
        return {
            "location": location,
            "celsius": 22.0,
            "condition": "partly cloudy",
            "humidity": 58,
        }

    @staticmethod
    def _mock_math(expression: str = "22 * 9/5 + 32", **_kwargs: Any) -> Dict[str, Any]:
        # Very small safe-eval for demo purposes
        allowed = set("0123456789.+-*/() ")
        if all(c in allowed for c in expression):
            try:
                value = eval(expression, {"__builtins__": {}}, {})
                return {"expression": expression, "result": round(value, 2)}
            except Exception as e:
                return {"expression": expression, "error": str(e)}
        return {"expression": expression, "error": "disallowed characters"}

    @staticmethod
    def _mock_write(prompt: str = "summary", context: str = "", **_kwargs: Any) -> Dict[str, Any]:
        text = f"Summary: {prompt}\nContext: {context}\nStatus: generated by native write tool."
        return {"text": text, "word_count": len(text.split())}

    @staticmethod
    def _mock_search(query: str = "", **_kwargs: Any) -> Dict[str, Any]:
        return {"query": query, "results": [f"Result for '{query}' (#1)", f"Result for '{query}' (#2)"]}


# ───────────────────────────────────────────────
# Executor — Parallel Subtask Execution
# ───────────────────────────────────────────────


class Executor:
    """Executes tasks in parallel where the DAG permits."""

    def __init__(self, tools: ToolRegistry, memory: AgentMemory) -> None:
        self.tools = tools
        self.memory = memory

    async def run_all(self, tasks: List[Task]) -> None:
        """Run tasks respecting dependency order, maximizing parallelism."""
        completed: Set[str] = set()
        pending = list(tasks)
        running: Set[asyncio.Task] = set()
        task_by_id = {t.task_id: t for t in tasks}

        while pending or running:
            # Launch newly ready tasks
            ready = [t for t in pending if t.is_ready(completed)]
            for t in ready:
                pending.remove(t)
                t.status = TaskStatus.RUNNING
                coro = self._execute_one(t, task_by_id)
                running.add(asyncio.create_task(coro))

            if running:
                done, running = await asyncio.wait(
                    running, return_when=asyncio.FIRST_COMPLETED
                )
                for future in done:
                    finished_task = await future
                    completed.add(finished_task.task_id)
            else:
                # Nothing ready and nothing running → deadlock (cycle or missing dep)
                await asyncio.sleep(0.01)

    async def _execute_one(self, task: Task, task_by_id: Dict[str, Task]) -> Task:
        """Execute a single task using its mapped tool."""
        task.attempts += 1
        try:
            tool_name = task.task_type if task.task_type in self.tools._tools else "search"
            tool_fn = self.tools.get(tool_name)

            # Build arguments from dependencies' results
            kwargs: Dict[str, Any] = {"prompt": task.description}
            if task.task_type == "weather":
                # Extract location heuristically
                words = task.description.lower().split()
                for w in words:
                    if w not in {"the", "in", "find", "latest", "weather", "forecast", "temperature", "for", "of"}:
                        kwargs["location"] = w.title()
                        break
            elif task.task_type == "math":
                # Prefer dependency result if present
                dep_results = [self.memory.get(d) for d in task.dependencies]
                numbers = []
                for r in dep_results:
                    if isinstance(r, dict):
                        for v in r.values():
                            if isinstance(v, (int, float)):
                                numbers.append(v)
                if numbers:
                    kwargs["expression"] = f"{numbers[0]} * 9/5 + 32"
                else:
                    kwargs["expression"] = task.description
            elif task.task_type == "write":
                dep_contexts = []
                for d in task.dependencies:
                    res = self.memory.get(d)
                    if res:
                        dep_contexts.append(json.dumps(res, default=str))
                kwargs["context"] = " | ".join(dep_contexts)

            # Run tool (simulated I/O bound)
            await asyncio.sleep(0.05)
            result = tool_fn(**kwargs)
            task.result = result
            self.memory.store(task.task_id, result)
            task.status = TaskStatus.SUCCESS
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error_log.append(str(exc))
            task.result = {"error": str(exc)}
            self.memory.store(task.task_id, task.result)
        return task


# ───────────────────────────────────────────────
# Observer — Quality Verification & Failure Detection
# ───────────────────────────────────────────────


class Observer:
    """Verifies subtask outputs and detects failure modes."""

    def observe(self, task: Task) -> Observation:
        obs = Observation(task_id=task.task_id)
        if task.status != TaskStatus.SUCCESS:
            obs.success = False
            obs.failure_mode = "execution_error"
            obs.notes.append(f"Task failed after {task.attempts} attempts.")
            return obs

        result = task.result
        if result is None:
            obs.success = False
            obs.failure_mode = "missing_data"
            obs.notes.append("Result is None.")
            return obs

        # Quality heuristics per task type
        if task.task_type == "write":
            text = result.get("text", "") if isinstance(result, dict) else str(result)
            obs.quality_score = min(1.0, len(text) / 200)
            if len(text) < 20:
                obs.success = False
                obs.failure_mode = "bad_format"
                obs.notes.append("Write output too short.")
            else:
                obs.success = True
                obs.notes.append(f"Write output length OK ({len(text)} chars).")

        elif task.task_type == "math":
            if isinstance(result, dict) and "error" in result:
                obs.success = False
                obs.failure_mode = "bad_format"
                obs.notes.append(f"Math error: {result['error']}")
            else:
                obs.success = True
                obs.quality_score = 1.0
                obs.notes.append("Math result computed.")

        elif task.task_type == "weather":
            if isinstance(result, dict) and "celsius" in result:
                obs.success = True
                obs.quality_score = 1.0
                obs.notes.append(f"Weather data for {result.get('location', '?')} retrieved.")
            else:
                obs.success = False
                obs.failure_mode = "missing_data"
                obs.notes.append("Missing temperature in weather result.")

        else:
            obs.success = True
            obs.quality_score = 0.8
            obs.notes.append("Generic task accepted.")

        return obs


# ───────────────────────────────────────────────
# SelfCorrector — Retry / Escalate / Replan
# ───────────────────────────────────────────────


class SelfCorrector:
    """Retries failed tasks with alternate strategy or escalates."""

    def __init__(self, planner: Planner, executor: Executor, observer: Observer) -> None:
        self.planner = planner
        self.executor = executor
        self.observer = observer

    async def correct(self, task: Task) -> bool:
        """Attempt to correct a failed task. Return True if corrected."""
        if task.attempts >= task.max_attempts:
            return False

        # Strategy 1: retry with softer args
        task.status = TaskStatus.PENDING
        await self.executor._execute_one(task, {})
        obs = self.observer.observe(task)
        if obs.success:
            task.status = TaskStatus.CORRECTED
            return True

        # Strategy 2: replan into smaller subtasks (simplified: just retry once more)
        if task.attempts < task.max_attempts:
            task.status = TaskStatus.PENDING
            task.description = task.description + " (retry with simpler parameters)"
            await self.executor._execute_one(task, {})
            obs = self.observer.observe(task)
            if obs.success:
                task.status = TaskStatus.CORRECTED
                return True

        return False


# ───────────────────────────────────────────────
# AgentLoop — Main Orchestrator
# ───────────────────────────────────────────────


class AgentLoop:
    """
    Main orchestrator:
        plan → execute → observe → correct → complete
    """

    def __init__(self) -> None:
        self.planner = Planner()
        self.memory = AgentMemory()
        self.tools = ToolRegistry()
        self.executor = Executor(self.tools, self.memory)
        self.observer = Observer()
        self.corrector = SelfCorrector(self.planner, self.executor, self.observer)

    async def run(self, request: str) -> AgentResult:
        """Run the full agentic loop on a user request."""
        start = time.time()
        result = AgentResult(request=request)

        # 1. Plan
        tasks = self.planner.plan(request)
        result.tasks = tasks

        # 2. Execute
        await self.executor.run_all(tasks)

        # 3. Observe + Correct loop
        iteration = 0
        max_iterations = 5
        while iteration < max_iterations:
            iteration += 1
            all_ok = True
            for task in tasks:
                if task.status not in (TaskStatus.SUCCESS, TaskStatus.CORRECTED):
                    obs = self.observer.observe(task)
                    if not obs.success:
                        all_ok = False
                        fixed = await self.corrector.correct(task)
                        if not fixed:
                            task.error_log.append(f"Uncorrectable after {task.attempts} tries.")
            self.memory.snapshot(tasks, iteration)
            if all_ok:
                break

        # 4. Finalize
        result.iterations = iteration
        result.duration_ms = (time.time() - start) * 1000
        result.completed = all(t.status in (TaskStatus.SUCCESS, TaskStatus.CORRECTED) for t in tasks)
        if tasks:
            # Prefer the last task's result as the final deliverable
            result.final_output = tasks[-1].result
        return result


# ───────────────────────────────────────────────
# Demo
# ───────────────────────────────────────────────


async def demo() -> None:
    """
    3-step demo:
        1. Find the latest weather in Tokyo
        2. Calculate Celsius to Fahrenheit
        3. Write a summary
    """
    request = "find the latest weather in Tokyo. calculate Celsius to Fahrenheit. write a summary"
    agent = AgentLoop()
    result = await agent.run(request)

    print("=" * 60)
    print("AGENTIC LOOP DEMO")
    print("=" * 60)
    print(f"Request : {result.request}")
    print(f"Completed: {result.completed}")
    print(f"Duration: {result.duration_ms:.1f} ms")
    print(f"Iterations: {result.iterations}")
    print("-" * 60)
    for t in result.tasks:
        status_icon = "✅" if t.status in (TaskStatus.SUCCESS, TaskStatus.CORRECTED) else "❌"
        print(f"{status_icon} [{t.task_id}] {t.description}")
        print(f"   type={t.task_type} | complexity={t.estimated_complexity} | attempts={t.attempts}")
        print(f"   result={json.dumps(t.result, indent=2, default=str)}")
        if t.error_log:
            print(f"   errors={t.error_log}")
    print("-" * 60)
    print("FINAL OUTPUT:")
    print(json.dumps(result.final_output, indent=2, default=str))
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
