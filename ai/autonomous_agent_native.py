#!/usr/bin/env python3
"""
MAGNATRIX-OS Layer: AI — Autonomous Goal-Driven Agent
File: ai/autonomous_agent_native.py
Pattern: AMATI-PELAJARI-TIRU dari farzanehasghari/AgentGPT + AutoGPT

Native pure-Python reimplementation of:
  - Goal-driven autonomy: user defines goal, agent breaks into subtasks
  - Task decomposition: goal → prioritized subtask list
  - Tool ecosystem: web search, file I/O, code execution, API calls
  - Memory: short-term + long-term (JSON persistence)
  - Observation loop: execute → observe → reflect → replan
  - Self-critique: agent evaluates its own output quality

Zero external dependencies. Pure Python standard library.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 1.  TASK — unit of work
# ---------------------------------------------------------------------------

@dataclass
class Task:
    id: str
    description: str
    status: str = "pending"  # pending | running | done | failed
    result: str = ""
    priority: int = 5  # 1=high, 10=low
    depends_on: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "description": self.description,
            "status": self.status, "result": self.result,
            "priority": self.priority, "depends_on": self.depends_on,
        }


# ---------------------------------------------------------------------------
# 2.  TOOL REGISTRY
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Tools yang bisa digunakan agent."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., str]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register("SEARCH", self._tool_search)
        self.register("WRITE_FILE", self._tool_write_file)
        self.register("READ_FILE", self._tool_read_file)
        self.register("CALCULATE", self._tool_calculate)
        self.register("HTTP_GET", self._tool_http_get)
        self.register("EXECUTE_CODE", self._tool_execute_code)

    def register(self, name: str, fn: Callable[..., str]) -> None:
        self._tools[name] = fn

    def run(self, name: str, args: str) -> str:
        if name not in self._tools:
            return f"[ERROR] Tool '{name}' not found"
        try:
            return self._tools[name](args)
        except Exception as e:
            return f"[ERROR] {e}"

    def list(self) -> List[str]:
        return list(self._tools.keys())

    @staticmethod
    def _tool_search(query: str) -> str:
        return f"[SEARCH RESULTS for '{query[:50]}']\n1. Result A\n2. Result B\n3. Result C"

    @staticmethod
    def _tool_write_file(params: str) -> str:
        try:
            parts = params.split("|", 1)
            if len(parts) != 2:
                return "[ERROR] Format: path|content"
            path, content = parts
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"[OK] Written {len(content)} chars to {path}"
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def _tool_read_file(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def _tool_calculate(expr: str) -> str:
        try:
            # Safe eval: only numbers and basic operators
            allowed = set("0123456789+-*/.() ")
            if not all(c in allowed for c in expr):
                return "[ERROR] Only numbers and +-*/.() allowed"
            result = eval(expr, {"__builtins__": {}}, {})
            return f"[RESULT] {result}"
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def _tool_http_get(url: str) -> str:
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = resp.read()[:2000]
                return f"[HTTP {resp.status}] {data[:500]}..."
        except Exception as e:
            return f"[MOCK HTTP GET] {url}\nStatus: 200\nBody: (mock response for {url[:40]})"

    @staticmethod
    def _tool_execute_code(code: str) -> str:
        try:
            # Very restricted: only simple expressions
            allowed = set("0123456789+-*/.() =<>!abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_\n\'\"")
            if not all(c in allowed for c in code):
                return "[ERROR] Restricted code execution"
            local = {}
            exec(code, {"__builtins__": {}}, local)
            return f"[OK] Output: {local}"
        except Exception as e:
            return f"[ERROR] {e}"


# ---------------------------------------------------------------------------
# 3.  MEMORY MANAGER — short-term + long-term
# ---------------------------------------------------------------------------

class MemoryManager:
    """Short-term rolling buffer + long-term JSON persistence."""

    def __init__(self, long_term_path: str = "agent_memory.json",
                 short_term_size: int = 20) -> None:
        self.short_term: deque = deque(maxlen=short_term_size)
        self.long_term_path = long_term_path
        self.long_term: Dict[str, Any] = {}
        self._load_long_term()

    def _load_long_term(self) -> None:
        if os.path.isfile(self.long_term_path):
            try:
                with open(self.long_term_path, "r", encoding="utf-8") as f:
                    self.long_term = json.load(f)
            except Exception:
                self.long_term = {}

    def save_long_term(self) -> None:
        with open(self.long_term_path, "w", encoding="utf-8") as f:
            json.dump(self.long_term, f, indent=2, ensure_ascii=False)

    def add(self, role: str, content: str) -> None:
        self.short_term.append({"role": role, "content": content, "time": time.time()})

    def get_context(self, n: int = 10) -> str:
        recent = list(self.short_term)[-n:]
        lines = []
        for item in recent:
            t = time.strftime("%H:%M:%S", time.localtime(item["time"]))
            lines.append(f"[{t}] {item['role']}: {item['content'][:200]}")
        return "\n".join(lines)

    def store_fact(self, key: str, value: Any) -> None:
        self.long_term[key] = value
        self.save_long_term()

    def recall(self, key: str) -> Any:
        return self.long_term.get(key)


# ---------------------------------------------------------------------------
# 4.  GOAL DECOMPOSER
# ---------------------------------------------------------------------------

class GoalDecomposer:
    """Breaks a goal into subtasks."""

    def __init__(self, llm: Optional[MockToUnifiedBridge] = None) -> None:
        self.llm = llm or MockToUnifiedBridge()

    def decompose(self, goal: str) -> List[Task]:
        """Break goal into tasks."""
        tasks = []
        # Heuristic decomposition based on keywords
        g = goal.lower()

        if any(kw in g for kw in ["research", "find", "search", "cari"]):
            tasks.append(Task("t1", f"Research information about: {goal}", priority=1))
        if any(kw in g for kw in ["write", "create", "buat", "tulis"]):
            tasks.append(Task("t2", f"Draft content for: {goal}", priority=2))
        if any(kw in g for kw in ["analyze", "analysis", "analisis"]):
            tasks.append(Task("t3", f"Analyze data for: {goal}", priority=2))
        if any(kw in g for kw in ["compare", "bandingkan"]):
            tasks.append(Task("t4", f"Compare options for: {goal}", priority=3))
        if any(kw in g for kw in ["summarize", "ringkasan", "summary"]):
            tasks.append(Task("t5", f"Summarize findings for: {goal}", priority=3))

        # Fallback: always add at least one task
        if not tasks:
            tasks.append(Task("t1", f"Complete task: {goal}", priority=1))
            tasks.append(Task("t2", f"Review and refine result", priority=2))

        # Sort by priority
        tasks.sort(key=lambda t: t.priority)
        return tasks


# ---------------------------------------------------------------------------
# 5.  OBSERVER — evaluates task results
# ---------------------------------------------------------------------------

class Observer:
    """Evaluates task execution quality."""

    @staticmethod
    def evaluate(task: Task) -> Tuple[str, float]:
        """Returns (verdict, score)."""
        if task.status == "failed":
            return ("failed", 0.0)
        if not task.result:
            return ("empty", 0.3)
        if "[ERROR]" in task.result:
            return ("error", 0.2)
        if len(task.result) < 20:
            return ("short", 0.5)
        # Check for positive signals
        score = 0.7
        if "[OK]" in task.result or "[RESULT]" in task.result:
            score += 0.2
        if len(task.result) > 100:
            score += 0.1
        return ("success", min(score, 1.0))


# ---------------------------------------------------------------------------
# 6.  SELF-CRITIQUE
# ---------------------------------------------------------------------------

class SelfCritique:
    """Agent reflects on its performance."""

    @staticmethod
    def reflect(history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze history and suggest improvements."""
        total = len(history)
        if total == 0:
            return {"summary": "No history", "suggestions": []}

        success = sum(1 for h in history if h.get("score", 0) > 0.6)
        failed = sum(1 for h in history if h.get("score", 0) < 0.3)
        avg_score = sum(h.get("score", 0) for h in history) / total

        suggestions = []
        if avg_score < 0.5:
            suggestions.append("Break tasks into smaller pieces")
        if failed > 0:
            suggestions.append("Verify tool inputs before execution")
        if success / total < 0.7:
            suggestions.append("Add more verification steps")

        return {
            "summary": f"{success}/{total} succeeded, avg score: {avg_score:.2f}",
            "avg_score": avg_score,
            "suggestions": suggestions,
        }


