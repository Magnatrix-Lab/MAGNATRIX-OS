"""Context Switcher — Multi-context management, task switching, and state preservation.

Modul ini menyediakan:
- ContextSession untuk single context/session state
- ContextSwitcher untuk switch between contexts
- StatePreserver untuk save/restore context state
- TaskRouter untuk route tasks to appropriate context
- MultiContextManager untuk manage all active contexts
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ContextPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ContextState(Enum):
    ACTIVE = auto()
    SUSPENDED = auto()
    ARCHIVED = auto()
    TERMINATED = auto()


@dataclass
class ContextSession:
    """Single context/session."""
    session_id: str
    name: str
    context_type: str = "general"
    messages: List[Dict[str, str]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    priority: ContextPriority = ContextPriority.NORMAL
    state: ContextState = ContextState.ACTIVE
    max_tokens: int = 4096
    current_tokens: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        self.current_tokens += len(content) // 4 + 4
        self.last_accessed = time.time()

    def get_recent(self, n: int = 10) -> List[Dict[str, str]]:
        return self.messages[-n:]

    def is_full(self) -> bool:
        return self.current_tokens >= self.max_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "type": self.context_type,
            "messages": len(self.messages),
            "tokens": self.current_tokens,
            "priority": self.priority.name,
            "state": self.state.name,
        }


class StatePreserver:
    """Save and restore context state."""

    def __init__(self):
        self._snapshots: Dict[str, Dict[str, Any]] = {}

    def save(self, session: ContextSession) -> str:
        snapshot_id = str(uuid.uuid4())[:12]
        self._snapshots[snapshot_id] = {
            "session_id": session.session_id,
            "messages": list(session.messages),
            "variables": dict(session.variables),
            "tokens": session.current_tokens,
            "saved_at": time.time(),
        }
        return snapshot_id

    def restore(self, session: ContextSession, snapshot_id: str) -> bool:
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return False
        session.messages = list(snapshot["messages"])
        session.variables = dict(snapshot["variables"])
        session.current_tokens = snapshot["tokens"]
        return True

    def list_snapshots(self, session_id: str) -> List[str]:
        return [sid for sid, snap in self._snapshots.items() if snap.get("session_id") == session_id]

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._snapshots, f, indent=2)


class TaskRouter:
    """Route tasks to appropriate context."""

    def __init__(self):
        self._rules: List[Tuple[str, Callable[[str], bool], str]] = []

    def add_rule(self, name: str, matcher: Callable[[str], bool], context_type: str) -> None:
        self._rules.append((name, matcher, context_type))

    def route(self, task: str) -> str:
        for name, matcher, ctx_type in self._rules:
            if matcher(task):
                return ctx_type
        return "general"

    @staticmethod
    def default_rules() -> List[Tuple[str, Callable[[str], bool], str]]:
        return [
            ("code", lambda t: any(k in t.lower() for k in ["code", "function", "class", "def ", "python", "java"]), "coding"),
            ("math", lambda t: any(k in t.lower() for k in ["math", "calculate", "solve", "equation", "integral"]), "math"),
            ("writing", lambda t: any(k in t.lower() for k in ["write", "essay", "article", "story"]), "writing"),
            ("analysis", lambda t: any(k in t.lower() for k in ["analyze", "compare", "evaluate"]), "analysis"),
        ]


class MultiContextManager:
    """Manage multiple active contexts."""

    def __init__(self, max_contexts: int = 10):
        self.max_contexts = max_contexts
        self._contexts: Dict[str, ContextSession] = {}
        self._preserver = StatePreserver()
        self._router = TaskRouter()
        for name, matcher, ctx_type in TaskRouter.default_rules():
            self._router.add_rule(name, matcher, ctx_type)
        self._active: Optional[str] = None

    def create(self, name: str, context_type: str = "general", priority: ContextPriority = ContextPriority.NORMAL,
               max_tokens: int = 4096) -> ContextSession:
        self._evict_if_needed()
        session = ContextSession(
            session_id=str(uuid.uuid4())[:12],
            name=name,
            context_type=context_type,
            priority=priority,
            max_tokens=max_tokens,
        )
        self._contexts[session.session_id] = session
        self._active = session.session_id
        return session

    def get(self, session_id: str) -> Optional[ContextSession]:
        ctx = self._contexts.get(session_id)
        if ctx:
            ctx.last_accessed = time.time()
        return ctx

    def get_active(self) -> Optional[ContextSession]:
        if self._active:
            return self.get(self._active)
        return None

    def switch(self, session_id: str) -> bool:
        if session_id in self._contexts:
            # Save current
            if self._active:
                current = self._contexts.get(self._active)
                if current:
                    current.state = ContextState.SUSPENDED
            # Switch
            self._active = session_id
            new_ctx = self._contexts[session_id]
            new_ctx.state = ContextState.ACTIVE
            return True
        return False

    def route_task(self, task: str) -> ContextSession:
        context_type = self._router.route(task)
        # Find existing context of same type or create new
        for ctx in self._contexts.values():
            if ctx.context_type == context_type and ctx.state == ContextState.ACTIVE:
                return ctx
        return self.create(f"auto-{context_type}", context_type)

    def suspend(self, session_id: str) -> bool:
        ctx = self._contexts.get(session_id)
        if ctx:
            ctx.state = ContextState.SUSPENDED
            self._preserver.save(ctx)
            return True
        return False

    def resume(self, session_id: str) -> bool:
        ctx = self._contexts.get(session_id)
        if ctx:
            ctx.state = ContextState.ACTIVE
            self._active = session_id
            return True
        return False

    def terminate(self, session_id: str) -> bool:
        ctx = self._contexts.pop(session_id, None)
        if ctx:
            ctx.state = ContextState.TERMINATED
            if self._active == session_id:
                self._active = None
            return True
        return False

    def _evict_if_needed(self) -> None:
        while len(self._contexts) >= self.max_contexts:
            # Remove oldest suspended context
            suspended = [(sid, c) for sid, c in self._contexts.items() if c.state == ContextState.SUSPENDED]
            if suspended:
                oldest = min(suspended, key=lambda x: x[1].last_accessed)
                self._contexts.pop(oldest[0])
            else:
                # Remove oldest overall
                oldest = min(self._contexts.keys(), key=lambda k: self._contexts[k].last_accessed)
                self._contexts.pop(oldest)

    def get_all(self) -> List[ContextSession]:
        return list(self._contexts.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_contexts": len(self._contexts),
            "active": sum(1 for c in self._contexts.values() if c.state == ContextState.ACTIVE),
            "suspended": sum(1 for c in self._contexts.values() if c.state == ContextState.SUSPENDED),
            "current_active": self._active,
        }

    def export_all(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "contexts": [c.to_dict() for c in self._contexts.values()],
                "stats": self.get_stats(),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CONTEXT SWITCHER DEMO")
    print("=" * 70)

    manager = MultiContextManager(max_contexts=5)

    # 1. Create contexts
    print("\n[1] Create Contexts")
    ctx1 = manager.create("Coding Session", "coding", ContextPriority.HIGH, 4096)
    ctx2 = manager.create("Writing Task", "writing", ContextPriority.NORMAL, 2048)
    ctx3 = manager.create("General Chat", "general", ContextPriority.LOW, 4096)
    print(f"  Created: {ctx1.session_id[:8]} (coding), {ctx2.session_id[:8]} (writing), {ctx3.session_id[:8]} (general)")

    # 2. Add messages
    print("\n[2] Add Messages")
    ctx1.add_message("user", "Write a Python function to sort a list")
    ctx1.add_message("assistant", "Here's a Python function: def sort_list(arr): return sorted(arr)")
    ctx2.add_message("user", "Write an essay about climate change")
    ctx2.add_message("assistant", "Climate change is one of the most pressing issues...")
    print(f"  Coding: {len(ctx1.messages)} messages, {ctx1.current_tokens} tokens")
    print(f"  Writing: {len(ctx2.messages)} messages, {ctx2.current_tokens} tokens")

    # 3. Switch contexts
    print("\n[3] Switch Contexts")
    print(f"  Active: {manager.get_active().name}")
    manager.switch(ctx2.session_id)
    print(f"  Switched to: {manager.get_active().name}")
    manager.switch(ctx1.session_id)
    print(f"  Switched to: {manager.get_active().name}")

    # 4. Route task
    print("\n[4] Task Routing")
    for task in ["How do I write a class in Python?", "Calculate the integral of x^2", "Write a story about space"]:
        ctx = manager.route_task(task)
        print(f"  '{task[:40]}...' -> {ctx.name} ({ctx.context_type})")

    # 5. Save/Restore
    print("\n[5] Save and Restore")
    snapshot = manager._preserver.save(ctx1)
    print(f"  Saved snapshot: {snapshot}")
    ctx1.messages = []
    ctx1.current_tokens = 0
    print(f"  Cleared: {len(ctx1.messages)} messages")
    manager._preserver.restore(ctx1, snapshot)
    print(f"  Restored: {len(ctx1.messages)} messages, {ctx1.current_tokens} tokens")

    # 6. Suspend/Resume
    print("\n[6] Suspend and Resume")
    manager.suspend(ctx2.session_id)
    print(f"  Suspended: {ctx2.state.name}")
    manager.resume(ctx2.session_id)
    print(f"  Resumed: {ctx2.state.name}")

    # 7. Terminate
    print("\n[7] Terminate")
    manager.terminate(ctx3.session_id)
    print(f"  Active contexts: {len(manager.get_all())}")

    # 8. Auto-evict
    print("\n[8] Auto-evict")
    for i in range(5):
        manager.create(f"Temp-{i}", "general", ContextPriority.LOW, 1024)
    print(f"  Total contexts: {len(manager.get_all())}")

    # 9. Stats
    print(f"\n[9] Stats")
    print(f"  {manager.get_stats()}")

    # 10. Export
    print("\n[10] Export")
    manager.export_all("/tmp/contexts.json")
    print("  Exported to /tmp/contexts.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
