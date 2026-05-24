#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Task Manager (Layer 6 Extension)
Inspired by: itseffi/agentic-os Tasks/
YAML-frontmatter task system with progress tracking, status transitions,
dependency chains, and backlog deduplication.
================================================================================
Zero-dependency task management using regex YAML parsing + markdown body.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple


# =============================================================================
# Constants
# =============================================================================
TASKS_DIR = "/tmp/magnatrix_tasks"


# =============================================================================
# Data Types
# =============================================================================
class TaskStatus(Enum):
    NOT_STARTED = "n"
    STARTED = "s"
    BLOCKED = "b"
    DONE = "d"
    CANCELLED = "c"


class TaskPriority(Enum):
    P0 = "P0"  # Critical
    P1 = "P1"  # Important
    P2 = "P2"  # Normal
    P3 = "P3"  # Low


@dataclass
class TaskLogEntry:
    timestamp: float
    message: str


@dataclass
class Task:
    task_id: str
    title: str
    category: str = "other"
    priority: TaskPriority = TaskPriority.P2
    status: TaskStatus = TaskStatus.NOT_STARTED
    created_at: float = field(default_factory=time.time)
    due_date: str = ""
    estimated_time_min: int = 0
    resource_refs: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    body: str = ""
    checklist: List[Dict[str, Any]] = field(default_factory=list)
    log: List[TaskLogEntry] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    assigned_agent: str = ""


# =============================================================================
# YAML Frontmatter Parser
# =============================================================================
class TaskParser:
    """Parse task files with YAML frontmatter and markdown body."""

    FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
    LIST_RE = re.compile(r"^-\s+(.+)$", re.MULTILINE)
    KV_RE = re.compile(r"^([a-zA-Z0-9_]+):\s*(.+)$", re.MULTILINE)
    CHECKBOX_RE = re.compile(r"^-\s+\[([ x])\]\s*(.+)$", re.MULTILINE)
    LOG_RE = re.compile(r"^-\s+(\d{4}-\d{2}-\d{2}):\s*(.+)$", re.MULTILINE)

    def parse_file(self, path: str) -> Optional[Task]:
        text = Path(path).read_text(encoding="utf-8")
        return self.parse_text(text, path)

    def parse_text(self, text: str, path_hint: str = "") -> Optional[Task]:
        m = self.FRONTMATTER_RE.match(text)
        if not m:
            return None
        yaml_block, body = m.groups()
        meta: Dict[str, Any] = {}
        for k, v in self.KV_RE.findall(yaml_block):
            k = k.strip()
            v = v.strip()
            if k in ("resource_refs", "tags", "dependencies"):
                # Could be multi-line list or comma-separated
                meta[k] = [x.strip() for x in v.split(",") if x.strip()]
            elif k == "estimated_time":
                meta[k] = int(v)
            else:
                meta[k] = v
        task_id = hashlib.sha256(text.encode()).hexdigest()[:12]
        # Parse checklist
        checklist = [{"done": c[0] == "x", "text": c[1]} for c in self.CHECKBOX_RE.findall(body)]
        # Parse progress log
        log = [TaskLogEntry(timestamp=time.mktime(time.strptime(l[0], "%Y-%m-%d")), message=l[1]) for l in self.LOG_RE.findall(body)]
        # Extract title from first # header
        title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = title_match.group(1) if title_match else meta.get("title", "Untitled")
        return Task(
            task_id=task_id,
            title=title,
            category=meta.get("category", "other"),
            priority=TaskPriority(meta.get("priority", "P2")),
            status=TaskStatus(meta.get("status", "n")),
            created_at=time.mktime(time.strptime(meta.get("created_date", time.strftime("%Y-%m-%d")), "%Y-%m-%d")) if "created_date" in meta else time.time(),
            due_date=meta.get("due_date", ""),
            estimated_time_min=meta.get("estimated_time", 0),
            resource_refs=meta.get("resource_refs", []),
            dependencies=set(meta.get("dependencies", [])),
            body=body,
            checklist=checklist,
            log=log,
            tags=set(meta.get("tags", [])),
            assigned_agent=meta.get("assigned_agent", ""),
        )

    def to_text(self, task: Task) -> str:
        lines = [
            "---",
            f"title: {task.title}",
            f"category: {task.category}",
            f"priority: {task.priority.value}",
            f"status: {task.status.value}",
            f"created_date: {time.strftime('%Y-%m-%d', time.localtime(task.created_at))}",
        ]
        if task.due_date:
            lines.append(f"due_date: {task.due_date}")
        if task.estimated_time_min:
            lines.append(f"estimated_time: {task.estimated_time_min}")
        if task.resource_refs:
            lines.append(f"resource_refs: {', '.join(task.resource_refs)}")
        if task.dependencies:
            lines.append(f"dependencies: {', '.join(task.dependencies)}")
        if task.tags:
            lines.append(f"tags: {', '.join(task.tags)}")
        if task.assigned_agent:
            lines.append(f"assigned_agent: {task.assigned_agent}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {task.title}")
        lines.append("")
        lines.append("## Context")
        lines.append(task.body.split("## Context")[1].split("## Next Actions")[0].strip() if "## Context" in task.body else "")
        lines.append("")
        lines.append("## Next Actions")
        for item in task.checklist:
            mark = "x" if item["done"] else " "
            lines.append(f"- [{mark}] {item['text']}")
        lines.append("")
        lines.append("## Progress Log")
        for entry in task.log:
            lines.append(f"- {time.strftime('%Y-%m-%d', time.localtime(entry.timestamp))}: {entry.message}")
        return "\n".join(lines)


