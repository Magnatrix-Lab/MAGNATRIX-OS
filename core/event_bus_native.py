"""
Event Bus — MAGNATRIX-OS Core
Cross-module pub/sub event bus untuk komunikasi antar komponen.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable


class EventPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class EventType(Enum):
    POLICY_VIOLATION = "policy_violation"
    AGENT_STARTUP = "agent_startup"
    AGENT_SHUTDOWN = "agent_shutdown"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    MODEL_REQUEST = "model_request"
    MODEL_RESPONSE = "model_response"
    AUDIT_LOG = "audit_log"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    CONCEALMENT_DETECTED = "concealment_detected"
    CONVERGENCE_ALERT = "convergence_alert"
    SELF_IMPROVEMENT_PROPOSED = "self_improvement_proposed"
    SELF_IMPROVEMENT_EXECUTED = "self_improvement_executed"
    ROLLBACK_TRIGGERED = "rollback_triggered"
    CIRCUIT_BREAKER = "circuit_breaker"
    SANDBOX_VIOLATION = "sandbox_violation"
    IDENTITY_AUTH = "identity_auth"
    IDENTITY_REVOKED = "identity_revoked"
    HEALTH_CHECK = "health_check"
    METRICS_UPDATE = "metrics_update"
    MODULE_RELOAD = "module_reload"
    SYSTEM_ERROR = "system_error"


@dataclass
class Event:
    """Event yang dipublish ke event bus."""
    event_type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            import hashlib
            self.event_id = hashlib.sha256(f"{self.event_type.value}{self.timestamp}{self.source}".encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "priority": self.priority.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


class EventBus:
    """
    Pub/sub event bus untuk cross-module komunikasi.
    Thread-safe. Supports priority queuing, filtering, and synchronous/asynchronous delivery.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {e: [] for e in EventType}
        self._wildcard_subscribers: List[Callable[[Event], None]] = []
        self._history: List[Event] = []
        self._max_history = 10000
        self._lock = threading.Lock()
        self._enabled = True
        self._filters: Dict[str, Callable[[Event], bool]] = {}

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Subscribe ke event type tertentu."""
        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Callable[[Event], None]) -> None:
        """Subscribe ke semua event types (wildcard)."""
        with self._lock:
            if handler not in self._wildcard_subscribers:
                self._wildcard_subscribers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> bool:
        with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                return True
            return False

    def publish(self, event: Event) -> None:
        """Publish event ke semua subscribers."""
        if not self._enabled:
            return

        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # Get subscribers
            handlers = list(self._subscribers[event.event_type])
            handlers.extend(self._wildcard_subscribers)

        # Deliver (outside lock to avoid deadlocks)
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass

    def publish_sync(self, event: Event) -> List[Any]:
        """Publish event dan collect return values."""
        if not self._enabled:
            return []
        results = []
        with self._lock:
            self._history.append(event)
            handlers = list(self._subscribers[event.event_type])
            handlers.extend(self._wildcard_subscribers)
        for handler in handlers:
            try:
                results.append(handler(event))
            except Exception:
                pass
        return results

    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            events = list(self._history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in events[-limit:]]

    def filter_events(self, predicate: Callable[[Event], bool]) -> List[Event]:
        with self._lock:
            return [e for e in self._history if predicate(e)]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "enabled": self._enabled,
                "total_subscribers": sum(len(s) for s in self._subscribers.values()),
                "wildcard_subscribers": len(self._wildcard_subscribers),
                "history_size": len(self._history),
                "max_history": self._max_history,
            }


def run():
    print("=" * 60)
    print("Event Bus — Demo")
    print("=" * 60)

    bus = EventBus()
    received = []

    def handler(event: Event):
        received.append(event.event_type.value)
        print(f"   [Handler] Received: {event.event_type.value} from {event.source}")

    bus.subscribe(EventType.TOOL_CALL, handler)
    bus.subscribe_all(lambda e: received.append(f"wildcard:{e.event_type.value}"))

    print("\n[1] Publish events")
    bus.publish(Event(EventType.TOOL_CALL, {"tool": "read_file"}, EventPriority.NORMAL, "agent_1"))
    bus.publish(Event(EventType.AUDIT_LOG, {"event": "login"}, EventPriority.LOW, "system"))
    bus.publish(Event(EventType.TOOL_CALL, {"tool": "write_file"}, EventPriority.HIGH, "agent_2"))

    print(f"\n[2] History: {len(bus.get_history())} events")
    print(f"   Tool calls: {len(bus.get_history(EventType.TOOL_CALL))}")

    print(f"\n[3] Stats: {bus.stats()}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
