"""LLM Audit Logger — Native Python (stdlib only)."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime

class AuditLevel(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

@dataclass
class AuditEntry:
    id: str
    timestamp: str
    level: AuditLevel
    user_id: str
    action: str
    resource: str
    result: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class AuditLogger:
    def __init__(self, max_entries: int = 10000) -> None:
        self.max_entries = max_entries
        self._entries: List[AuditEntry] = []

    def log(self, entry: AuditEntry) -> None:
        if len(self._entries) >= self.max_entries:
            self._entries.pop(0)
        self._entries.append(entry)

    def query(self, user_id: Optional[str] = None, level: Optional[AuditLevel] = None, resource: Optional[str] = None, limit: int = 100) -> List[AuditEntry]:
        results = self._entries
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if level:
            results = [e for e in results if e.level == level]
        if resource:
            results = [e for e in results if e.resource == resource]
        return results[-limit:]

    def export(self, path: str) -> None:
        data = [{"id": e.id, "timestamp": e.timestamp, "level": e.level.name, "user": e.user_id, "action": e.action, "resource": e.resource, "result": e.result} for e in self._entries]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for e in self._entries:
            counts[e.level.name] = counts.get(e.level.name, 0) + 1
        return {"total": len(self._entries), "by_level": counts}

def run() -> None:
    print("Audit Logger test")
    e = AuditLogger()
    e.log(AuditEntry("a1", datetime.now().isoformat(), AuditLevel.INFO, "u1", "login", "system", "success"))
    e.log(AuditEntry("a2", datetime.now().isoformat(), AuditLevel.WARNING, "u2", "delete", "file.txt", "denied"))
    e.log(AuditEntry("a3", datetime.now().isoformat(), AuditLevel.ERROR, "u1", "update", "config", "failed"))
    print("  All entries: " + str(len(e.query())))
    print("  Warnings: " + str(len(e.query(level=AuditLevel.WARNING))))
    print("  User u1: " + str(len(e.query(user_id="u1"))))
    print("  Stats: " + str(e.get_stats()))
    print("Audit Logger test complete.")

if __name__ == "__main__":
    run()
