"""
llm_audit_logger_native.py
MAGNATRIX-OS Audit Logger Engine
Native Python, stdlib only.
Provides tamper-evident audit logging with hash chaining, structured events,
access tracking, and immutable log export for compliance and forensics.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable


class AuditEventType(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    AUTHENTICATE = "authenticate"
    AUTHORIZE = "authorize"
    CONFIG_CHANGE = "config_change"
    DATA_ACCESS = "data_access"


class AuditSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    entry_id: str
    timestamp: float
    event_type: AuditEventType
    actor: str
    resource: str
    action: str
    details: Dict[str, Any]
    severity: AuditSeverity = AuditSeverity.INFO
    previous_hash: str = ""
    current_hash: str = ""
    ip_address: str = ""
    session_id: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id, "timestamp": self.timestamp,
            "event_type": self.event_type.value, "actor": self.actor,
            "resource": self.resource, "action": self.action,
            "details": self.details, "severity": self.severity.value,
            "previous_hash": self.previous_hash, "current_hash": self.current_hash,
            "ip_address": self.ip_address, "session_id": self.session_id,
            "tags": self.tags,
        }

    def compute_hash(self) -> str:
        data = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()


class AuditLoggerEngine:
    """
    Tamper-evident audit logger with hash chaining for immutable records.
    """

    def __init__(self, service_name: str = "magnatrix") -> None:
        self.service_name = service_name
        self._entries: List[AuditEntry] = []
        self._last_hash: str = "0" * 64
        self._handlers: List[Callable[[AuditEntry], None]] = []
        self._filters: List[Callable[[AuditEntry], bool]] = []
        self._entry_counter = 0

    def log(self, event_type: AuditEventType, actor: str, resource: str, action: str,
            details: Dict[str, Any], severity: AuditSeverity = AuditSeverity.INFO,
            ip_address: str = "", session_id: str = "", tags: Optional[List[str]] = None) -> AuditEntry:
        self._entry_counter += 1
        entry_id = f"{self.service_name}_{int(time.time() * 1000)}_{self._entry_counter}"
        entry = AuditEntry(
            entry_id=entry_id, timestamp=time.time(), event_type=event_type,
            actor=actor, resource=resource, action=action, details=details,
            severity=severity, previous_hash=self._last_hash,
            ip_address=ip_address, session_id=session_id, tags=tags or []
        )
        entry.current_hash = entry.compute_hash()
        self._last_hash = entry.current_hash
        self._entries.append(entry)

        for handler in self._handlers:
            try:
                handler(entry)
            except Exception:
                pass
        return entry

    def verify_chain(self) -> List[Dict[str, Any]]:
        errors = []
        for i in range(1, len(self._entries)):
            prev = self._entries[i - 1]
            curr = self._entries[i]
            if curr.previous_hash != prev.current_hash:
                errors.append({
                    "entry_id": curr.entry_id,
                    "expected_previous": prev.current_hash,
                    "actual_previous": curr.previous_hash,
                })
            expected_hash = curr.compute_hash()
            if curr.current_hash != expected_hash:
                errors.append({
                    "entry_id": curr.entry_id,
                    "expected_hash": expected_hash,
                    "actual_hash": curr.current_hash,
                })
        return errors

    def get_entries(self, event_type: Optional[AuditEventType] = None,
                    actor: Optional[str] = None, resource: Optional[str] = None,
                    severity: Optional[AuditSeverity] = None, limit: int = 100) -> List[AuditEntry]:
        entries = self._entries
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        if actor:
            entries = [e for e in entries if e.actor == actor]
        if resource:
            entries = [e for e in entries if e.resource == resource]
        if severity:
            entries = [e for e in entries if e.severity == severity]
        return entries[-limit:]

    def add_handler(self, handler: Callable[[AuditEntry], None]) -> None:
        self._handlers.append(handler)

    def add_filter(self, filter_fn: Callable[[AuditEntry], bool]) -> None:
        self._filters.append(filter_fn)

    def get_stats(self) -> Dict[str, Any]:
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for e in self._entries:
            by_type[e.event_type.value] = by_type.get(e.event_type.value, 0) + 1
            by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1
        return {
            "total_entries": len(self._entries),
            "by_type": by_type,
            "by_severity": by_severity,
            "chain_integrity": len(self.verify_chain()) == 0,
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._entries], f, indent=2, default=str)

    def export_filtered(self, path: str, event_type: Optional[AuditEventType] = None,
                        severity: Optional[AuditSeverity] = None) -> None:
        entries = self.get_entries(event_type=event_type, severity=severity)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in entries], f, indent=2, default=str)

    def clear(self) -> None:
        self._entries.clear()
        self._last_hash = "0" * 64


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Audit Logger Engine")
    print("=" * 60)

    logger = AuditLoggerEngine(service_name="magnatrix_llm")

    # Add handler
    def alert_handler(entry: AuditEntry) -> None:
        if entry.severity == AuditSeverity.CRITICAL:
            print(f"  [CRITICAL AUDIT] {entry.actor} {entry.action} {entry.resource}")

    logger.add_handler(alert_handler)

    print("\n--- Logging events ---")
    logger.log(AuditEventType.AUTHENTICATE, "user_A", "auth_service", "login",
               {"method": "api_key"}, AuditSeverity.INFO, "10.0.0.1", "sess_123")
    logger.log(AuditEventType.DATA_ACCESS, "user_A", "dataset_customers", "read",
               {"rows": 1000}, AuditSeverity.INFO, "10.0.0.1", "sess_123")
    logger.log(AuditEventType.CONFIG_CHANGE, "admin_B", "llm_config", "update_temperature",
               {"old": 0.7, "new": 1.0}, AuditSeverity.WARNING, "10.0.0.2", "sess_456")
    logger.log(AuditEventType.DELETE, "user_C", "model_v1", "delete_model",
               {"model_id": "m1"}, AuditSeverity.CRITICAL, "10.0.0.3", "sess_789")
    logger.log(AuditEventType.EXECUTE, "user_A", "prompt_engine", "generate",
               {"tokens_in": 50, "tokens_out": 200}, AuditSeverity.INFO, "10.0.0.1", "sess_123")

    print(f"\n--- Total entries: {len(logger._entries)} ---")

    print("\n--- Chain Verification ---")
    errors = logger.verify_chain()
    print(f"  Integrity errors: {len(errors)}")
    if errors:
        for e in errors:
            print(f"    {e}")

    print("\n--- Stats ---")
    stats = logger.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n--- Filter by actor 'user_A' ---")
    entries = logger.get_entries(actor="user_A")
    for e in entries:
        print(f"  {e.event_type.value}: {e.action} on {e.resource}")

    print("\n--- Filter by CRITICAL severity ---")
    critical = logger.get_entries(severity=AuditSeverity.CRITICAL)
    for e in critical:
        print(f"  {e.actor} -> {e.action}: {e.details}")

    print("\nAudit Logger test complete.")


if __name__ == "__main__":
    run()
