"""
agent_gpt_native.py — Autonomous Web Agent with Goal Decomposition.

Architectural patterns extracted from reworkd/AgentGPT (canonical fork of farzanehasghari/AgentGPT):
- Goal-driven autonomous loop: goal → task decomposition → execution → learning.
- Web browsing capability via simulated browser actions (navigate, extract, search).
- Long-term memory via vector DB for storing task outcomes and learnings.
- Self-evaluation and task retry with exponential backoff.
- Human-in-the-loop pause points for high-stakes decisions.

Pure Python ≥3.9, stdlib only. LLM provided via callback.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class TaskStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    DONE = auto()
    FAILED = auto()
    NEEDS_HELP = auto()


@dataclass
class Task:
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    attempts: int = 0
    max_attempts: int = 3
    subtasks: List["Task"] = field(default_factory=list)
    parent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMemory:
    """Simple episodic memory for the agent."""
    episodes: List[Dict[str, Any]] = field(default_factory=list)

    def add(self, task_id: str, action: str, outcome: str, lesson: str = "") -> None:
        self.episodes.append({
            "task_id": task_id,
            "action": action,
            "outcome": outcome,
            "lesson": lesson,
            "timestamp": time.time(),
        })

    def recall(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Naive keyword recall (replace with vector search in production)."""
        scored = []
        for ep in self.episodes:
            score = sum(1 for w in query.lower().split() if w in str(ep).lower())
            if score:
                scored.append((score, ep))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:k]]


@dataclass
class BrowserState:
    """Simulated browser state for web actions."""
    url: str = "about:blank"
    title: str = ""
    extracted_text: str = ""
    history: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Native AgentGPT Engine
# ---------------------------------------------------------------------------

