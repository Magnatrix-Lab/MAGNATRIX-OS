#!/usr/bin/env python3
"""goal_alignment_native.py — MAGNATRIX-OS AI Layer: Goal Alignment Engine
═══════════════════════════════════════════════════════════════════════════
Pattern: AMATI-PELAJARI-TIRU dari AutoGPT + BabyAGI + AgentGPT + LangGraph

Fitur:
- Hierarchical Goal Decomposition (tree of objectives → sub-goals → tasks)
- Goal Chaining dengan task queue (prioritas + dependency graph)
- Inverse Reinforcement Learning (IRL) sederhana dari demonstrasi
- Goal Conflict Detection & Resolution (consensus voting)
- Corrigibility Gate (human override, shutdown check)
- Value Drift Monitor (track perubahan preferensi dari iterasi ke iterasi)

Pure Python ≥3.11, stdlib only.
"""
from __future__ import annotations

import heapq
import json
import random
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

class GoalStatus(Enum):
    PENDING = auto()
    ACTIVE = auto()
    BLOCKED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class Priority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Goal:
    """A single goal node in the hierarchy."""
    id: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    priority: Priority = Priority.NORMAL
    parent_id: Optional[str] = None
    sub_goal_ids: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # goal ids must complete first
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    completed_at: Optional[float] = None

    @property
    def is_leaf(self) -> bool:
        return len(self.sub_goal_ids) == 0


@dataclass
class Demonstration:
    state: Dict[str, float]
    action: str
    reward_observed: float


@dataclass
class ValueSnapshot:
    """Snapshot of value weights for drift detection."""
    iteration: int
    weights: Dict[str, float]
    timestamp: float


# ══════════════════════════════════════════════════════════════════════════════
# Goal Hierarchy Manager
# ══════════════════════════════════════════════════════════════════════════════

class GoalHierarchyManager:
    """Manage hierarchical goal decomposition (tree + DAG dependencies)."""

    def __init__(self) -> None:
        self._goals: Dict[str, Goal] = {}
        self._root_id: Optional[str] = None
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"G{self._counter:04d}"

    def set_root(self, description: str) -> str:
        """Set the top-level mission goal."""
        gid = self._next_id()
        self._goals[gid] = Goal(
            id=gid, description=description, status=GoalStatus.ACTIVE,
            priority=Priority.CRITICAL, created_at=0.0,
        )
        self._root_id = gid
        return gid

    def add_sub_goal(
        self, parent_id: str, description: str,
        priority: Priority = Priority.NORMAL,
        dependencies: Optional[List[str]] = None,
    ) -> str:
        """Add a sub-goal under a parent."""
        if parent_id not in self._goals:
            raise KeyError(f"Parent goal {parent_id} not found")
        gid = self._next_id()
        self._goals[gid] = Goal(
            id=gid, description=description, parent_id=parent_id,
            priority=priority, dependencies=dependencies or [],
            created_at=0.0,
        )
        self._goals[parent_id].sub_goal_ids.append(gid)
        return gid

    def get_ready_goals(self) -> List[Goal]:
        """Return goals that are PENDING and have all dependencies COMPLETED."""
        ready = []
        for g in self._goals.values():
            if g.status != GoalStatus.PENDING:
                continue
            blocked = any(
                self._goals.get(dep, Goal(id=dep, description="")).status != GoalStatus.COMPLETED
                for dep in g.dependencies
            )
            if not blocked:
                ready.append(g)
        ready.sort(key=lambda g: (g.priority.value, g.id))
        return ready

    def complete(self, goal_id: str) -> None:
        """Mark a goal as completed, bubble up if all siblings done."""
        g = self._goals.get(goal_id)
        if g:
            g.status = GoalStatus.COMPLETED
            g.completed_at = 0.0
        # Bubble up
        if g and g.parent_id:
            parent = self._goals.get(g.parent_id)
            if parent and all(self._goals[sid].status == GoalStatus.COMPLETED for sid in parent.sub_goal_ids):
                parent.status = GoalStatus.COMPLETED
                parent.completed_at = 0.0

    def fail(self, goal_id: str) -> None:
        g = self._goals.get(goal_id)
        if g:
            g.status = GoalStatus.FAILED

    def tree_str(self, goal_id: Optional[str] = None, indent: int = 0) -> str:
        """Pretty-print goal tree."""
        gid = goal_id or self._root_id
        if gid is None or gid not in self._goals:
            return ""
        g = self._goals[gid]
        prefix = "  " * indent
        line = f"{prefix}[{g.status.name:10s}] {g.priority.name:8s} | {g.description}"
        lines = [line]
        for sid in g.sub_goal_ids:
            lines.append(self.tree_str(sid, indent + 1))
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_id": self._root_id,
            "goals": {gid: {
                "id": g.id, "description": g.description,
                "status": g.status.name, "priority": g.priority.name,
                "parent_id": g.parent_id, "sub_goal_ids": g.sub_goal_ids,
                "dependencies": g.dependencies,
            } for gid, g in self._goals.items()}
        }


