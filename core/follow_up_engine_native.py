#!/usr/bin/env python3
"""
Follow-up Engine for MAGNATRIX-OS (GENesis-AGI inspired)
Follow-up handling, reminders, scheduled actions, task completion tracking.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import time
from typing import Any, Dict, List, Optional


@dataclasses.dataclass
class FollowUp:
    id: str
    original_task_id: str
    description: str
    scheduled_for: float
    status: str = "pending"  # pending, triggered, completed, dismissed
    trigger_condition: str = "time"  # time, event, completion
    priority: int = 5
    created_at: float = dataclasses.field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'description': self.description,
            'scheduled_for': self.scheduled_for,
            'status': self.status,
            'priority': self.priority,
        }


class FollowUpEngine:
    """Follow-up and reminder management."""

    def __init__(self) -> None:
        self._followups: Dict[str, FollowUp] = {}
        self._completed_tasks: List[str] = []

    def schedule(self, task_id: str, description: str, delay_seconds: float, priority: int = 5) -> FollowUp:
        fu = FollowUp(
            id=f"fu_{int(time.time())}",
            original_task_id=task_id,
            description=description,
            scheduled_for=time.time() + delay_seconds,
            priority=priority,
        )
        self._followups[fu.id] = fu
        return fu

    def check_due(self) -> List[FollowUp]:
        now = time.time()
        due = [fu for fu in self._followups.values() if fu.status == "pending" and fu.scheduled_for <= now]
        for fu in due:
            fu.status = "triggered"
        return sorted(due, key=lambda f: f.priority)

    def complete(self, followup_id: str) -> bool:
        fu = self._followups.get(followup_id)
        if fu:
            fu.status = "completed"
            self._completed_tasks.append(fu.original_task_id)
            return True
        return False

    def dismiss(self, followup_id: str) -> bool:
        fu = self._followups.get(followup_id)
        if fu:
            fu.status = "dismissed"
            return True
        return False

    def get_pending(self) -> List[FollowUp]:
        return [fu for fu in self._followups.values() if fu.status == "pending"]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._followups)
        pending = len(self.get_pending())
        completed = len([fu for fu in self._followups.values() if fu.status == "completed"])
        return {
            'total': total,
            'pending': pending,
            'triggered': len([fu for fu in self._followups.values() if fu.status == "triggered"]),
            'completed': completed,
            'completion_rate': completed / max(1, total),
        }


def _demo() -> None:
    print("=== Follow-up Engine Demo ===\n")

    fu = FollowUpEngine()

    # Schedule follow-ups
    fu.schedule('task_1', 'Check if user received response', 3600, priority=3)
    fu.schedule('task_2', 'Review published article', 86400, priority=5)
    fu.schedule('task_3', 'Follow up on meeting', 1800, priority=2)

    print(f"Scheduled: {len(fu._followups)} follow-ups")

    # Check due (simulate time passing)
    for f in fu._followups.values():
        f.scheduled_for = time.time() - 1  # Make all due

    due = fu.check_due()
    print(f"Due now: {len(due)}")
    for d in due[:3]:
        print(f"  [{d.priority}] {d.description}")

    # Complete some
    for d in due[:2]:
        fu.complete(d.id)

    print(f"Stats: {fu.get_stats()}")

    print("\n=== Follow-up Engine Demo Complete ===")


if __name__ == '__main__':
    _demo()