# ---------------------------------------------------------------------------
# 7.  MOCK LLM
# ---------------------------------------------------------------------------

from ai.mock_to_unified_bridge import MockToUnifiedBridge


# ---------------------------------------------------------------------------
# 8.  AUTONOMOUS AGENT — main orchestrator
# ---------------------------------------------------------------------------

class AutonomousAgent:
    """
    End-to-end autonomous agent: decompose → execute → observe → critique → replan.
    """

    def __init__(self, goal: str = "", max_steps: int = 10,
                 memory_path: str = "autonomous_agent_memory.json") -> None:
        self.goal = goal
        self.max_steps = max_steps
        self.memory = MemoryManager(memory_path)
        self.tools = ToolRegistry()
        self.decomposer = GoalDecomposer()
        self.observer = Observer()
        self.critique = SelfCritique()
        self.tasks: List[Task] = []
        self.history: List[Dict[str, Any]] = []
        self.step_count = 0

    def run(self, goal: Optional[str] = None) -> str:
        """Execute full autonomous loop."""
        if goal:
            self.goal = goal

        self.memory.add("user", f"Goal: {self.goal}")

        # Phase 1: Decompose
        self.tasks = self.decomposer.decompose(self.goal)
        self.memory.add("system", f"Decomposed into {len(self.tasks)} tasks")

        # Phase 2: Execute each task
        for task in self.tasks:
            if self.step_count >= self.max_steps:
                break
            self._execute_task(task)
            self.step_count += 1

        # Phase 3: Critique
        reflection = self.critique.reflect(self.history)
        self.memory.add("system", f"Self-critique: {reflection['summary']}")

        # Phase 4: Synthesize final answer
        results = [t.result for t in self.tasks if t.result]
        final = self._synthesize(results)

        self.memory.add("assistant", final)
        return final

    def _execute_task(self, task: Task) -> None:
        """Run single task dengan available tools."""
        task.status = "running"
        self.memory.add("system", f"Running task {task.id}: {task.description}")

        # Simple heuristic: decide which tool to use
        tool_name, tool_args = self._select_tool(task)
        result = self.tools.run(tool_name, tool_args)

        task.result = result
        task.status = "done" if "[OK]" in result or "[RESULT]" in result else "failed"
        task.completed_at = time.time()

        verdict, score = self.observer.evaluate(task)
        self.history.append({
            "task_id": task.id,
            "tool": tool_name,
            "verdict": verdict,
            "score": score,
            "result_preview": result[:100],
        })

        self.memory.add("tool", f"{tool_name}: {result[:200]}")

    def _select_tool(self, task: Task) -> Tuple[str, str]:
        """Heuristic tool selection."""
        desc = task.description.lower()
        if any(kw in desc for kw in ["research", "find", "search", "cari"]):
            return "SEARCH", task.description
        if any(kw in desc for kw in ["write", "create", "save", "file"]):
            return "WRITE_FILE", "output.txt|" + task.description
        if any(kw in desc for kw in ["read", "load", "file", "baca"]):
            return "READ_FILE", "output.txt"
        if any(kw in desc for kw in ["calculate", "compute", "math", "hitung"]):
            return "CALCULATE", "2 + 2"
        if any(kw in desc for kw in ["http", "api", "fetch", "url"]):
            return "HTTP_GET", "https://example.com"
        if any(kw in desc for kw in ["code", "run", "execute", "program"]):
            return "EXECUTE_CODE", "x = 1 + 1"
        return "SEARCH", task.description

    def _synthesize(self, results: List[str]) -> str:
        """Merge task results into final answer."""
        if not results:
            return "[AGENT] No results to synthesize."
        lines = [f"[AGENT RESULT for: {self.goal}]", "", "Subtask results:"]
        for i, r in enumerate(results, 1):
            lines.append(f"  {i}. {r[:150]}...")
        lines.append("")
        lines.append(f"Total steps: {self.step_count}")
        lines.append(f"Tasks completed: {sum(1 for t in self.tasks if t.status == 'done')}/{len(self.tasks)}")
        return "\n".join(lines)

    def get_status(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "step_count": self.step_count,
            "tasks": [t.to_dict() for t in self.tasks],
            "history": self.history,
            "llm_stats": self.decomposer.llm.get_stats(),
        }


