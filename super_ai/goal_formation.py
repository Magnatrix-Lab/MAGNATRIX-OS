#!/usr/bin/env python3
"""goal_formation.py — Advanced Emergent Goal Formation Engine for MAGNATRIX-OS.

Dynamic need detection with learning, automatic goal decomposition, resource estimation,
temporal planning, cross-goal synergy detection, and intelligent abandonment.
"""

from __future__ import annotations
import time, uuid, math, statistics
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto


class GoalStatus(Enum):
    DETECTED = auto(); PROPOSED = auto(); APPROVED = auto(); PLANNED = auto()
    EXECUTING = auto(); COMPLETED = auto(); FAILED = auto(); ARCHIVED = auto(); ABANDONED = auto()


class GoalPriority(Enum):
    CRITICAL = 1; HIGH = 2; MEDIUM = 3; LOW = 4; DEFERRED = 5


@dataclass
class SubGoal:
    id: str
    name: str
    milestone: str
    estimated_duration: float  # seconds
    required_resources: Dict[str, float]


@dataclass
class Goal:
    id: str
    name: str
    description: str
    priority: GoalPriority
    status: GoalStatus
    needs: List[str]
    prerequisites: List[str]
    subgoals: List[SubGoal] = field(default_factory=list)
    resource_estimate: Dict[str, float] = field(default_factory=dict)
    deadline: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    success_rate: float = 0.0


class AdaptiveNeedDetector:
    """Dynamic need detection with learning from history."""

    def __init__(self):
        self._thresholds: Dict[str, float] = {
            "memory_usage": 0.85, "cpu_usage": 0.90, "error_rate": 0.05,
            "network_latency": 0.5, "disk_usage": 0.90, "queue_depth": 100,
        }
        self._history: List[Dict[str, Any]] = []
        self._trend_window: int = 10

    def detect(self, system_state: Dict[str, Any]) -> List[str]:
        needs = []
        if system_state.get("memory_usage", 0) > self._thresholds["memory_usage"]:
            needs.append("memory_low")
        if system_state.get("cpu_usage", 0) > self._thresholds["cpu_usage"]:
            needs.append("cpu_high")
        if system_state.get("error_rate", 0) > self._thresholds["error_rate"]:
            needs.append("error_rate_high")
        if system_state.get("security_alert", False):
            needs.append("security_threat")
        if system_state.get("new_users_count", 0) > 0:
            needs.append("new_user")
        if system_state.get("unknown_tasks", 0) > 0:
            needs.append("skill_gap")
        if system_state.get("network_latency", 0) > self._thresholds["network_latency"]:
            needs.append("network_slow")
        if system_state.get("disk_usage", 0) > self._thresholds["disk_usage"]:
            needs.append("disk_full")

        self._history.append({"time": time.time(), "needs": needs, "state": system_state})
        self._adapt_thresholds()
        return needs

    def _adapt_thresholds(self) -> None:
        if len(self._history) < self._trend_window:
            return
        recent = self._history[-self._trend_window:]
        for metric in ["memory_usage", "cpu_usage", "error_rate"]:
            values = [h["state"].get(metric, 0) for h in recent if metric in h["state"]]
            if values:
                mean = statistics.mean(values)
                std = statistics.stdev(values) if len(values) > 1 else 0
                self._thresholds[metric] = max(0.5, min(0.99, mean + 2 * std))

    def get_trend(self, metric: str, window: int = 10) -> Optional[Dict[str, float]]:
        values = [h["state"].get(metric) for h in self._history[-window:] if metric in h.get("state", {})]
        if not values:
            return None
        return {
            "current": values[-1], "mean": statistics.mean(values),
            "trend": "increasing" if values[-1] > statistics.mean(values[:-1] or [0]) else "stable",
        }


