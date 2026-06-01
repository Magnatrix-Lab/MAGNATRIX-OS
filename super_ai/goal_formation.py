#!/usr/bin/env python3
"""goal_formation.py — Emergent Goal Formation Engine for MAGNATRIX-OS.

Detect needs, generate goals, prioritize, resolve dependencies, manage lifecycle.
"""

from __future__ import annotations
import time, uuid, math
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum, auto


class GoalStatus(Enum):
    DETECTED = auto()
    PROPOSED = auto()
    APPROVED = auto()
    PLANNED = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()
    ARCHIVED = auto()


class GoalPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    DEFERRED = 5


@dataclass
class Goal:
    id: str
    name: str
    description: str
    priority: GoalPriority
    status: GoalStatus
    needs: List[str]  # detected needs that triggered this goal
    prerequisites: List[str]  # goal IDs that must complete first
    created_at: float
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GoalFormationEngine:
    """Detect needs, form goals, prioritize, resolve dependencies."""

    def __init__(self):
        self._goals: Dict[str, Goal] = {}
        self._needs_log: List[Dict[str, Any]] = []
        self._capability_map: Dict[str, List[str]] = {
            "memory_low": ["optimize_cache", "flush_unused", "scale_storage"],
            "cpu_high": ["offload_tasks", "reduce_precision", "parallelize"],
            "error_rate_high": ["rollback_last", "isolate_component", "restart_service"],
            "security_threat": ["isolate_actor", "rotate_keys", "audit_logs"],
            "new_user": ["onboard_flow", "verify_identity", "grant_access"],
            "skill_gap": ["learn_new_skill", "request_training", "outsource_task"],
        }

    def detect_needs(self, system_state: Dict[str, Any]) -> List[str]:
        """Analyze system state and return detected needs."""
        needs = []
        if system_state.get("memory_usage", 0) > 0.85:
            needs.append("memory_low")
        if system_state.get("cpu_usage", 0) > 0.90:
            needs.append("cpu_high")
        if system_state.get("error_rate", 0) > 0.05:
            needs.append("error_rate_high")
        if system_state.get("security_alert", False):
            needs.append("security_threat")
        if system_state.get("new_users_count", 0) > 0:
            needs.append("new_user")
        if system_state.get("unknown_tasks", 0) > 0:
            needs.append("skill_gap")
        self._needs_log.append({"time": time.time(), "needs": needs, "state": system_state})
        return needs

    def generate_goals(self, needs: List[str]) -> List[Goal]:
        goals = []
        for need in needs:
            actions = self._capability_map.get(need, ["investigate"])
            for action in actions:
                gid = f"G-{uuid.uuid4().hex[:8]}"
                priority = self._priority_for_need(need)
                goal = Goal(
                    id=gid, name=action,
                    description=f"Address {need} via {action}",
                    priority=priority, status=GoalStatus.DETECTED,
                    needs=[need], prerequisites=[],
                    created_at=time.time(),
                )
                goals.append(goal)
                self._goals[gid] = goal
        return goals

    def _priority_for_need(self, need: str) -> GoalPriority:
        mapping = {
            "security_threat": GoalPriority.CRITICAL,
            "memory_low": GoalPriority.CRITICAL,
            "cpu_high": GoalPriority.HIGH,
            "error_rate_high": GoalPriority.HIGH,
            "new_user": GoalPriority.MEDIUM,
            "skill_gap": GoalPriority.LOW,
        }
        return mapping.get(need, GoalPriority.MEDIUM)

    def prioritize(self, goals: List[Goal]) -> List[Goal]:
        return sorted(goals, key=lambda g: (g.priority.value, g.created_at))

    def resolve_dependencies(self, goals: List[Goal]) -> List[Goal]:
        """Identify prerequisite goals and link them."""
        for g in goals:
            if g.name in ["scale_storage", "parallelize"]:
                for other in goals:
                    if other.name == "optimize_cache" and other.id != g.id:
                        g.prerequisites.append(other.id)
        return goals

    def check_conflicts(self, goals: List[Goal]) -> List[Dict[str, Any]]:
        conflicts = []
        for i, g1 in enumerate(goals):
            for g2 in goals[i+1:]:
                if g1.name == g2.name and g1.priority == g2.priority:
                    conflicts.append({"type": "duplicate", "goals": [g1.id, g2.id], "resolution": "merge"})
                if g1.name == "isolate_actor" and g2.name == "grant_access":
                    conflicts.append({"type": "contradiction", "goals": [g1.id, g2.id], "resolution": "isolate_wins"})
        return conflicts

    def approve(self, goal_id: str) -> None:
        g = self._goals.get(goal_id)
        if g and g.status == GoalStatus.DETECTED:
            g.status = GoalStatus.APPROVED

    def plan(self, goal_id: str) -> List[str]:
        g = self._goals.get(goal_id)
        if not g or g.status != GoalStatus.APPROVED:
            return []
        if all(self._goals.get(p, GoalStatus.COMPLETED).status == GoalStatus.COMPLETED for p in g.prerequisites):
            g.status = GoalStatus.PLANNED
            return [f"step: execute {g.name}", f"step: verify {g.name}", f"step: report {g.name}"]
        return [f"blocked: waiting for prerequisites {g.prerequisites}"]

    def execute(self, goal_id: str) -> Dict[str, Any]:
        g = self._goals.get(goal_id)
        if not g or g.status != GoalStatus.PLANNED:
            return {"error": "Goal not ready for execution"}
        g.status = GoalStatus.EXECUTING
        return {"goal_id": goal_id, "status": "executing", "started": time.time()}

    def complete(self, goal_id: str, success: bool = True) -> None:
        g = self._goals.get(goal_id)
        if g:
            g.status = GoalStatus.COMPLETED if success else GoalStatus.FAILED
            g.completed_at = time.time()

    def archive(self, goal_id: str) -> None:
        g = self._goals.get(goal_id)
        if g and g.status in (GoalStatus.COMPLETED, GoalStatus.FAILED):
            g.status = GoalStatus.ARCHIVED

    def get_active(self) -> List[Goal]:
        return [g for g in self._goals.values() if g.status not in (GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.ARCHIVED)]

    def get_stats(self) -> Dict[str, Any]:
        status_counts = {s.name: 0 for s in GoalStatus}
        for g in self._goals.values():
            status_counts[g.status.name] += 1
        return {
            "total_goals": len(self._goals),
            "active": len(self.get_active()),
            "needs_detected": len(self._needs_log),
            "status_breakdown": status_counts,
        }


if __name__ == "__main__":
    engine = GoalFormationEngine()
    state = {"memory_usage": 0.92, "cpu_usage": 0.45, "error_rate": 0.02, "security_alert": True}
    needs = engine.detect_needs(state)
    print(f"Detected needs: {needs}")
    goals = engine.generate_goals(needs)
    goals = engine.resolve_dependencies(goals)
    conflicts = engine.check_conflicts(goals)
    print(f"Conflicts: {conflicts}")
    prioritized = engine.prioritize(goals)
    for g in prioritized[:5]:
        print(f"  {g.id} | {g.name} | {g.priority.name} | needs: {g.needs} | prereqs: {g.prerequisites}")
    for g in prioritized[:3]:
        engine.approve(g.id)
        engine.plan(g.id)
        print(f"Approved & planned: {g.id} -> {g.status.name}")
    print(f"Stats: {engine.get_stats()}")
