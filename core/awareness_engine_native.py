#!/usr/bin/env python3
"""
Awareness Engine for MAGNATRIX-OS (GENesis-AGI inspired)
Signal collection, classification, perception, world snapshot.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import time
from typing import Any, Dict, List, Optional, Set


class SignalClass(enum.Enum):
    URGENT = "urgent"
    IMPORTANT = "important"
    ROUTINE = "routine"
    BACKGROUND = "background"
    NOISE = "noise"


@dataclasses.dataclass
class WorldSnapshot:
    """Snapshot of the world state at a moment in time."""
    timestamp: float
    user_presence: bool
    active_conversations: int
    pending_tasks: int
    system_load: float
    memory_pressure: float
    recent_topics: List[str]
    user_mood: str
    time_of_day: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'user_presence': self.user_presence,
            'active_conversations': self.active_conversations,
            'pending_tasks': self.pending_tasks,
            'system_load': self.system_load,
            'memory_pressure': self.memory_pressure,
            'recent_topics': self.recent_topics,
            'user_mood': self.user_mood,
            'time_of_day': self.time_of_day,
        }


class SignalClassifier:
    """Classify signals into priority buckets."""

    KEYWORDS_URGENT = {'urgent', 'critical', 'emergency', 'error', 'fail', 'broken', 'crash'}
    KEYWORDS_IMPORTANT = {'question', 'help', 'task', 'deadline', 'goal', 'schedule'}
    KEYWORDS_ROUTINE = {'hello', 'hi', 'check', 'status', 'update'}

    def classify(self, content: str) -> SignalClass:
        content_lower = content.lower()

        if any(kw in content_lower for kw in self.KEYWORDS_URGENT):
            return SignalClass.URGENT
        if any(kw in content_lower for kw in self.KEYWORDS_IMPORTANT):
            return SignalClass.IMPORTANT
        if any(kw in content_lower for kw in self.KEYWORDS_ROUTINE):
            return SignalClass.ROUTINE

        return SignalClass.BACKGROUND

    def priority(self, content: str) -> int:
        classification = self.classify(content)
        priorities = {
            SignalClass.URGENT: 1,
            SignalClass.IMPORTANT: 3,
            SignalClass.ROUTINE: 5,
            SignalClass.BACKGROUND: 7,
            SignalClass.NOISE: 10,
        }
        return priorities.get(classification, 5)


class AwarenessEngine:
    """Awareness and signal collection engine."""

    def __init__(self) -> None:
        self._classifier = SignalClassifier()
        self._snapshots: List[WorldSnapshot] = []
        self._sources: Dict[str, Dict[str, Any]] = {}
        self._active: bool = True

    def register_source(self, source_id: str, source_type: str, metadata: Dict[str, Any] = None) -> None:
        self._sources[source_id] = {
            'type': source_type,
            'active': True,
            'metadata': metadata or {},
            'last_signal': 0,
        }

    def capture_snapshot(self, user_presence: bool, conversations: int, tasks: int, 
                         load: float, memory: float, topics: List[str], mood: str) -> WorldSnapshot:
        snapshot = WorldSnapshot(
            timestamp=time.time(),
            user_presence=user_presence,
            active_conversations=conversations,
            pending_tasks=tasks,
            system_load=load,
            memory_pressure=memory,
            recent_topics=topics,
            user_mood=mood,
            time_of_day=time.strftime('%H:%M'),
        )
        self._snapshots.append(snapshot)
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]
        return snapshot

    def get_latest_snapshot(self) -> Optional[WorldSnapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def classify_signal(self, content: str) -> Dict[str, Any]:
        classification = self._classifier.classify(content)
        priority = self._classifier.priority(content)
        return {
            'classification': classification.value,
            'priority': priority,
            'requires_attention': classification in (SignalClass.URGENT, SignalClass.IMPORTANT),
        }

    def get_perception(self) -> Dict[str, Any]:
        snapshot = self.get_latest_snapshot()
        if not snapshot:
            return {'status': 'no_data'}

        # Derive perception from snapshot
        perceptions = []
        if snapshot.user_presence:
            perceptions.append('user_is_active')
        if snapshot.system_load > 0.8:
            perceptions.append('system_under_load')
        if snapshot.pending_tasks > 5:
            perceptions.append('backlog_building')
        if snapshot.memory_pressure > 0.9:
            perceptions.append('memory_critical')
        if not snapshot.user_presence and snapshot.active_conversations == 0:
            perceptions.append('quiet_period')

        return {
            'snapshot': snapshot.to_dict(),
            'perceptions': perceptions,
            'status': 'active' if self._active else 'inactive',
        }

    def should_proactive(self) -> bool:
        snapshot = self.get_latest_snapshot()
        if not snapshot:
            return False
        return snapshot.user_presence and snapshot.system_load < 0.5 and snapshot.pending_tasks < 3


def _demo() -> None:
    print("=== Awareness Engine Demo ===\n")

    awareness = AwarenessEngine()

    # Register sources
    awareness.register_source('telegram', 'chat', {'priority': 2})
    awareness.register_source('system', 'monitor', {'priority': 1})
    awareness.register_source('schedule', 'cron', {'priority': 5})

    # Capture snapshots
    awareness.capture_snapshot(
        user_presence=True, conversations=2, tasks=3,
        load=0.4, memory=0.3, topics=['AI', 'Python'], mood='focused'
    )
    awareness.capture_snapshot(
        user_presence=False, conversations=0, tasks=5,
        load=0.7, memory=0.6, topics=['security'], mood='unknown'
    )

    # Classify signals
    signals = [
        "System error: disk full",
        "Hello, how are you?",
        "Can you help me with this task?",
        "Reminder: meeting at 3pm",
    ]

    for s in signals:
        result = awareness.classify_signal(s)
        print(f"  '{s[:40]}' -> {result['classification']} (priority: {result['priority']})")

    # Perception
    print(f"\nPerception: {awareness.get_perception()}")
    print(f"Should proactive: {awareness.should_proactive()}")

    print("\n=== Awareness Engine Demo Complete ===")


if __name__ == '__main__':
    _demo()