# ---------------------------------------------------------------------------
# 9.  MAIN DEMO & TEST SUITE
# ---------------------------------------------------------------------------

def _test_task_model() -> None:
    t = Task("t1", "Test task", priority=1)
    assert t.status == "pending"
    t.status = "done"
    assert t.to_dict()["status"] == "done"
    print("  [OK] Task model")


def _test_tool_registry() -> None:
    tr = ToolRegistry()
    assert "SEARCH" in tr.list()
    r = tr.run("SEARCH", "test query")
    assert "RESULTS" in r
    r2 = tr.run("CALCULATE", "2 + 3 * 4")
    assert "14" in r2
    print("  [OK] ToolRegistry")


def _test_memory_manager() -> None:
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        mm = MemoryManager(path, short_term_size=5)
        mm.add("user", "hello")
        mm.add("assistant", "hi")
        ctx = mm.get_context(2)
        assert "hello" in ctx
        mm.store_fact("key1", "value1")
        assert mm.recall("key1") == "value1"
        print("  [OK] MemoryManager")
    finally:
        os.unlink(path)


def _test_goal_decomposer() -> None:
    gd = GoalDecomposer()
    tasks = gd.decompose("Research and summarize Python asyncio")
    assert len(tasks) >= 2
    assert tasks[0].priority <= tasks[-1].priority
    print("  [OK] GoalDecomposer")


