"""
llm_event_sourcing_native.py
MAGNATRIX-OS Event Sourcing Engine
Native Python, stdlib only.
Provides event sourcing with event store, aggregate reconstruction, snapshotting, and replay.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class EventType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    CUSTOM = "custom"


@dataclass
class DomainEvent:
    event_id: str
    aggregate_id: str
    event_type: EventType
    payload: Dict[str, Any]
    sequence: int
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id, "aggregate_id": self.aggregate_id,
            "event_type": self.event_type.value, "payload": self.payload,
            "sequence": self.sequence, "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class Snapshot:
    aggregate_id: str
    sequence: int
    state: Dict[str, Any]
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id, "sequence": self.sequence,
            "state": self.state, "created_at": self.created_at,
        }


class EventSourcingEngine:
    """
    Event sourcing engine with event store, replay, and snapshotting.
    """

    def __init__(self, snapshot_interval: int = 100) -> None:
        self.snapshot_interval = snapshot_interval
        self._events: Dict[str, List[DomainEvent]] = {}  # aggregate_id -> events
        self._snapshots: Dict[str, Snapshot] = {}
        self._handlers: Dict[str, List[Callable[[DomainEvent], None]]] = {}
        self._global_listeners: List[Callable[[DomainEvent], None]] = []
        self._sequence_counter: Dict[str, int] = {}

    def append(self, event: DomainEvent) -> None:
        agg_id = event.aggregate_id
        if agg_id not in self._events:
            self._events[agg_id] = []
        self._events[agg_id].append(event)
        self._sequence_counter[agg_id] = event.sequence

        # Notify handlers
        for handler in self._handlers.get(agg_id, []):
            try:
                handler(event)
            except Exception:
                pass
        for listener in self._global_listeners:
            try:
                listener(event)
            except Exception:
                pass

        # Auto-snapshot
        if len(self._events[agg_id]) >= self.snapshot_interval and len(self._events[agg_id]) % self.snapshot_interval == 0:
            self._create_snapshot(agg_id)

    def create_event(self, aggregate_id: str, event_type: EventType, payload: Dict[str, Any],
                     metadata: Optional[Dict[str, Any]] = None) -> DomainEvent:
        seq = self._sequence_counter.get(aggregate_id, 0) + 1
        event_id = f"{aggregate_id}_{seq}_{int(time.time() * 1000)}"
        return DomainEvent(
            event_id=event_id, aggregate_id=aggregate_id, event_type=event_type,
            payload=payload, sequence=seq, timestamp=time.time(), metadata=metadata or {}
        )

    def get_events(self, aggregate_id: str, from_sequence: int = 1) -> List[DomainEvent]:
        return [e for e in self._events.get(aggregate_id, []) if e.sequence >= from_sequence]

    def get_all_events(self) -> List[DomainEvent]:
        all_events = []
        for agg_events in self._events.values():
            all_events.extend(agg_events)
        return sorted(all_events, key=lambda e: e.timestamp)

    def _create_snapshot(self, aggregate_id: str) -> None:
        events = self._events.get(aggregate_id, [])
        if not events:
            return
        state = self._reconstruct_state(aggregate_id)
        last_seq = events[-1].sequence if events else 0
        self._snapshots[aggregate_id] = Snapshot(
            aggregate_id=aggregate_id, sequence=last_seq, state=state, created_at=time.time()
        )

    def _reconstruct_state(self, aggregate_id: str) -> Dict[str, Any]:
        state: Dict[str, Any] = {}
        for event in self._events.get(aggregate_id, []):
            state = self._apply_event(state, event)
        return state

    def _apply_event(self, state: Dict[str, Any], event: DomainEvent) -> Dict[str, Any]:
        new_state = dict(state)
        if event.event_type == EventType.CREATE:
            new_state.update(event.payload)
        elif event.event_type == EventType.UPDATE:
            for key, value in event.payload.items():
                if isinstance(value, dict) and key in new_state and isinstance(new_state[key], dict):
                    new_state[key].update(value)
                else:
                    new_state[key] = value
        elif event.event_type == EventType.DELETE:
            for key in event.payload.get("keys", []):
                new_state.pop(key, None)
        elif event.event_type == EventType.CUSTOM:
            if "__set__" in event.payload:
                new_state.update(event.payload["__set__"])
        return new_state

    def reconstruct(self, aggregate_id: str) -> Dict[str, Any]:
        snapshot = self._snapshots.get(aggregate_id)
        if snapshot:
            state = dict(snapshot.state)
            events = self.get_events(aggregate_id, snapshot.sequence + 1)
        else:
            state = {}
            events = self.get_events(aggregate_id)
        for event in events:
            state = self._apply_event(state, event)
        return state

    def replay(self, aggregate_id: str, projection: Callable[[Dict[str, Any], DomainEvent], Dict[str, Any]]) -> Dict[str, Any]:
        state = {}
        for event in self.get_events(aggregate_id):
            state = projection(state, event)
        return state

    def subscribe(self, aggregate_id: str, handler: Callable[[DomainEvent], None]) -> None:
        self._handlers.setdefault(aggregate_id, []).append(handler)

    def subscribe_global(self, handler: Callable[[DomainEvent], None]) -> None:
        self._global_listeners.append(handler)

    def get_snapshot(self, aggregate_id: str) -> Optional[Snapshot]:
        return self._snapshots.get(aggregate_id)

    def take_snapshot(self, aggregate_id: str) -> Snapshot:
        self._create_snapshot(aggregate_id)
        return self._snapshots[aggregate_id]

    def get_stats(self) -> Dict[str, Any]:
        total_events = sum(len(e) for e in self._events.values())
        return {
            "aggregates": len(self._events),
            "total_events": total_events,
            "snapshots": len(self._snapshots),
            "avg_events_per_aggregate": total_events / max(len(self._events), 1),
        }

    def export_events(self, path: str, aggregate_id: Optional[str] = None) -> None:
        if aggregate_id:
            events = self.get_events(aggregate_id)
        else:
            events = self.get_all_events()
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in events], f, indent=2, default=str)

    def import_events(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for ed in data:
            event = DomainEvent(
                event_id=ed["event_id"], aggregate_id=ed["aggregate_id"],
                event_type=EventType(ed["event_type"]), payload=ed["payload"],
                sequence=ed["sequence"], timestamp=ed["timestamp"],
                metadata=ed.get("metadata", {}),
            )
            self.append(event)

    def clear(self, aggregate_id: Optional[str] = None) -> None:
        if aggregate_id:
            self._events.pop(aggregate_id, None)
            self._snapshots.pop(aggregate_id, None)
            self._sequence_counter.pop(aggregate_id, None)
        else:
            self._events.clear()
            self._snapshots.clear()
            self._sequence_counter.clear()


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Event Sourcing Engine")
    print("=" * 60)

    engine = EventSourcingEngine(snapshot_interval=5)

    # Simulate an LLM conversation as an aggregate
    conv_id = "conversation_001"

    events = [
        engine.create_event(conv_id, EventType.CREATE, {"user_id": "U123", "topic": "support", "status": "active"}),
        engine.create_event(conv_id, EventType.UPDATE, {"messages": [{"role": "user", "content": "Hello"}]}),
        engine.create_event(conv_id, EventType.UPDATE, {"messages": [{"role": "assistant", "content": "Hi there!"}]}),
        engine.create_event(conv_id, EventType.UPDATE, {"status": "resolved", "resolved_at": time.time()}),
    ]

    for e in events:
        engine.append(e)
        print(f"  Appended event {e.sequence}: {e.event_type.value} (id={e.event_id})")

    print("\n--- Reconstructed State ---")
    state = engine.reconstruct(conv_id)
    for k, v in state.items():
        print(f"  {k}: {v}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\n--- Snapshot ---")
    snap = engine.take_snapshot(conv_id)
    print(f"  Snapshot at sequence {snap.sequence}, created_at={snap.created_at}")

    print("\n--- Add more events, reconstruct from snapshot ---")
    for i in range(3):
        e = engine.create_event(conv_id, EventType.UPDATE, {"extra_field": f"value_{i}"})
        engine.append(e)

    state2 = engine.reconstruct(conv_id)
    print(f"  Reconstructed state has {len(state2)} keys")

    print("\n--- Replay with custom projection ---")
    def message_counter(state: Dict, event: DomainEvent) -> Dict:
        if event.event_type == EventType.UPDATE and "messages" in event.payload:
            state["message_count"] = state.get("message_count", 0) + len(event.payload["messages"])
        return state

    projection = engine.replay(conv_id, message_counter)
    print(f"  Message count projection: {projection}")

    print("\n--- Event subscription ---")
    received_events = []
    engine.subscribe(conv_id, lambda e: received_events.append(e.event_id))
    new_event = engine.create_event(conv_id, EventType.CUSTOM, {"__set__": {"final": True}})
    engine.append(new_event)
    print(f"  Subscriber received: {len(received_events)} events")

    print("\nEvent Sourcing test complete.")


if __name__ == "__main__":
    run()
