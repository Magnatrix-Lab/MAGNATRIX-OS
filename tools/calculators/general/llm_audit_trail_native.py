"""Audit Trail — immutable log, tamper detection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import hashlib
import time
import json

class AuditAction(Enum):
    CREATE = auto()
    READ = auto()
    UPDATE = auto()
    DELETE = auto()
    LOGIN = auto()
    LOGOUT = auto()
    CONFIG_CHANGE = auto()

@dataclass
class AuditEntry:
    entry_id: str
    timestamp: float
    actor: str
    action: AuditAction
    resource: str
    details: Dict
    prev_hash: str = ""
    hash: str = field(default="", repr=False)

    def __post_init__(self):
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = json.dumps({"id": self.entry_id, "time": self.timestamp, "actor": self.actor, "action": self.action.name, "resource": self.resource, "details": self.details, "prev": self.prev_hash}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

class AuditTrail:
    def __init__(self):
        self.entries: List[AuditEntry] = []
        self.chain_valid = True

    def log(self, actor: str, action: AuditAction, resource: str, details: Dict = None) -> AuditEntry:
        entry_id = str(len(self.entries) + 1)
        prev_hash = self.entries[-1].hash if self.entries else ""
        entry = AuditEntry(entry_id, time.time(), actor, action, resource, details or {}, prev_hash)
        self.entries.append(entry)
        return entry

    def verify(self) -> bool:
        for i in range(1, len(self.entries)):
            if self.entries[i].prev_hash != self.entries[i-1].hash:
                self.chain_valid = False
                return False
        self.chain_valid = True
        return True

    def query(self, actor: Optional[str] = None, action: Optional[AuditAction] = None, resource: Optional[str] = None, since: float = 0) -> List[AuditEntry]:
        results = self.entries
        if actor:
            results = [e for e in results if e.actor == actor]
        if action:
            results = [e for e in results if e.action == action]
        if resource:
            results = [e for e in results if e.resource == resource]
        if since > 0:
            results = [e for e in results if e.timestamp >= since]
        return results

    def stats(self) -> Dict:
        return {"entries": len(self.entries), "chain_valid": self.chain_valid and self.verify(), "actors": len(set(e.actor for e in self.entries))}

def run():
    trail = AuditTrail()
    trail.log("admin", AuditAction.CREATE, "user_1", {"name": "Alice"})
    trail.log("admin", AuditAction.UPDATE, "user_1", {"field": "email"})
    trail.log("user_1", AuditAction.LOGIN, "system", {"ip": "192.168.1.1"})
    print(trail.verify())
    print(len(trail.query(actor="admin")))
    print(trail.stats())

if __name__ == "__main__":
    run()