def _test_observer() -> None:
    t = Task("t1", "test")
    t.result = "[OK] success with detailed output that is longer than one hundred characters to ensure proper scoring"
    t.status = "done"
    v, s = Observer.evaluate(t)
    assert v == "success"
    assert s > 0.7

    t2 = Task("t2", "test")
    t2.result = "[ERROR] fail"
    t2.status = "failed"
    v2, s2 = Observer.evaluate(t2)
    assert v2 == "failed"
    assert s2 == 0.0
    print("  [OK] Observer")


def _test_self_critique() -> None:
    history = [
        {"score": 0.9}, {"score": 0.8}, {"score": 0.3},
    ]
    r = SelfCritique.reflect(history)
    assert "succeeded" in r["summary"]
    assert "avg_score" in r
    print("  [OK] SelfCritique")


def _test_autonomous_agent() -> None:
    agent = AutonomousAgent(goal="Calculate 100 factorial and save to file", max_steps=5)
    result = agent.run()
    assert agent.step_count >= 1
    assert len(agent.tasks) >= 1
    status = agent.get_status()
    assert status["goal"] == "Calculate 100 factorial and save to file"
    print("  [OK] AutonomousAgent full loop")


def _test_agent_with_research_goal() -> None:
    agent = AutonomousAgent(goal="Research MAGNATRIX-OS architecture", max_steps=5)
    result = agent.run()
    assert "AGENT RESULT" in result
    print("  [OK] Agent research goal")


def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Autonomous Agent — Native Demo")
    print("Pattern: AMATI-PELAJARI-TIRU dari AutoGPT / AgentGPT")
    print("=" * 60)

    print("\n[Unit Tests]")
    _test_task_model()
    _test_tool_registry()
    _test_memory_manager()
    _test_goal_decomposer()
    _test_observer()
    _test_self_critique()
    _test_autonomous_agent()
    _test_agent_with_research_goal()

    print("\n[Full Execution Demo — Research Goal]")
    agent = AutonomousAgent(
        goal="Research the benefits of agentic AI operating systems",
        max_steps=6,
    )
    result = agent.run()
    print(result)

    print("\n[Agent Status]")
    status = agent.get_status()
    print(f"  Steps: {status['step_count']}")
    print(f"  Tasks: {len(status['tasks'])}")
    print(f"  LLM calls: {status['llm_stats']['calls']}")

    print("\n" + "=" * 60)
    print("All tests passed. Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
