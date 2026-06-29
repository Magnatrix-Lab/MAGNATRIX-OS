"""Sandbox Syscall Auditor — Logging, audit trail, anomaly detection."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class SyscallEvent:
    pid: int = 0
    syscall: str = ""
    args: list = None
    timestamp: float = 0.0
    blocked: bool = False

    def __post_init__(self):
        if self.args is None:
            self.args = []

class SandboxSyscallAuditor:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._events: list[SyscallEvent] = []
        self._anomaly_patterns: list[str] = ["exec", "fork", "open", "connect"]
        self._persist_path = self.root / "sandbox_audit.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._events = [SyscallEvent(**e) for e in data.get("events", [])]
            self._anomaly_patterns = data.get("anomaly_patterns", self._anomaly_patterns)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "events": [e.__dict__ for e in self._events],
            "anomaly_patterns": self._anomaly_patterns
        }, indent=2))

    def log(self, pid: int, syscall: str, args: list = None, blocked: bool = False) -> SyscallEvent:
        event = SyscallEvent(pid=pid, syscall=syscall, args=args or [], timestamp=time.time(), blocked=blocked)
        self._events.append(event)
        self._save()
        return event

    def detect_anomalies(self, pid: int | None = None) -> list[dict]:
        events = self._events if pid is None else [e for e in self._events if e.pid == pid]
        anomalies = []
        syscall_counts = {}
        for e in events:
            syscall_counts[e.syscall] = syscall_counts.get(e.syscall, 0) + 1
        for syscall, count in syscall_counts.items():
            if any(p in syscall for p in self._anomaly_patterns) and count > 100:
                anomalies.append({"syscall": syscall, "count": count, "reason": "frequency"})
        # Check for blocked bursts
        blocked_events = [e for e in events if e.blocked]
        if len(blocked_events) > 10:
            anomalies.append({"blocked_count": len(blocked_events), "reason": "blocked_burst"})
        return anomalies

    def get_trail(self, pid: int) -> list[SyscallEvent]:
        return [e for e in self._events if e.pid == pid]

    def to_dict(self) -> dict:
        return {"event_count": len(self._events), "anomaly_patterns": self._anomaly_patterns}

    def get_stats(self) -> dict:
        blocked = sum(1 for e in self._events if e.blocked)
        return {"events": len(self._events), "blocked": blocked, "unique_syscalls": len(set(e.syscall for e in self._events))}

__all__ = ["SandboxSyscallAuditor", "SyscallEvent"]
