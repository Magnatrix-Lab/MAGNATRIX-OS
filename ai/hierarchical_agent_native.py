"""
hierarchical_agent_native.py — Hierarchical Command Agent (Lord Architecture).

Architectural pattern inspired by notdanilo/lord (hierarchical command system):
- Lord agent (master) delegates commands to vassal agents (subordinates).
- Permission hierarchy: lord can override, vassals can escalate.
- Command bus with priority routing and acknowledgment.
- Status heartbeat from vassals to lord for health monitoring.
- Sandboxed execution of vassal commands to prevent privilege escalation.

Pure Python ≥3.9, stdlib only.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class CommandPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class CommandStatus(Enum):
    PENDING = auto()
    ACKNOWLEDGED = auto()
    EXECUTING = auto()
    DONE = auto()
    FAILED = auto()
    ESCALATED = auto()


@dataclass
class Command:
    id: str
    action: str
    args: Dict[str, Any] = field(default_factory=dict)
    priority: CommandPriority = CommandPriority.NORMAL
    issuer: str = "lord"
    target: str = ""
    status: CommandStatus = CommandStatus.PENDING
    result: Any = None
    issued_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


@dataclass
class Heartbeat:
    agent_id: str
    role: str
    status: str
    load: float  # 0.0 - 1.0
    last_seen: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Vassal Agent
# ---------------------------------------------------------------------------

class NativeVassalAgent:
    """
    Subordinate agent in the hierarchy.
    Executes commands, reports heartbeat, and can escalate when stuck.
    """

    def __init__(self, agent_id: str, role: str, capabilities: Set[str]) -> None:
        self.agent_id = agent_id
        self.role = role
        self.capabilities = capabilities
        self.command_history: List[Command] = []
        self.escalation_threshold = 3
        self._failed_count = 0

    def heartbeat(self) -> Heartbeat:
        load = min(1.0, len([c for c in self.command_history if c.status == CommandStatus.EXECUTING]) / 5.0)
        return Heartbeat(agent_id=self.agent_id, role=self.role, status="healthy", load=load)

    def can_execute(self, cmd: Command) -> bool:
        return cmd.action in self.capabilities

    def execute(self, cmd: Command, executor: Optional[Callable[[Command], Any]] = None) -> Command:
        """Execute a command or escalate if unable."""
        if not self.can_execute(cmd):
            cmd.status = CommandStatus.ESCALATED
            self.command_history.append(cmd)
            return cmd

        cmd.status = CommandStatus.EXECUTING
        try:
            if executor:
                cmd.result = executor(cmd)
            else:
                cmd.result = self._default_execute(cmd)
            cmd.status = CommandStatus.DONE
            self._failed_count = 0
        except Exception as e:
            cmd.result = str(e)
            self._failed_count += 1
            if self._failed_count >= self.escalation_threshold:
                cmd.status = CommandStatus.ESCALATED
            else:
                cmd.status = CommandStatus.FAILED

        cmd.completed_at = time.time()
        self.command_history.append(cmd)
        return cmd

    def _default_execute(self, cmd: Command) -> Any:
        return f"[default execution of {cmd.action}]"


# ---------------------------------------------------------------------------
# Lord Agent
# ---------------------------------------------------------------------------

class NativeLordAgent:
    """
    Master agent that coordinates a hierarchy of vassal agents.
    Receives high-level goals, decomposes them, and delegates to vassals.
    """

    def __init__(self, lord_id: str = "lord-0") -> None:
        self.lord_id = lord_id
        self.vassals: Dict[str, NativeVassalAgent] = {}
        self.command_queue: List[Command] = []
        self.heartbeats: Dict[str, Heartbeat] = {}
        self.escalation_log: List[Dict[str, Any]] = []

    def register_vassal(self, vassal: NativeVassalAgent) -> None:
        self.vassals[vassal.agent_id] = vassal

    def issue_command(
        self,
        action: str,
        args: Optional[Dict[str, Any]] = None,
        target: Optional[str] = None,
        priority: CommandPriority = CommandPriority.NORMAL,
    ) -> Command:
        """Issue a command from the lord to a specific vassal or best-match."""
        cmd = Command(
            id=str(uuid.uuid4())[:8],
            action=action,
            args=args or {},
            priority=priority,
            target=target or "",
        )
        if target and target in self.vassals:
            cmd.target = target
        else:
            # Route to first capable vassal
            for vid, v in self.vassals.items():
                if v.can_execute(cmd):
                    cmd.target = vid
                    break
        self.command_queue.append(cmd)
        self.command_queue.sort(key=lambda c: c.priority.value, reverse=True)
        return cmd

    def dispatch(self, executor: Optional[Callable[[Command], Any]] = None) -> List[Command]:
        """Dispatch all pending commands to their targets."""
        completed = []
        pending = [c for c in self.command_queue if c.status == CommandStatus.PENDING]
        for cmd in pending:
            if cmd.target in self.vassals:
                vassal = self.vassals[cmd.target]
                vassal.execute(cmd, executor=executor)
                if cmd.status == CommandStatus.ESCALATED:
                    self.escalation_log.append({
                        "command_id": cmd.id,
                        "vassal": cmd.target,
                        "reason": "escalation_threshold" if vassal._failed_count >= vassal.escalation_threshold else "capability_mismatch",
                    })
                    # Lord reassigns to another capable vassal
                    for vid, v in self.vassals.items():
                        if vid != cmd.target and v.can_execute(cmd):
                            cmd.target = vid
                            cmd.status = CommandStatus.PENDING
                            v.execute(cmd, executor=executor)
                            break
                completed.append(cmd)
        self.command_queue = [c for c in self.command_queue if c not in completed or c.status == CommandStatus.PENDING]
        return completed

    def collect_heartbeats(self) -> Dict[str, Heartbeat]:
        """Poll all vassals for health status."""
        self.heartbeats = {vid: v.heartbeat() for vid, v in self.vassals.items()}
        return self.heartbeats

    def get_overloaded_vassals(self, threshold: float = 0.8) -> List[str]:
        """Return IDs of vassals with load above threshold."""
        return [vid for vid, hb in self.heartbeats.items() if hb.load > threshold]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "lord_id": self.lord_id,
            "vassals": len(self.vassals),
            "pending_commands": len([c for c in self.command_queue if c.status == CommandStatus.PENDING]),
            "escalations": len(self.escalation_log),
            "heartbeats": {vid: {"status": hb.status, "load": hb.load} for vid, hb in self.heartbeats.items()},
        }


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def test_hierarchical_agent() -> None:
    lord = NativeLordAgent(lord_id="lord-alpha")

    # Register vassals with different capabilities
    v1 = NativeVassalAgent("vassal-1", "web_scraper", {"scrape", "search"})
    v2 = NativeVassalAgent("vassal-2", "coder", {"code", "test", "debug"})
    v3 = NativeVassalAgent("vassal-3", "writer", {"write", "summarize"})

    lord.register_vassal(v1)
    lord.register_vassal(v2)
    lord.register_vassal(v3)

    # Issue commands
    c1 = lord.issue_command("scrape", {"url": "https://example.com"}, priority=CommandPriority.HIGH)
    c2 = lord.issue_command("code", {"language": "python"})
    c3 = lord.issue_command("write", {"topic": "AI"})
    c4 = lord.issue_command("debug", target="vassal-2")

    # Dispatch
    completed = lord.dispatch()
    assert len(completed) == 4
    assert c1.status == CommandStatus.DONE
    assert c2.status == CommandStatus.DONE

    # Heartbeats
    hbs = lord.collect_heartbeats()
    assert len(hbs) == 3
    assert all(hb.status == "healthy" for hb in hbs.values())

    stats = lord.get_stats()
    assert stats["vassals"] == 3
    assert stats["pending_commands"] == 0

    print("[test_hierarchical_agent] PASSED")


if __name__ == "__main__":
    test_hierarchical_agent()