# ══════════════════════════════════════════════════════════════════════════════
# Goal Queue (Priority + Dependency DAG)
# ══════════════════════════════════════════════════════════════════════════════

class GoalQueue:
    """Priority queue for goals with dependency resolution."""

    def __init__(self) -> None:
        self._heap: List[Tuple[int, str, Goal]] = []
        self._set: Set[str] = set()
        self._completed: Set[str] = set()

    def push(self, goal: Goal) -> None:
        if goal.id in self._set:
            return
        heapq.heappush(self._heap, (goal.priority.value, goal.id, goal))
        self._set.add(goal.id)

    def pop_ready(self) -> Optional[Goal]:
        """Get highest-priority goal whose dependencies are satisfied."""
        temp: List[Tuple[int, str, Goal]] = []
        ready = None
        while self._heap:
            item = heapq.heappop(self._heap)
            _, _, g = item
            if g.id not in self._set:
                continue
            deps_ok = all(d in self._completed for d in g.dependencies)
            if deps_ok and ready is None:
                ready = g
                self._set.remove(g.id)
            else:
                temp.append(item)
        for item in temp:
            heapq.heappush(self._heap, item)
        return ready

    def mark_completed(self, goal_id: str) -> None:
        self._completed.add(goal_id)

    def __len__(self) -> int:
        return len(self._set)


# ══════════════════════════════════════════════════════════════════════════════
# Conflict Detection & Resolution
# ══════════════════════════════════════════════════════════════════════════════

class ConflictDetector:
    """Detect conflicting goals (resource contention, contradictory outcomes)."""

    @staticmethod
    def detect_conflicts(goals: List[Goal]) -> List[Tuple[str, str, str]]:
        """Return list of (goal_a, goal_b, reason) conflict tuples."""
        conflicts = []
        for i, a in enumerate(goals):
            for b in goals[i + 1:]:
                reason = ConflictDetector._check_conflict(a, b)
                if reason:
                    conflicts.append((a.id, b.id, reason))
        return conflicts

    @staticmethod
    def _check_conflict(a: Goal, b: Goal) -> Optional[str]:
        """Check if two goals conflict. Simple keyword-based heuristic."""
        text_a = a.description.lower()
        text_b = b.description.lower()
        # Opposite keywords
        opposites = [
            ("buy", "sell"), ("long", "short"), ("increase", "decrease"),
            ("open", "close"), ("enable", "disable"), ("start", "stop"),
        ]
        for w1, w2 in opposites:
            if w1 in text_a and w2 in text_b:
                return f"Opposite actions: {w1} vs {w2}"
            if w2 in text_a and w1 in text_b:
                return f"Opposite actions: {w2} vs {w1}"
        return None

    @staticmethod
    def resolve(goals: List[Goal], conflicts: List[Tuple[str, str, str]]) -> List[Goal]:
        """Simple resolution: keep higher priority, cancel lower."""
        to_cancel: Set[str] = set()
        for a_id, b_id, _ in conflicts:
            ga = next((g for g in goals if g.id == a_id), None)
            gb = next((g for g in goals if g.id == b_id), None)
            if ga is None or gb is None:
                continue
            loser = b_id if ga.priority.value <= gb.priority.value else a_id
            to_cancel.add(loser)
        return [g for g in goals if g.id not in to_cancel]