class GoalDecomposer:
    """Break goals into actionable sub-goals with milestones."""

    TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
        "optimize_cache": [
            {"name": "analyze_cache", "milestone": "Identify cache hotspots", "duration": 30, "resources": {"cpu": 0.1}},
            {"name": "evict_stale", "milestone": "Remove stale entries", "duration": 15, "resources": {"cpu": 0.2, "memory": -50}},
            {"name": "resize_cache", "milestone": "Resize cache pool", "duration": 10, "resources": {"memory": 100}},
        ],
        "isolate_actor": [
            {"name": "identify_threat", "milestone": "Threat actor identified", "duration": 5, "resources": {"cpu": 0.05}},
            {"name": "quarantine", "milestone": "Actor quarantined", "duration": 10, "resources": {"cpu": 0.1}},
            {"name": "audit_access", "milestone": "Access logs audited", "duration": 60, "resources": {"cpu": 0.2, "io": 0.3}},
        ],
        "scale_storage": [
            {"name": "check_capacity", "milestone": "Capacity analysis done", "duration": 20, "resources": {"cpu": 0.1}},
            {"name": "allocate_volume", "milestone": "New volume allocated", "duration": 60, "resources": {"disk": 1000}},
            {"name": "migrate_data", "milestone": "Data migrated", "duration": 300, "resources": {"cpu": 0.3, "io": 0.5, "network": 0.2}},
        ],
    }

    def decompose(self, goal: Goal) -> Goal:
        template = self.TEMPLATES.get(goal.name, [])
        if not template:
            template = [
                {"name": f"prepare_{goal.name}", "milestone": "Preparation complete", "duration": 10, "resources": {"cpu": 0.1}},
                {"name": f"execute_{goal.name}", "milestone": "Execution complete", "duration": 30, "resources": {"cpu": 0.2}},
                {"name": f"verify_{goal.name}", "milestone": "Verification complete", "duration": 15, "resources": {"cpu": 0.05}},
            ]
        subgoals = []
        for i, t in enumerate(template):
            sg = SubGoal(
                id=f"{goal.id}-SG{i}", name=t["name"], milestone=t["milestone"],
                estimated_duration=t["duration"], required_resources=t.get("resources", {}),
            )
            subgoals.append(sg)
        goal.subgoals = subgoals
        goal.resource_estimate = self._aggregate_resources(subgoals)
        return goal

    def _aggregate_resources(self, subgoals: List[SubGoal]) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        for sg in subgoals:
            for k, v in sg.required_resources.items():
                totals[k] = totals.get(k, 0.0) + v
        return totals


class TemporalPlanner:
    """Schedule goals with time windows and deadlines."""

    def schedule(self, goals: List[Goal]) -> Dict[str, Any]:
        now = time.time()
        schedule = []
        cumulative_time = 0
        for g in sorted(goals, key=lambda x: x.priority.value):
            est_duration = sum(sg.estimated_duration for sg in g.subgoals) if g.subgoals else 30
            start = now + cumulative_time
            end = start + est_duration
            deadline_ok = g.deadline is None or end <= g.deadline
            schedule.append({
                "goal_id": g.id, "start": start, "end": end,
                "estimated_duration": est_duration, "deadline_ok": deadline_ok,
            })
            cumulative_time += est_duration
        return {"schedule": schedule, "total_estimated": cumulative_time, "all_deadlines_ok": all(s["deadline_ok"] for s in schedule)}


class SynergyDetector:
    """Detect cross-goal synergies for batch optimization."""

    def detect(self, goals: List[Goal]) -> List[Dict[str, Any]]:
        synergies = []
        for i, g1 in enumerate(goals):
            for g2 in goals[i+1:]:
                shared_resources = set(g1.resource_estimate.keys()) & set(g2.resource_estimate.keys())
                shared_needs = set(g1.needs) & set(g2.needs)
                if shared_needs or shared_resources:
                    synergies.append({
                        "goals": [g1.id, g2.id],
                        "type": "shared_resources" if shared_resources else "shared_needs",
                        "shared": list(shared_resources or shared_needs),
                        "suggestion": "Batch execution" if shared_needs else "Resource co-allocation",
                    })
        return synergies