# =============================================================================
# Dedup Engine
# =============================================================================
class DedupEngine:
    """Detect duplicate/similar tasks using simple text similarity."""

    def __init__(self, threshold: float = 0.85) -> None:
        self.threshold = threshold

    def _normalize(self, text: str) -> Set[str]:
        return set(re.findall(r"[a-zA-Z]{3,}", text.lower()))

    def similarity(self, a: str, b: str) -> float:
        sa = self._normalize(a)
        sb = self._normalize(b)
        if not sa or not sb:
            return 0.0
        inter = len(sa & sb)
        union = len(sa | sb)
        return inter / union if union > 0 else 0.0

    def find_duplicates(self, tasks: List[Task], new_task: Task) -> List[Task]:
        dups = []
        for t in tasks:
            if t.task_id == new_task.task_id:
                continue
            sim = max(
                self.similarity(new_task.title, t.title),
                self.similarity(new_task.body, t.body),
            )
            if sim >= self.threshold:
                dups.append(t)
        return dups


# =============================================================================
# Task Manager
# =============================================================================
class TaskManager:
    """CRUD, search, filter, and orchestrate tasks."""

    def __init__(self, tasks_dir: str = TASKS_DIR) -> None:
        self.tasks_dir = Path(tasks_dir)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self._parser = TaskParser()
        self._dedup = DedupEngine()
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._callbacks: Dict[str, List[Callable[[Task], None]]] = {
            "created": [],
            "updated": [],
            "completed": [],
        }
        self._load_all()

    def _load_all(self) -> None:
        for p in sorted(self.tasks_dir.glob("*.md")):
            t = self._parser.parse_file(str(p))
            if t:
                self._tasks[t.task_id] = t

    def _save(self, task: Task) -> None:
        safe_name = re.sub(r"[^\w-]", "_", task.title.lower())[:50]
        path = self.tasks_dir / f"{safe_name}_{task.task_id[:6]}.md"
        path.write_text(self._parser.to_text(task), encoding="utf-8")

    def _on(self, event: str, task: Task) -> None:
        for cb in self._callbacks.get(event, []):
            cb(task)

    def on(self, event: str, callback: Callable[[Task], None]) -> None:
        self._callbacks.setdefault(event, []).append(callback)

    def create(self, text: str) -> Tuple[Task, List[Task]]:
        """Create task, return (task, duplicates)."""
        task = self._parser.parse_text(text)
        if not task:
            raise ValueError("Invalid task format")
        dups = self._dedup.find_duplicates(list(self._tasks.values()), task)
        with self._lock:
            self._tasks[task.task_id] = task
            self._save(task)
        self._on("created", task)
        return task, dups

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update_status(self, task_id: str, status: TaskStatus) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        old = task.status
        task.status = status
        if status == TaskStatus.DONE and old != TaskStatus.DONE:
            task.log.append(TaskLogEntry(timestamp=time.time(), message="Marked as done"))
            self._on("completed", task)
        else:
            task.log.append(TaskLogEntry(timestamp=time.time(), message=f"Status: {old.value} → {status.value}"))
            self._on("updated", task)
        with self._lock:
            self._save(task)
        return True

    def update_checklist(self, task_id: str, index: int, done: bool) -> bool:
        task = self._tasks.get(task_id)
        if not task or index >= len(task.checklist):
            return False
        task.checklist[index]["done"] = done
        with self._lock:
            self._save(task)
        return True

    def add_log(self, task_id: str, message: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.log.append(TaskLogEntry(timestamp=time.time(), message=message))
        with self._lock:
            self._save(task)
        return True

    def delete(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.pop(task_id, None)
            if task:
                safe_name = re.sub(r"[^\w-]", "_", task.title.lower())[:50]
                path = self.tasks_dir / f"{safe_name}_{task.task_id[:6]}.md"
                path.unlink(missing_ok=True)
                return True
            return False

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        category: Optional[str] = None,
        agent: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Task]:
        result = list(self._tasks.values())
        if status:
            result = [t for t in result if t.status == status]
        if priority:
            result = [t for t in result if t.priority == priority]
        if category:
            result = [t for t in result if t.category == category]
        if agent:
            result = [t for t in result if t.assigned_agent == agent]
        if tag:
            result = [t for t in result if tag in t.tags]
        # Sort: P0 first, then by created_at desc
        priority_order = {TaskPriority.P0: 0, TaskPriority.P1: 1, TaskPriority.P2: 2, TaskPriority.P3: 3}
        result.sort(key=lambda t: (priority_order.get(t.priority, 99), -t.created_at))
        return result

    def get_ready_tasks(self) -> List[Task]:
        """Tasks that are not started and have all dependencies done."""
        done_ids = {t.task_id for t in self._tasks.values() if t.status == TaskStatus.DONE}
        ready = []
        for t in self._tasks.values():
            if t.status == TaskStatus.NOT_STARTED and t.dependencies.issubset(done_ids):
                ready.append(t)
        return ready

    def summary(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for s in TaskStatus:
            counts[s.value] = sum(1 for t in self._tasks.values() if t.status == s)
        return {
            "total": len(self._tasks),
            "by_status": counts,
            "by_priority": {
                p.value: sum(1 for t in self._tasks.values() if t.priority == p)
                for p in TaskPriority
            },
            "ready": len(self.get_ready_tasks()),
            "blocked": sum(1 for t in self._tasks.values() if t.status == TaskStatus.BLOCKED),
        }

    def search(self, query: str) -> List[Task]:
        q = query.lower()
        return [t for t in self._tasks.values() if q in t.title.lower() or q in t.body.lower() or q in " ".join(t.tags)]

    def process_backlog(self) -> Dict[str, Any]:
        """Auto-process backlog: dedup, unblock, re-prioritize."""
        ready = self.get_ready_tasks()
        blocked = [t for t in self._tasks.values() if t.status == TaskStatus.BLOCKED]
        # Unblock if dependencies done
        unblocked = 0
        done_ids = {t.task_id for t in self._tasks.values() if t.status == TaskStatus.DONE}
        for t in blocked:
            if t.dependencies.issubset(done_ids):
                self.update_status(t.task_id, TaskStatus.NOT_STARTED)
                unblocked += 1
        return {
            "ready": len(ready),
            "unblocked": unblocked,
            "total": len(self._tasks),
        }


# =============================================================================
# Task Kernel Bridge
# =============================================================================
class TaskKernelBridge:
    def __init__(self, manager: TaskManager, event_bus: Any = None) -> None:
        self.manager = manager
        self.bus = event_bus
        manager.on("created", self._on_created)
        manager.on("updated", self._on_updated)
        manager.on("completed", self._on_completed)

    def _on_created(self, task: Task) -> None:
        if self.bus:
            self.bus.publish("task.created", {"id": task.task_id, "title": task.title, "priority": task.priority.value})

    def _on_updated(self, task: Task) -> None:
        if self.bus:
            self.bus.publish("task.updated", {"id": task.task_id, "status": task.status.value})

    def _on_completed(self, task: Task) -> None:
        if self.bus:
            self.bus.publish("task.completed", {"id": task.task_id, "title": task.title})


# =============================================================================
# MCP-style Tool Interface
# =============================================================================
class TaskTools:
    """Structured tools for AI agents to interact with tasks."""

    def __init__(self, manager: TaskManager) -> None:
        self.manager = manager

    def list_tasks(self, status: Optional[str] = None, priority: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        s = TaskStatus(status) if status else None
        p = TaskPriority(priority) if priority else None
        tasks = self.manager.list_tasks(status=s, priority=p, category=category)
        return [self._to_dict(t) for t in tasks]

    def create_task(self, markdown: str) -> Dict[str, Any]:
        task, dups = self.manager.create(markdown)
        return {
            "task": self._to_dict(task),
            "duplicates": [self._to_dict(d) for d in dups],
        }

    def update_task_status(self, task_id: str, status: str) -> bool:
        return self.manager.update_status(task_id, TaskStatus(status))

    def get_task_summary(self) -> Dict[str, Any]:
        return self.manager.summary()

    def process_backlog_with_dedup(self) -> Dict[str, Any]:
        return self.manager.process_backlog()

    def _to_dict(self, task: Task) -> Dict[str, Any]:
        return {
            "id": task.task_id,
            "title": task.title,
            "category": task.category,
            "priority": task.priority.value,
            "status": task.status.value,
            "due_date": task.due_date,
            "estimated_time_min": task.estimated_time_min,
            "checklist": task.checklist,
            "log_count": len(task.log),
            "tags": list(task.tags),
            "agent": task.assigned_agent,
        }


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Task Manager Demo")
    print("=" * 60)
    tm = TaskManager("/tmp/magnatrix_demo_tasks")
    md = """---
title: Implement Raft consensus
category: technical
priority: P0
status: n
created_date: 2026-05-24
estimated_time: 240
resource_refs: Knowledge/distributed-systems.md
dependencies: task-abc123
assigned_agent: governance-agent
---
# Implement Raft consensus

## Context
Need leader election and log replication for distributed governance.

## Next Actions
- [ ] Design state machine
- [ ] Implement RequestVote RPC
- [ ] Implement AppendEntries RPC
- [ ] Add BFT voting overlay

## Progress Log
"""
    task, dups = tm.create(md)
    print(f"Created task: {task.title} ({task.task_id})")
    print(f"Duplicates found: {len(dups)}")
    tm.update_status(task.task_id, TaskStatus.STARTED)
    tm.update_checklist(task.task_id, 0, True)
    tm.add_log(task.task_id, "Designed state machine on whiteboard")
    print(f"Summary: {tm.summary()}")
    tools = TaskTools(tm)
    print(f"Ready tasks: {len(tools.list_tasks())}")
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