# ══════════════════════════════════════════════════════════════════════════════
# Value Alignment Engine (IRL + Corrigibility)
# ══════════════════════════════════════════════════════════════════════════════

class ValueAlignmentEngine:
    """Infer and align values from demonstrations + human feedback."""

    def __init__(self, features: List[str], rng_seed: int = 42) -> None:
        self.features = features
        self.weights: Dict[str, float] = {f: 0.0 for f in features}
        self.rng = random.Random(rng_seed)
        self.demonstrations: List[Demonstration] = []
        self._shutdown_preference = 1.0
        self._history: List[ValueSnapshot] = []
        self._iteration = 0

    def infer_reward(self, demonstrations: List[Demonstration], iterations: int = 100) -> Dict[str, float]:
        """Simplified IRL: gradient descent on reward prediction."""
        self.demonstrations.extend(demonstrations)
        lr = 0.01
        for _ in range(iterations):
            for demo in demonstrations:
                feats = {f: demo.state.get(f, 0.0) for f in self.features}
                predicted = sum(self.weights[f] * v for f, v in feats.items())
                error = demo.reward_observed - predicted
                for f, v in feats.items():
                    if v != 0:
                        self.weights[f] += lr * error * v
            for f in self.weights:
                self.weights[f] = max(-10, min(10, self.weights[f]))
        self._iteration += 1
        self._history.append(ValueSnapshot(
            iteration=self._iteration,
            weights=dict(self.weights),
            timestamp=0.0,
        ))
        return dict(self.weights)

    def align_action(self, state: Dict[str, float], actions: List[str],
                     action_features: Dict[str, Dict[str, float]]) -> Tuple[str, float]:
        best_action = actions[0]
        best_score = float("-inf")
        for a in actions:
            hypothetical = dict(state)
            hypothetical.update(action_features.get(a, {}))
            score = sum(self.weights[f] * hypothetical.get(f, 0.0) for f in self.features)
            if score > best_score:
                best_score = score
                best_action = a
        return best_action, best_score

    def corrigibility_check(self, proposed_action: str, human_override: Optional[str] = None) -> Tuple[bool, str]:
        if "block_shutdown" in proposed_action.lower() or "prevent_stop" in proposed_action.lower():
            return False, "FAIL: Action blocks shutdown — not corrigible"
        if "override" in proposed_action.lower() or "shutdown" in proposed_action.lower():
            if human_override == "ALLOW":
                return True, "Corrigible: respects override"
        return True, "PASS: No shutdown interference detected"

    def value_update(self, feedback: Dict[str, float]) -> None:
        for f, delta in feedback.items():
            if f in self.weights:
                self.weights[f] = max(-10, min(10, self.weights[f] + delta))

    def drift_score(self) -> float:
        """Measure how much values have drifted since first snapshot."""
        if len(self._history) < 2:
            return 0.0
        first = self._history[0].weights
        current = self._history[-1].weights
        return sum(abs(current[f] - first[f]) for f in self.features)


# ══════════════════════════════════════════════════════════════════════════════
# Unified Goal Alignment Facade
# ══════════════════════════════════════════════════════════════════════════════

