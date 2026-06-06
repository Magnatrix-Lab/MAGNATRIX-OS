#!/usr/bin/env python3
"""
Autonomy Engine for MAGNATRIX-OS (GENesis-AGI inspired)
Goal-directed execution, autonomy verification, self-directed behavior.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import time
from typing import Any, Dict, List, Optional, Set


class GoalStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class GoalType(enum.Enum):
    USER_DIRECTED = "user_directed"
    SYSTEM_DIRECTED = "system_directed"
    SELF_DIRECTED = "self_directed"
    PROACTIVE = "proactive"


@dataclasses.dataclass
class Goal:
    id: str
    description: str
    goal_type: GoalType
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 5
    created_at: float = dataclasses.field(default_factory=time.time)
    deadline: Optional[float] = None
    parent_id: Optional[str] = None
    subgoals: List[str] = dataclasses.field(default_factory=list)
    required_capabilities: Set[str] = dataclasses.field(default_factory=set)
    verification_criteria: str = ""
    autonomy_level: float = 0.0  # 0.0-1.0, earned autonomy

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'description': self.description,
            'type': self.goal_type.value,
            'status': self.status.value,
            'priority': self.priority,
            'autonomy_level': self.autonomy_level,
        }


class AutonomyVerifier:
    """Verify autonomy level before executing goals."""

    def __init__(self) -> None:
        self._trust_score: float = 0.0  # 0.0-1.0
        self._success_history: List[bool] = []

    def record_outcome(self, success: bool) -> None:
        self._success_history.append(success)
        if len(self._success_history) > 100:
            self._success_history = self._success_history[-100:]
        self._trust_score = sum(self._success_history) / len(self._success_history) if self._success_history else 0.0

    def can_autonomous(self, goal: Goal) -> bool:
        # Higher trust = more autonomy
        if goal.goal_type == GoalType.USER_DIRECTED:
            return True  # User-directed always allowed
        if goal.goal_type == GoalType.SELF_DIRECTED:
            return self._trust_score >= 0.7
        if goal.goal_type == GoalType.PROACTIVE:
            return self._trust_score >= 0.8
        return self._trust_score >= 0.5

    def required_approval(self, goal: Goal) -> bool:
        return not self.can_autonomous(goal)

    def get_trust_score(self) -> float:
        return self._trust_score


class GoalCascade:
    """Decompose goals into subgoals."""

    def decompose(self, goal: Goal) -> List[Goal]:
        # Simple decomposition strategies
        if 'learn' in goal.description.lower():
            return [
                Goal(id=f"{goal.id}_1", description="Research topic", goal_type=GoalType.SELF_DIRECTED, parent_id=goal.id),
                Goal(id=f"{goal.id}_2", description="Practice with examples", goal_type=GoalType.SELF_DIRECTED, parent_id=goal.id),
                Goal(id=f"{goal.id}_3", description="Summarize findings", goal_type=GoalType.SELF_DIRECTED, parent_id=goal.id),
            ]
        elif 'create' in goal.description.lower():
            return [
                Goal(id=f"{goal.id}_1", description="Plan content structure", goal_type=GoalType.SELF_DIRECTED, parent_id=goal.id),
                Goal(id=f"{goal.id}_2", description="Draft content", goal_type=GoalType.SELF_DIRECTED, parent_id=goal.id),
                Goal(id=f"{goal.id}_3", description="Review and refine", goal_type=GoalType.SELF_DIRECTED, parent_id=goal.id),
            ]
        else:
            return [
                Goal(id=f"{goal.id}_1", description=f"Analyze: {goal.description}", goal_type=GoalType.SELF_DIRECTED, parent_id=goal.id),
                Goal(id=f"{goal.id}_2", description=f"Execute: {goal.description}", goal_type=GoalType.SELF_DIRECTED, parent_id=goal.id),
            ]


class AutonomyEngine:
    """Main autonomy orchestrator."""

    def __init__(self) -> None:
        self._goals: Dict[str, Goal] = {}
        self._verifier = AutonomyVerifier()
        self._cascade = GoalCascade()
        self._active_goal: Optional[str] = None

    def create_goal(self, description: str, goal_type: GoalType = GoalType.USER_DIRECTED, 
                    priority: int = 5, capabilities: Set[str] = None) -> Goal:
        goal = Goal(
            id=f"goal_{int(time.time())}",
            description=description,
            goal_type=goal_type,
            priority=priority,
            required_capabilities=capabilities or set(),
        )
        self._goals[goal.id] = goal
        return goal

    def decompose(self, goal_id: str) -> List[Goal]:
        goal = self._goals.get(goal_id)
        if not goal:
            return []

        subgoals = self._cascade.decompose(goal)
        for sg in subgoals:
            self._goals[sg.id] = sg
            goal.subgoals.append(sg.id)
        return subgoals

    def execute(self, goal_id: str) -> Dict[str, Any]:
        goal = self._goals.get(goal_id)
        if not goal:
            return {'error': 'Goal not found'}

        # Verify autonomy
        if self._verifier.required_approval(goal):
            return {'status': 'needs_approval', 'goal': goal_id, 'trust_score': self._verifier.get_trust_score()}

        goal.status = GoalStatus.ACTIVE
        self._active_goal = goal_id

        # Simulate execution
        success = True  # In real system, execute actual task

        goal.status = GoalStatus.COMPLETED if success else GoalStatus.FAILED
        self._verifier.record_outcome(success)

        return {
            'status': goal.status.value,
            'goal': goal_id,
            'autonomous': True,
            'trust_score': self._verifier.get_trust_score(),
        }

    def get_pending(self) -> List[Goal]:
        return [g for g in self._goals.values() if g.status == GoalStatus.PENDING]

    def get_active(self) -> List[Goal]:
        return [g for g in self._goals.values() if g.status == GoalStatus.ACTIVE]

    def get_status(self) -> Dict[str, Any]:
        return {
            'total_goals': len(self._goals),
            'pending': len(self.get_pending()),
            'active': len(self.get_active()),
            'trust_score': self._verifier.get_trust_score(),
            'active_goal': self._active_goal,
        }


def _demo() -> None:
    print("=== Autonomy Engine Demo ===\n")

    autonomy = AutonomyEngine()

    # Create goals
    g1 = autonomy.create_goal("Learn about quantum computing", GoalType.USER_DIRECTED, priority=3)
    g2 = autonomy.create_goal("Proactive research on AI trends", GoalType.PROACTIVE, priority=7)

    print(f"Goal 1: {g1.description} (type: {g1.goal_type.value})")
    print(f"Goal 2: {g2.description} (type: {g2.goal_type.value})")

    # Decompose
    subgoals = autonomy.decompose(g1.id)
    print(f"\nDecomposed into {len(subgoals)} subgoals:")
    for sg in subgoals:
        print(f"  - {sg.description}")

    # Execute with low trust
    print(f"\nTrust score: {autonomy._verifier.get_trust_score():.2f}")
    result = autonomy.execute(g2.id)  # Proactive needs high trust
    print(f"Proactive execution: {result['status']}")

    # Build trust by executing user-directed goals
    for _ in range(10):
        g = autonomy.create_goal("Simple task", GoalType.USER_DIRECTED)
        autonomy.execute(g.id)

    print(f"Trust score after successes: {autonomy._verifier.get_trust_score():.2f}")

    # Now proactive should work
    result = autonomy.execute(g2.id)
    print(f"Proactive execution: {result['status']}")

    print(f"\nStatus: {autonomy.get_status()}")

    print("\n=== Autonomy Engine Demo Complete ===")


if __name__ == '__main__':
    _demo()