class GoalFormationEngine:
    """Advanced goal formation with decomposition, planning, and synergy."""

    def __init__(self):
        self._goals: Dict[str, Goal] = {}
        self._detector = AdaptiveNeedDetector()
        self._decomposer = GoalDecomposer()
        self._planner = TemporalPlanner()
        self._synergy = SynergyDetector()
        self._capability_map: Dict[str, List[str]] = {
            "memory_low": ["optimize_cache", "flush_unused", "scale_storage"],
            "cpu_high": ["offload_tasks", "reduce_precision", "parallelize"],
            "error_rate_high": ["rollback_last", "isolate_component", "restart_service"],
            "security_threat": ["isolate_actor", "rotate_keys", "audit_logs"],
            "new_user": ["onboard_flow", "verify_identity", "grant_access"],
            "skill_gap": ["learn_new_skill", "request_training", "outsource_task"],
            "network_slow": ["compress_payload", "cdn_reroute", "batch_requests"],
            "disk_full": ["cleanup_temp", "archive_old", "scale_storage"],
        }

    def detect_needs(self, system_state: Dict[str, Any]) -> List[str]:
        return self._detector.detect(system_state)

    def get_trend(self, metric: str) -> Optional[Dict[str, float]]:
        return self._detector.get_trend(metric)

    def generate_goals(self, needs: List[str]) -> List[Goal]:
        goals = []
        for need in needs:
            actions = self._capability_map.get(need, ["investigate"])
            for action in actions:
                gid = f"G-{uuid.uuid4().hex[:8]}"
                goal = Goal(
                    id=gid, name=action, description=f"Address {need} via {action}",
                    priority=self._priority_for_need(need), status=GoalStatus.DETECTED,
                    needs=[need], prerequisites=[],
                )
                goals.append(goal)
                self._goals[gid] = goal
        return goals

    def decompose_goals(self, goals: List[Goal]) -> List[Goal]:
        for g in goals:
            self._decomposer.decompose(g)
        return goals

    def schedule_goals(self, goals: List[Goal]) -> Dict[str, Any]:
        return self._planner.schedule(goals)

    def detect_synergies(self, goals: List[Goal]) -> List[Dict[str, Any]]:
        return self._synergy.detect(goals)

    def _priority_for_need(self, need: str) -> GoalPriority:
        mapping = {
            "security_threat": GoalPriority.CRITICAL, "memory_low": GoalPriority.CRITICAL,
            "cpu_high": GoalPriority.HIGH, "error_rate_high": GoalPriority.HIGH,
            "disk_full": GoalPriority.HIGH, "network_slow": GoalPriority.MEDIUM,
            "new_user": GoalPriority.MEDIUM, "skill_gap": GoalPriority.LOW,
        }
        return mapping.get(need, GoalPriority.MEDIUM)

    def prioritize(self, goals: List[Goal]) -> List[Goal]:
        return sorted(goals, key=lambda g: (g.priority.value, g.created_at))

    def resolve_dependencies(self, goals: List[Goal]) -> List[Goal]:
        for g in goals:
            if g.name in ["scale_storage", "parallelize", "flush_unused"]:
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
                if g1.name == "scale_storage" and g2.name == "cleanup_temp":
                    conflicts.append({"type": "redundant", "goals": [g1.id, g2.id], "resolution": "cleanup_first"})
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
            return [f"step: prepare {g.name}", f"step: execute {g.name}", f"step: verify {g.name}"]
        return [f"blocked: waiting for {g.prerequisites}"]

    def execute(self, goal_id: str) -> Dict[str, Any]:
        g = self._goals.get(goal_id)
        if not g or g.status != GoalStatus.PLANNED:
            return {"error": "Goal not ready"}
        g.status = GoalStatus.EXECUTING
        return {"goal_id": goal_id, "status": "executing", "started": time.time(), "subgoals": len(g.subgoals)}

    def complete(self, goal_id: str, success: bool = True) -> None:
        g = self._goals.get(goal_id)
        if g:
            g.status = GoalStatus.COMPLETED if success else GoalStatus.FAILED
            g.completed_at = time.time()
            g.success_rate = 1.0 if success else 0.0

    def abandon(self, goal_id: str, reason: str) -> None:
        g = self._goals.get(goal_id)
        if g and g.status in (GoalStatus.DETECTED, GoalStatus.PROPOSED, GoalStatus.APPROVED, GoalStatus.PLANNED):
            g.status = GoalStatus.ABANDONED
            g.metadata["abandon_reason"] = reason

    def reevaluate(self, system_state: Dict[str, Any]) -> List[str]:
        """Re-evaluate active goals against current state. Abandon if no longer relevant."""
        abandoned = []
        current_needs = set(self.detect_needs(system_state))
        for g in self.get_active():
            if not any(n in current_needs for n in g.needs):
                self.abandon(g.id, "Need no longer present in system state")
                abandoned.append(g.id)
        return abandoned

    def archive(self, goal_id: str) -> None:
        g = self._goals.get(goal_id)
        if g and g.status in (GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.ABANDONED):
            g.status = GoalStatus.ARCHIVED

    def get_active(self) -> List[Goal]:
        return [g for g in self._goals.values() if g.status not in (GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.ARCHIVED, GoalStatus.ABANDONED)]

    def get_stats(self) -> Dict[str, Any]:
        status_counts = {s.name: 0 for s in GoalStatus}
        for g in self._goals.values():
            status_counts[g.status.name] += 1
        return {
            "total_goals": len(self._goals), "active": len(self.get_active()),
            "needs_detected": len(self._detector._history), "status_breakdown": status_counts,
        }


if __name__ == "__main__":
    engine = GoalFormationEngine()
    state = {"memory_usage": 0.92, "cpu_usage": 0.45, "error_rate": 0.02, "security_alert": True, "disk_usage": 0.95}
    needs = engine.detect_needs(state)
    print(f"Detected needs: {needs}")
    print(f"Memory trend: {engine.get_trend('memory_usage')}")
    goals = engine.generate_goals(needs)
    goals = engine.decompose_goals(goals)
    goals = engine.resolve_dependencies(goals)
    conflicts = engine.check_conflicts(goals)
    print(f"Conflicts: {conflicts}")
    synergies = engine.detect_synergies(goals)
    print(f"Synergies: {synergies}")
    schedule = engine.schedule_goals(goals)
    print(f"Schedule: {schedule}")
    prioritized = engine.prioritize(goals)
    for g in prioritized[:5]:
        print(f"  {g.id} | {g.name} | {g.priority.name} | subgoals={len(g.subgoals)} | resources={g.resource_estimate}")
    for g in prioritized[:3]:
        engine.approve(g.id)
        engine.plan(g.id)
        print(f"Approved & planned: {g.id} -> {g.status.name}")
    # Test re-evaluation
    new_state = {"memory_usage": 0.6, "cpu_usage": 0.4, "error_rate": 0.01, "security_alert": False}
    abandoned = engine.reevaluate(new_state)
    print(f"Abandoned after re-evaluation: {abandoned}")
    print(f"Stats: {engine.get_stats()}")