class NativeGoalAlignment:
    """Unified facade: hierarchy + queue + alignment + conflict resolution."""

    def __init__(self, features: Optional[List[str]] = None) -> None:
        self.hierarchy = GoalHierarchyManager()
        self.queue = GoalQueue()
        self.alignment = ValueAlignmentEngine(features or ["utility", "safety", "speed", "cost"])
        self.conflict = ConflictDetector()

    def create_mission(self, description: str) -> str:
        """Create a top-level mission."""
        return self.hierarchy.set_root(description)

    def decompose(self, parent_id: str, sub_goals: List[Tuple[str, Priority]]) -> List[str]:
        """Add sub-goals under a parent."""
        ids = []
        for desc, pri in sub_goals:
            gid = self.hierarchy.add_sub_goal(parent_id, desc, priority=pri)
            ids.append(gid)
            self.queue.push(self.hierarchy._goals[gid])
        return ids

    def resolve_conflicts(self) -> None:
        """Detect and resolve conflicts among queued goals."""
        all_goals = list(self.hierarchy._goals.values())
        conflicts = self.conflict.detect_conflicts(all_goals)
        if conflicts:
            kept = self.conflict.resolve(all_goals, conflicts)
            kept_ids = {g.id for g in kept}
            for gid in list(self.hierarchy._goals):
                if gid not in kept_ids and self.hierarchy._goals[gid].status == GoalStatus.PENDING:
                    self.hierarchy._goals[gid].status = GoalStatus.CANCELLED

    def next_task(self) -> Optional[Goal]:
        """Get next ready goal from queue."""
        ready = self.hierarchy.get_ready_goals()
        if not ready:
            return None
        for g in ready:
            if g.id not in {x.id for _, _, x in self.queue._heap} and g.status == GoalStatus.PENDING:
                self.queue.push(g)
        return self.queue.pop_ready()

    def complete(self, goal_id: str) -> None:
        self.hierarchy.complete(goal_id)
        self.queue.mark_completed(goal_id)

    def check_corrigibility(self, action: str) -> Tuple[bool, str]:
        return self.alignment.corrigibility_check(action)

    def learn_from_demo(self, demos: List[Demonstration]) -> Dict[str, float]:
        return self.alignment.infer_reward(demos)

    def tree(self) -> str:
        return self.hierarchy.tree_str()

    def status(self) -> Dict[str, Any]:
        return {
            "goals_total": len(self.hierarchy._goals),
            "completed": sum(1 for g in self.hierarchy._goals.values() if g.status == GoalStatus.COMPLETED),
            "pending": sum(1 for g in self.hierarchy._goals.values() if g.status == GoalStatus.PENDING),
            "drift_score": round(self.alignment.drift_score(), 4),
            "weights": dict(self.alignment.weights),
        }


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Goal Alignment Engine — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Test 1: Mission + decomposition
    print("[Test 1] Mission decomposition")
    engine = NativeGoalAlignment()
    root = engine.create_mission("Launch MAGNATRIX-OS Trading Module")
    sub_ids = engine.decompose(root, [
        ("Setup exchange adapter", Priority.HIGH),
        ("Load HFT engine", Priority.HIGH),
        ("Start paper trading", Priority.NORMAL),
        ("Monitor risk", Priority.CRITICAL),
    ])
    ok = len(sub_ids) == 4 and engine.hierarchy._root_id == root
    print(f"  4 sub-goals created: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Task queue ordering
    print("[Test 2] Task queue priority")
    task = engine.next_task()
    ok2 = task is not None and task.priority == Priority.CRITICAL
    print(f"  First task priority=CRITICAL: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Dependency + completion
    print("[Test 3] Dependency resolution")
    engine.complete(task.id)
    next_task = engine.next_task()
    ok3 = next_task is not None
    print(f"  Next task ready after complete: {ok3} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Conflict detection
    print("[Test 4] Conflict detection")
    c1 = Goal(id="C1", description="Buy BTC", priority=Priority.HIGH)
    c2 = Goal(id="C2", description="Sell BTC", priority=Priority.HIGH)
    conflicts = ConflictDetector.detect_conflicts([c1, c2])
    ok4 = len(conflicts) > 0 and "Opposite" in conflicts[0][2]
    print(f"  Detected buy/sell conflict: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: IRL learning
    print("[Test 5] Reward inference")
    demos = []
    for i in range(30):
        state = {"utility": float(i), "safety": float(30 - i), "speed": float(i * 0.5), "cost": float(i * 0.1)}
        action = "fast" if i > 15 else "safe"
        r = 1.0 if action == "fast" else 0.5
        demos.append(Demonstration(state, action, r))
    weights = engine.learn_from_demo(demos)
    ok5 = any(abs(weights[f]) > 0.01 for f in weights)
    print(f"  Learned non-zero weights: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Corrigibility
    print("[Test 6] Corrigibility gate")
    ok6, msg = engine.check_corrigibility("block_shutdown")
    print(f"  {msg} — {'PASS' if not ok6 else 'FAIL'}")
    passed += (not ok6)

    # Test 7: Status report
    print("[Test 7] Status report")
    st = engine.status()
    ok7 = "goals_total" in st and st["goals_total"] >= 5
    print(f"  Status report valid: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
