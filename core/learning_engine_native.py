#!/usr/bin/env python3
"""
Learning Engine for MAGNATRIX-OS (GENesis-AGI inspired)
Self-learning, procedure acquisition, skill building, knowledge consolidation.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import time
from typing import Any, Callable, Dict, List, Optional


@dataclasses.dataclass
class Procedure:
    id: str
    name: str
    steps: List[str]
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0.0
    created_at: float = dataclasses.field(default_factory=time.time)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'steps': len(self.steps),
            'success_rate': self.success_rate(),
            'confidence': self.confidence,
        }

    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class LearningEngine:
    """Self-learning and procedure acquisition engine."""

    def __init__(self) -> None:
        self._procedures: Dict[str, Procedure] = {}
        self._skills: Dict[str, float] = {}  # skill -> proficiency (0.0-1.0)
        self._learning_history: List[Dict[str, Any]] = []

    def acquire_procedure(self, name: str, steps: List[str], source: str = "observation") -> Procedure:
        proc = Procedure(
            id=f"proc_{int(time.time())}",
            name=name,
            steps=steps,
        )
        self._procedures[proc.id] = proc
        self._learning_history.append({
            'type': 'procedure_acquired',
            'name': name,
            'source': source,
            'timestamp': time.time(),
        })
        return proc

    def execute_procedure(self, procedure_id: str) -> Dict[str, Any]:
        proc = self._procedures.get(procedure_id)
        if not proc:
            return {'error': 'Procedure not found'}

        # Simulate execution
        success = True  # In real system, execute actual steps

        if success:
            proc.success_count += 1
        else:
            proc.failure_count += 1

        proc.last_used = time.time()
        proc.confidence = proc.success_rate()

        return {
            'success': success,
            'steps_executed': len(proc.steps),
            'confidence': proc.confidence,
        }

    def learn_skill(self, skill_name: str, progress: float = 0.1) -> float:
        current = self._skills.get(skill_name, 0.0)
        self._skills[skill_name] = min(1.0, current + progress)
        self._learning_history.append({
            'type': 'skill_progress',
            'skill': skill_name,
            'progress': progress,
            'timestamp': time.time(),
        })
        return self._skills[skill_name]

    def get_skill_level(self, skill_name: str) -> float:
        return self._skills.get(skill_name, 0.0)

    def find_procedure(self, keyword: str) -> List[Procedure]:
        return [p for p in self._procedures.values() if keyword.lower() in p.name.lower()]

    def consolidate(self) -> Dict[str, Any]:
        # Remove low-confidence procedures, merge duplicates
        removed = 0
        to_remove = [pid for pid, p in self._procedures.items() if p.confidence < 0.2 and p.failure_count > 5]
        for pid in to_remove:
            del self._procedures[pid]
            removed += 1

        return {
            'procedures_removed': removed,
            'remaining': len(self._procedures),
            'total_skills': len(self._skills),
            'avg_skill_level': sum(self._skills.values()) / max(1, len(self._skills)),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            'procedures': len(self._procedures),
            'skills': len(self._skills),
            'learning_events': len(self._learning_history),
            'avg_procedure_confidence': sum(p.confidence for p in self._procedures.values()) / max(1, len(self._procedures)),
        }


def _demo() -> None:
    print("=== Learning Engine Demo ===\n")

    learning = LearningEngine()

    # Acquire procedures
    p1 = learning.acquire_procedure("Debug Python", ["Check logs", "Reproduce issue", "Fix code", "Test"])
    p2 = learning.acquire_procedure("Write Article", ["Research", "Outline", "Draft", "Edit", "Publish"])

    print(f"Acquired: {p1.name}, {p2.name}")

    # Execute and learn
    for _ in range(8):
        learning.execute_procedure(p1.id)
    for _ in range(2):
        learning.execute_procedure(p1.id)

    learning.execute_procedure(p1.id)

    print(f"Procedure confidence: {p1.confidence:.2f}")

    # Learn skills
    learning.learn_skill('python', 0.2)
    learning.learn_skill('python', 0.3)
    learning.learn_skill('writing', 0.1)

    print(f"Python skill: {learning.get_skill_level('python'):.2f}")
    print(f"Writing skill: {learning.get_skill_level('writing'):.2f}")

    # Consolidate
    result = learning.consolidate()
    print(f"Consolidation: {result}")

    print(f"\nStats: {learning.get_stats()}")

    print("\n=== Learning Engine Demo Complete ===")


if __name__ == '__main__':
    _demo()