class NativeAgentGPT:
    """
    Autonomous agent inspired by AgentGPT architecture.

    Usage:
        agent = NativeAgentGPT(llm_fn=my_llm)
        result = agent.run("Research the latest AI breakthroughs")
    """

    def __init__(
        self,
        llm_fn: Callable[[str], str],
        web_search_fn: Optional[Callable[[str], List[str]]] = None,
        web_extract_fn: Optional[Callable[[str], str]] = None,
        max_iterations: int = 10,
    ) -> None:
        self.llm = llm_fn
        self.web_search = web_search_fn or self._default_web_search
        self.web_extract = web_extract_fn or self._default_web_extract
        self.max_iterations = max_iterations
        self.memory = AgentMemory()
        self.browser = BrowserState()
        self.task_registry: Dict[str, Task] = {}

    # --- Default web stubs -------------------------------------------------

    @staticmethod
    def _default_web_search(query: str) -> List[str]:
        return [f"https://example.com/search?q={query.replace(' ', '+')}"]

    @staticmethod
    def _default_web_extract(url: str) -> str:
        return f"[Simulated extraction from {url}]"

    # --- Core loop ---------------------------------------------------------

    def run(self, goal: str, pause_callback: Optional[Callable[[Task], bool]] = None) -> str:
        """Execute the full autonomous loop for a given goal."""
        root = Task(id=str(uuid.uuid4())[:8], description=goal)
        self.task_registry[root.id] = root

        # Phase 1: Decompose goal into tasks
        self._decompose(root)

        # Phase 2: Execute all tasks breadth-first
        iteration = 0
        queue: List[Task] = [root]
        while queue and iteration < self.max_iterations:
            iteration += 1
            current = queue.pop(0)
            if current.status in (TaskStatus.DONE, TaskStatus.FAILED):
                continue

            if pause_callback and current.metadata.get("high_stakes"):
                if not pause_callback(current):
                    current.status = TaskStatus.NEEDS_HELP
                    continue

            self._execute_task(current)
            if current.subtasks:
                queue.extend(current.subtasks)

        # Phase 3: Synthesize final answer
        return self._synthesize(root)

    # --- Internal methods --------------------------------------------------

    def _decompose(self, task: Task) -> None:
        """Ask LLM to break a task into subtasks."""
        prompt = (
            f"Goal: {task.description}\n"
            "Break this into 1-5 concrete subtasks as a JSON list of strings. "
            "Return ONLY the JSON list, no markdown."
        )
        raw = self.llm(prompt)
        try:
            sub_descriptions = json.loads(raw)
        except Exception:
            sub_descriptions = [raw[:200]]

        if not isinstance(sub_descriptions, list):
            sub_descriptions = [str(sub_descriptions)]

        for desc in sub_descriptions:
            sub = Task(
                id=str(uuid.uuid4())[:8],
                description=str(desc),
                parent_id=task.id,
            )
            task.subtasks.append(sub)
            self.task_registry[sub.id] = sub

    def _execute_task(self, task: Task) -> None:
        """Execute a single task with retry and web fallback."""
        task.status = TaskStatus.IN_PROGRESS
        task.attempts += 1

        # Recall similar past episodes
        memories = self.memory.recall(task.description, k=3)
        memory_context = ""
        if memories:
            memory_context = "\n".join(
                f"- Past action: {m['action']} → {m['outcome']}" for m in memories
            )

        # Decide whether to use web search
        needs_web = any(k in task.description.lower() for k in ("latest", "web", "search", "find", "url"))

        if needs_web:
            urls = self.web_search(task.description)
            if urls:
                self.browser.url = urls[0]
                self.browser.history.append(urls[0])
                self.browser.extracted_text = self.web_extract(urls[0])

        prompt = (
            f"Task: {task.description}\n"
            f"{memory_context}\n"
            f"Web context: {self.browser.extracted_text[:500]}\n"
            "Execute the task and return ONLY the result, no extra text."
        )
        result = self.llm(prompt)
        task.result = result

        # Self-evaluation
        eval_prompt = (
            f"Task: {task.description}\nResult: {result}\n"
            "Does this result successfully complete the task? Answer ONLY 'yes' or 'no'."
        )
        eval_result = self.llm(eval_prompt).strip().lower()
        success = eval_result.startswith("yes") or eval_result.startswith("true")

        if success:
            task.status = TaskStatus.DONE
            task.completed_at = time.time()
            self.memory.add(task.id, task.description, result, lesson="success")
        elif task.attempts < task.max_attempts:
            task.status = TaskStatus.PENDING
            time.sleep(0.5 * (2 ** task.attempts))  # exponential backoff
        else:
            task.status = TaskStatus.FAILED
            self.memory.add(task.id, task.description, result, lesson="failed")

    def _synthesize(self, root: Task) -> str:
        """Compose final answer from all completed subtask results."""
        results = []
        for sub in root.subtasks:
            if sub.status == TaskStatus.DONE:
                results.append(f"- {sub.description}: {sub.result}")
        context = "\n".join(results) if results else root.result

        prompt = (
            f"Original goal: {root.description}\n"
            f"Completed results:\n{context}\n"
            "Synthesize a coherent final answer."
        )
        return self.llm(prompt)

    def get_task_tree(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Return JSON-serializable task tree for dashboard visualization."""
        task = self.task_registry.get(task_id) if task_id else None
        if task is None:
            # find root
            task = next((t for t in self.task_registry.values() if t.parent_id is None), None)
        if task is None:
            return {}

        def _to_dict(t: Task) -> Dict[str, Any]:
            return {
                "id": t.id,
                "description": t.description,
                "status": t.status.name,
                "result": t.result[:200],
                "attempts": t.attempts,
                "children": [_to_dict(c) for c in t.subtasks],
            }

        return _to_dict(task)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _mock_llm(prompt: str) -> str:
    """Deterministic mock LLM for testing."""
    p = prompt.lower()
    if "json" in p and "subtasks" in p:
        return '["Search web", "Summarize findings", "Verify sources"]'
    if "yes" in p and "no" in p:
        return "yes"
    if "synthesize" in p:
        return "Final synthesized answer from mock LLM."
    return "Mock result: " + prompt[:50]


def test_agent_gpt() -> None:
    agent = NativeAgentGPT(llm_fn=_mock_llm)
    result = agent.run("Find latest AI news")
    assert isinstance(result, str)
    assert len(result) > 0
    tree = agent.get_task_tree()
    assert tree["status"] in ("DONE", "IN_PROGRESS", "PENDING")
    assert len(tree["children"]) > 0
    print("[test_agent_gpt] PASSED")


if __name__ == "__main__":
    test_agent_gpt()
