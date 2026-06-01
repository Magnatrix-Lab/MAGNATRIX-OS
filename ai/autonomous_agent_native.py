# ai/autonomous_agent_native.py
# AMATI-PELAJARI-TIRU: Pattern extracted from AgentGPT (reworkd/AgentGPT)
# https://github.com/reworkd/AgentGPT
# Autonomous browser-based AI agent with task decomposition, Next.js stack, tRPC, Prisma
# Native reimplementation for MAGNATRIX-OS Layer 10 (AI) + Layer 6 (Skills)

"""
Native Autonomous Agent Engine
==============================
Inspired by AgentGPT architecture patterns:
  - Goal-based autonomous task execution
  - Task decomposition: agent breaks goal into subtasks, executes iteratively
  - ReAct loop: Reason -> Act -> Observe -> Repeat
  - Memory: short-term (context window) + long-term (vector DB / SQLite)
  - Web browsing: simulated browser actions (navigate, search, extract)
  - Streaming output: real-time task progress updates

Features:
  - Pure-Python autonomous agent with no external web framework deps
  - Task tree with parent-child dependencies
  - ReAct reasoning loop with tool execution
  - SQLite-backed long-term memory
  - Simulated browser environment
  - Streaming progress callbacks
"""

from __future__ import annotations

import re
import json
import sqlite3
import uuid
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class TaskStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class Task:
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    result: str = ""
    created_at: str = ""
    updated_at: str = ""


class SimulatedBrowser:
    """Simulated browser for web actions."""

    def __init__(self):
        self.history: List[str] = []
        self.current_url: Optional[str] = None

    def navigate(self, url: str) -> str:
        self.current_url = url
        self.history.append(url)
        return f"Navigated to {url}. Simulated page content for {url}."

    def search(self, query: str) -> str:
        self.history.append(f"search:{query}")
        return f"Search results for '{query}': [Result 1] ... [Result 2] ... [Result 3] ..."

    def extract_text(self) -> str:
        return f"Extracted text from {self.current_url}. Simulated content."


class LongTermMemory:
    """SQLite-backed memory for agent persistence."""

    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS memory ("
            "id TEXT PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp TEXT)"
        )
        conn.commit()
        conn.close()

    def add(self, session_id: str, role: str, content: str) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO memory VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, role, content, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_context(self, session_id: str, limit: int = 20) -> List[Dict[str, str]]:
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT role, content, timestamp FROM memory WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        conn.close()
        return [{"role": r, "content": c, "timestamp": t} for r, c, t in reversed(rows)]


class AutonomousAgent:
    """
    Autonomous agent with goal decomposition and ReAct execution.
    """

    def __init__(
        self,
        name: str = "AgentGPT-Native",
        llm_call: Optional[Callable[[str], str]] = None,
        browser: Optional[SimulatedBrowser] = None,
        memory: Optional[LongTermMemory] = None,
    ):
        self.name = name
        self.llm_call = llm_call or self._default_llm
        self.browser = browser or SimulatedBrowser()
        self.memory = memory or LongTermMemory()
        self.tasks: Dict[str, Task] = {}
        self.session_id = str(uuid.uuid4())
        self.max_iterations = 10

    def _default_llm(self, prompt: str) -> str:
        return f"[LLM] {prompt[:80]}..."

    def set_goal(self, goal: str) -> Task:
        root = Task(
            id=f"task-{uuid.uuid4().hex[:8]}",
            description=goal,
            status=TaskStatus.IN_PROGRESS,
            created_at=datetime.utcnow().isoformat(),
        )
        self.tasks[root.id] = root
        self.memory.add(self.session_id, "system", f"Goal set: {goal}")
        return root

    def decompose(self, task: Task) -> List[Task]:
        prompt = (
            f"You are an autonomous agent. Break the following task into 3-5 subtasks. "
            f"Output format: [Subtask N] <description>.\n\nTask: {task.description}\n"
        )
        raw = self.llm_call(prompt)
        subtasks: List[Task] = []
        pattern = re.compile(r"\[Subtask\s*(\d+)\]\s*(.+)")
        for m in pattern.finditer(raw):
            st = Task(
                id=f"task-{uuid.uuid4().hex[:8]}",
                description=m.group(2).strip(),
                parent_id=task.id,
                created_at=datetime.utcnow().isoformat(),
            )
            subtasks.append(st)
            self.tasks[st.id] = st
        task.subtasks = [st.id for st in subtasks]
        return subtasks

    def execute_task(self, task: Task) -> str:
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.utcnow().isoformat()
        self.memory.add(self.session_id, "user", f"Execute: {task.description}")

        # ReAct loop
        for i in range(self.max_iterations):
            context = self.memory.get_context(self.session_id, limit=10)
            ctx_str = "\n".join([f"{c['role']}: {c['content']}" for c in context])
            prompt = (
                f"You are {self.name}. Based on the conversation history, decide the next action.\n\n"
                f"History:\n{ctx_str}\n\n"
                f"Task: {task.description}\n\n"
                f"Available actions: [think], [search <query>], [navigate <url>], [extract], [done <result>]\n"
                f"Action:"
            )
            action = self.llm_call(prompt)
            self.memory.add(self.session_id, "assistant", action)

            if action.startswith("[done]"):
                result = action[6:].strip() if len(action) > 6 else "completed"
                task.result = result
                task.status = TaskStatus.COMPLETED
                return result
            elif action.startswith("[search]"):
                query = action[8:].strip()
                result = self.browser.search(query)
                self.memory.add(self.session_id, "tool", f"Search result: {result}")
            elif action.startswith("[navigate]"):
                url = action[10:].strip()
                result = self.browser.navigate(url)
                self.memory.add(self.session_id, "tool", f"Browser: {result}")
            elif action.startswith("[extract]"):
                result = self.browser.extract_text()
                self.memory.add(self.session_id, "tool", f"Extracted: {result}")
            else:
                self.memory.add(self.session_id, "assistant", f"Thought: {action}")

        task.status = TaskStatus.FAILED
        return "Max iterations reached"

    def run(self, goal: str) -> Dict[str, Any]:
        root = self.set_goal(goal)
        subtasks = self.decompose(root)
        for st in subtasks:
            self.execute_task(st)
        # Aggregate results
        completed = sum(1 for st in subtasks if self.tasks[st.id].status == TaskStatus.COMPLETED)
        return {
            "goal": goal,
            "session_id": self.session_id,
            "total_subtasks": len(subtasks),
            "completed": completed,
            "failed": len(subtasks) - completed,
            "results": {st.id: self.tasks[st.id].result for st in subtasks},
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "tasks": {tid: {"desc": t.description, "status": t.status.name} for tid, t in self.tasks.items()},
            "browser_history": self.browser.history,
            "memory_count": len(self.memory.get_context(self.session_id, limit=1000)),
        }


# --- Standalone test ---
if __name__ == "__main__":
    agent = AutonomousAgent()
    result = agent.run("Research the latest trends in AI agents and summarize findings.")
    print(f"Goal: {result['goal']}")
    print(f"Completed {result['completed']}/{result['total_subtasks']} subtasks")
    print("Status:", agent.get_status())
