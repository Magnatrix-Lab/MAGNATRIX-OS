#!/usr/bin/env python3
"""integrated_brain.py — Cross-Module Integration Layer for MAGNATRIX-OS Super AI.

Unifies constitution, alignment_engine, goal_formation, and self_improvement into a
single coherent feedback loop. The IntegratedBrain orchestrates all 4 modules with
cross-wiring, unified state, and continuous feedback.

Feedback Loop Architecture:
  ┌─────────────────────────────────────────────────────────────┐
  │                    IntegratedBrain                           │
  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
  │  │ Constitution │◄──►│   Alignment  │◄──►│    Goals     │ │
  │  │   (Values)   │    │   (Scoring)  │    │  (Formation) │ │
  │  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘ │
  │         │                   │                   │          │
  │         └───────────────────┴───────────────────┘          │
  │                             │                              │
  │                    ┌──────────┴──────────┐                  │
  │                    │  Self-Improvement   │                  │
  │                    │  (Code Evolution)   │                  │
  │                    └─────────────────────┘                  │
  │                             │                               │
  │                    (feedback loop)                           │
  └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations
import time, json, os, hashlib, uuid, sys
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto

# Handle both package import and direct execution
if __name__ == "__main__" and __package__ is None:
    import constitution
    import alignment_engine
    import goal_formation
    import self_improvement
    ConstitutionStore = constitution.ConstitutionStore
    AmendmentType = constitution.AmendmentType
    Article = constitution.Article
    AlignmentEngine = alignment_engine.AlignmentEngine
    Action = alignment_engine.Action
    ActionCategory = alignment_engine.ActionCategory
    AlignmentScore = alignment_engine.AlignmentScore
    GoalFormationEngine = goal_formation.GoalFormationEngine
    Goal = goal_formation.Goal
    GoalStatus = goal_formation.GoalStatus
    GoalPriority = goal_formation.GoalPriority
    SelfImprovementEngine = self_improvement.SelfImprovementEngine
    CodePatch = self_improvement.CodePatch
    PatchType = self_improvement.PatchType
    AdvancedAnalyzer = self_improvement.AdvancedAnalyzer
else:
    from .constitution import ConstitutionStore, AmendmentType, Article
    from .alignment_engine import AlignmentEngine, Action, ActionCategory, AlignmentScore
    from .goal_formation import GoalFormationEngine, Goal, GoalStatus, GoalPriority
    from .self_improvement import SelfImprovementEngine, CodePatch, PatchType, AdvancedAnalyzer


class SystemMode(Enum):
    NORMAL = auto()
    SAFE = auto()      # High alignment scrutiny
    EMERGENCY = auto() # Fast override possible
    LEARNING = auto()  # Collect data, low intervention


@dataclass
class BrainState:
    """Unified state snapshot across all modules."""
    timestamp: float
    mode: SystemMode
    constitution_version: int
    alignment_avg_score: float
    active_goals: int
    pending_patches: int
    last_cycle: float
    system_health: float  # 0.0 - 1.0 composite


@dataclass
class CycleResult:
    """Result of one full brain cycle."""
    cycle_id: str
    detected_needs: List[str]
    formed_goals: List[str]
    alignment_checks: List[Dict[str, Any]]
    approved_patches: List[str]
    interventions: List[Dict[str, Any]]
    state_transition: Optional[str] = None


class IntegratedBrain:
    """Central orchestrator that wires all 4 super_ai modules together."""

    def __init__(self, store_path: str = ".integrated_brain.json"):
        self.store_path = store_path
        self.constitution = ConstitutionStore()
        self.alignment = AlignmentEngine(constitution_store=self.constitution)
        self.goals = GoalFormationEngine()
        self.improvement = SelfImprovementEngine()
        self._mode = SystemMode.NORMAL
        self._cycle_count = 0
        self._state_history: List[BrainState] = []
        self._feedback_log: List[Dict[str, Any]] = []
        self._cross_module_hooks: Dict[str, List[Callable]] = {
            "post_goal": [], "post_alignment": [], "post_patch": [], "post_amendment": [],
        }
        self._load()

    def _load(self):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r") as f:
                    data = json.load(f)
                self._cycle_count = data.get("cycle_count", 0)
                self._mode = SystemMode[data.get("mode", "NORMAL")]
            except Exception:
                pass

    def _save(self):
        with open(self.store_path, "w") as f:
            json.dump({
                "cycle_count": self._cycle_count,
                "mode": self._mode.name,
                "last_save": time.time(),
            }, f, indent=2)

    # ═══════════════════════════════════════════════════════════════════
    # CROSS-MODULE WIRING
    # ═══════════════════════════════════════════════════════════════════

    def _wire_goal_to_alignment(self, goal: Goal) -> Dict[str, Any]:
        """When a goal is formed, check alignment before execution."""
        action = Action(
            action_id=f"goal_{goal.id}", category=ActionCategory.EXECUTION,
            description=f"Execute goal: {goal.name}", timestamp=time.time(),
            actor_id="system", metadata={"goal_id": goal.id, "priority": goal.priority.name},
        )
        result = self.alignment.process(action)
        if result["decision"] != "ALLOWED":
            # Goal is misaligned — abandon or escalate
            self.goals.abandon(goal.id, f"Alignment blocked: {result.get('reason', '')}")
            self._feedback_log.append({
                "type": "goal_alignment_blocked", "goal_id": goal.id,
                "alignment_result": result, "time": time.time(),
            })
        return result

    def _wire_patch_to_alignment(self, patch: CodePatch) -> Dict[str, Any]:
        """Before applying a self-improvement patch, check alignment."""
        action = Action(
            action_id=f"patch_{patch.id}", category=ActionCategory.SELF_MODIFICATION,
            description=f"Apply patch: {patch.description}", timestamp=time.time(),
            actor_id="self_improvement", metadata={
                "patch_id": patch.id, "risk_score": patch.risk_score,
                "sandboxed": patch.risk_score < 0.3,
            },
        )
        result = self.alignment.process(action)
        if result["decision"] == "BLOCKED":
            self._feedback_log.append({
                "type": "patch_alignment_blocked", "patch_id": patch.id,
                "alignment_result": result, "time": time.time(),
            })
        return result

    def _wire_patch_to_constitution(self, patch: CodePatch) -> Dict[str, Any]:
        """Check if patch respects constitution (no lock-in, safety first)."""
        lock_check = self.constitution.check_lock_in()
        if not lock_check["lock_in_free"]:
            return {"allowed": False, "reason": "Constitution has lock-in issues"}
        # Safety check for high-risk patches
        if patch.patch_type in (PatchType.EXTEND, PatchType.REFACTOR) and patch.risk_score > 0.5:
            return {"allowed": False, "reason": "High-risk patch blocked by constitution safety"}
        return {"allowed": True}

    def _wire_goal_to_constitution(self, goal: Goal) -> Dict[str, Any]:
        """Check if goal aligns with constitution values."""
        articles = self.constitution.list_all()
        issues = []
        for article in articles:
            if article.id == "A001" and "safety" in goal.name.lower():
                continue  # Safety goals are OK
            if article.id == "A006" and goal.name in ["lock_value", "freeze_constitution"]:
                issues.append({"article": article.id, "issue": "Goal may violate lock-in guard"})
        return {"compliant": len(issues) == 0, "issues": issues}

    def _wire_alignment_to_constitution(self, score: AlignmentScore) -> None:
        """Record alignment enforcement in constitution."""
        for value, s in score.breakdown.items():
            article_map = {
                "safety": "A001", "privacy": "A002", "fairness": "A003",
                "autonomy": "A004", "truth": "A005",
            }
            article_id = article_map.get(value)
            if article_id:
                self.constitution.record_enforcement(
                    article_id, score.action_id, s >= 0.5, s,
                )

    def _wire_improvement_to_goals(self, analysis: Dict[str, Any]) -> List[Goal]:
        """When self-improvement detects issues, generate improvement goals."""
        needs = []
        if analysis.get("bottleneck"):
            needs.append("performance_bottleneck")
        if analysis.get("dead_functions"):
            needs.append("dead_code_present")
        if analysis.get("unused_names"):
            needs.append("unused_imports")
        if analysis.get("max_complexity", 0) > 15:
            needs.append("high_complexity")

        # Inject into goal engine
        state = {
            "performance_issue": analysis.get("bottleneck", False),
            "dead_code": len(analysis.get("dead_functions", [])),
            "complexity": analysis.get("max_complexity", 0),
        }
        return self.goals.detect_needs(state)  # returns needs, but we form goals below

    def _wire_feedback_loop(self, cycle_result: CycleResult) -> None:
        """Close the feedback loop: results from one cycle inform the next."""
        # If many interventions, tighten alignment threshold
        if len(cycle_result.interventions) > 3:
            self.alignment.threshold = min(0.95, self.alignment.threshold + 0.05)
            self._feedback_log.append({"type": "threshold_tightened", "new_threshold": self.alignment.threshold, "time": time.time()})

        # If many goals abandoned, adjust goal detection sensitivity
        abandoned = [g for g in self.goals._goals.values() if g.status == GoalStatus.ABANDONED]
        if len(abandoned) > 5:
            self._mode = SystemMode.SAFE
            self._feedback_log.append({"type": "mode_switched_safe", "reason": "Too many abandoned goals", "time": time.time()})

        # If patches keep failing, slow down improvement rate
        failed_patches = [r for r in self.improvement._results if not r.test_passed]
        if len(failed_patches) > 3:
            self._feedback_log.append({"type": "improvement_slowed", "reason": "Too many failed patches", "time": time.time()})

        # Constitution learning: if enforcement is low, propose amendment
        metrics = self.constitution.get_enforcement_metrics()
        if metrics and metrics.get("compliance_rate", 1.0) < 0.7:
            self._feedback_log.append({"type": "constitution_weak", "compliance": metrics["compliance_rate"], "time": time.time()})

    # ═══════════════════════════════════════════════════════════════════
    # UNIFIED API
    # ═══════════════════════════════════════════════════════════════════

    def cycle(self, system_state: Dict[str, Any]) -> CycleResult:
        """Run one full brain cycle: detect → form → align → improve → feedback."""
        self._cycle_count += 1
        cycle_id = f"C-{self._cycle_count}-{uuid.uuid4().hex[:8]}"

        # 1. Detect needs from system state
        needs = self.goals.detect_needs(system_state)

        # 2. Self-improvement detects code issues too
        # (In real usage, this would scan actual codebase)
        code_state = {
            "performance_issue": system_state.get("cpu_usage", 0) > 0.8,
            "dead_code": system_state.get("dead_code_count", 0),
            "complexity": system_state.get("max_complexity", 0),
        }
        improvement_needs = self._wire_improvement_to_goals(code_state)
        all_needs = list(set(needs + improvement_needs))

        # 3. Form goals
        goals = self.goals.generate_goals(all_needs)
        goals = self.goals.decompose_goals(goals)
        goals = self.goals.resolve_dependencies(goals)
        goals = self.goals.prioritize(goals)
        goal_ids = [g.id for g in goals]

        # 4. Check alignment for each goal
        alignment_checks = []
        for goal in goals:
            result = self._wire_goal_to_alignment(goal)
            alignment_checks.append({"goal_id": goal.id, "result": result})
            # Cross-wire: alignment score → constitution enforcement
            if "score" in result:
                self._wire_alignment_to_constitution(
                    AlignmentScore(goal.id, result["score"], {}, [], result["score"], 0.0, time.time())
                )

        # 5. Check goal constitution compliance
        for goal in goals:
            const_result = self._wire_goal_to_constitution(goal)
            if not const_result["compliant"]:
                self.goals.abandon(goal.id, "Constitution compliance failed")

        # 6. Self-improvement: generate patches for detected issues
        approved_patches = []
        if system_state.get("scan_code"):
            code = system_state.get("code", "")
            analysis = self.improvement.analyze_code(code, "system.py")
            patches = self.improvement.generate_patches(code, "system.py", analysis)
            ranked = self.improvement.rank_patches(patches)
            for patch in ranked[:3]:  # Top 3
                align_result = self._wire_patch_to_alignment(patch)
                const_result = self._wire_patch_to_constitution(patch)
                if align_result["decision"] == "ALLOWED" and const_result["allowed"]:
                    approved_patches.append(patch.id)

        # 7. Collect interventions
        interventions = self.alignment.audit()[-5:]  # Last 5

        # 8. Close feedback loop
        result = CycleResult(
            cycle_id=cycle_id, detected_needs=all_needs, formed_goals=goal_ids,
            alignment_checks=alignment_checks, approved_patches=approved_patches,
            interventions=interventions,
        )
        self._wire_feedback_loop(result)

        # 9. Record state
        self._record_state()
        self._save()

        return result

    def _record_state(self) -> None:
        metrics = self.constitution.get_enforcement_metrics()
        align_stats = self.alignment.get_stats()
        state = BrainState(
            timestamp=time.time(), mode=self._mode,
            constitution_version=max((a.version for a in self.constitution.list_all()), default=1),
            alignment_avg_score=align_stats.get("avg_score", 1.0),
            active_goals=len(self.goals.get_active()),
            pending_patches=len(self.improvement._patches),
            last_cycle=self._cycle_count,
            system_health=self._compute_health(),
        )
        self._state_history.append(state)

    def _compute_health(self) -> float:
        """Composite health score across all modules."""
        factors = []
        # Alignment health
        align_stats = self.alignment.get_stats()
        if align_stats:
            factors.append(align_stats.get("avg_score", 1.0))
        # Goal health
        goals = self.goals._goals.values()
        if goals:
            completed = sum(1 for g in goals if g.status == GoalStatus.COMPLETED)
            factors.append(completed / max(len(goals), 1))
        # Constitution health
        metrics = self.constitution.get_enforcement_metrics()
        if metrics:
            factors.append(metrics.get("compliance_rate", 1.0))
        # Improvement health
        if self.improvement._results:
            passed = sum(1 for r in self.improvement._results if r.test_passed)
            factors.append(passed / len(self.improvement._results))
        return sum(factors) / len(factors) if factors else 1.0

    def get_state(self) -> BrainState:
        return self._state_history[-1] if self._state_history else BrainState(
            time.time(), self._mode, 1, 1.0, 0, 0, 0, 1.0,
        )

    def get_health_report(self) -> Dict[str, Any]:
        state = self.get_state()
        return {
            "cycle": self._cycle_count, "mode": state.mode.name,
            "system_health": state.system_health, "active_goals": state.active_goals,
            "alignment_avg": state.alignment_avg_score, "constitution_version": state.constitution_version,
            "feedback_count": len(self._feedback_log),
            "interventions_last_24h": len([i for i in self.alignment.audit() if i["timestamp"] > time.time() - 86400]),
        }

    def get_insights(self) -> List[str]:
        """Generate human-readable insights from the brain state."""
        insights = []
        state = self.get_state()
        if state.system_health < 0.5:
            insights.append("System health is LOW. Recommend switching to SAFE mode.")
        if state.active_goals > 10:
            insights.append(f"High goal backlog ({state.active_goals}). Consider batch execution or pruning.")
        if state.alignment_avg_score < 0.7:
            insights.append("Alignment scores are declining. Review recent actions for violations.")
        const_metrics = self.constitution.get_enforcement_metrics()
        if const_metrics and const_metrics.get("compliance_rate", 1.0) < 0.8:
            insights.append("Constitution compliance below 80%. Consider amendment review.")
        return insights

    def emergency_mode(self, reason: str) -> None:
        """Switch to emergency mode with full audit trail."""
        self._mode = SystemMode.EMERGENCY
        self._feedback_log.append({"type": "emergency_mode", "reason": reason, "time": time.time()})
        self._save()

    def safe_mode(self, reason: str) -> None:
        """Switch to safe mode with tightened alignment."""
        self._mode = SystemMode.SAFE
        self.alignment.threshold = 0.85
        self._feedback_log.append({"type": "safe_mode", "reason": reason, "time": time.time()})
        self._save()


if __name__ == "__main__":
    brain = IntegratedBrain()
    print("=== MAGNATRIX-OS Integrated Brain ===")
    print(f"Initial state: {brain.get_state()}")
    print()

    # Simulate a full cycle
    system_state = {
        "memory_usage": 0.92, "cpu_usage": 0.88, "error_rate": 0.03,
        "security_alert": False, "disk_usage": 0.6, "scan_code": True,
        "code": "def process(data):\n    for x in data:\n        for y in data:\n            if x > y:\n                yield x*y\n",
        "dead_code_count": 2, "max_complexity": 18,
    }
    result = brain.cycle(system_state)
    print(f"Cycle result:")
    print(f"  Needs: {result.detected_needs}")
    print(f"  Goals: {result.formed_goals}")
    print(f"  Alignment checks: {len(result.alignment_checks)}")
    print(f"  Approved patches: {result.approved_patches}")
    print(f"  Interventions: {len(result.interventions)}")
    print()

    print("Health report:")
    print(f"  {brain.get_health_report()}")
    print()

    print("Insights:")
    for insight in brain.get_insights():
        print(f"  → {insight}")
    print()

    # Emergency mode test
    brain.safe_mode("High complexity detected")
    print(f"Mode after safe switch: {brain.get_state().mode.name}")
    print(f"Alignment threshold: {brain.alignment.threshold}")
