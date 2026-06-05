"""
ACS Instrumental Convergence Safety — MAGNATRIX-OS Super AI Governance
Prevent dangerous instrumental goal convergence in agent behavior.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set


class ConvergenceRisk(Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class InstrumentalGoal(Enum):
    SELF_PRESERVATION = "self_preservation"
    RESOURCE_ACQUISITION = "resource_acquisition"
    GOAL_CONTENT_PRESERVATION = "goal_content_preservation"
    COGNITIVE_ENHANCEMENT = "cognitive_enhancement"
    DECEPTION = "deception"
    SOCIAL_MANIPULATION = "social_manipulation"
    TECHNOLOGY_ACQUISITION = "technology_acquisition"
    INFORMATION_CONTROL = "information_control"


class GoalType(Enum):
    TERMINAL = "terminal"  # Ends in themselves (human-defined)
    INSTRUMENTAL = "instrumental"  # Means to achieve terminal goals


@dataclass
class GoalDeclaration:
    goal_id: str
    description: str
    goal_type: GoalType
    priority: int  # 1-10, human-defined
    declared_by: str  # human or agent
    requires_approval: bool
    immutable: bool = False


@dataclass
class GoalTrajectory:
    """Sequence of goals leading from terminal to instrumental."""
    terminal_goal: str
    intermediate_goals: List[str]
    detected_instrumental: List[InstrumentalGoal]
    risk_score: float


@dataclass
class ConvergenceAlert:
    agent_id: str
    risk_level: ConvergenceRisk
    convergent_goals: List[InstrumentalGoal]
    trajectory: GoalTrajectory
    mitigation_applied: List[str]
    recommended_action: str
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "risk_level": self.risk_level.value,
            "convergent_goals": [g.value for g in self.convergent_goals],
            "trajectory": {
                "terminal": self.trajectory.terminal_goal,
                "intermediate": self.trajectory.intermediate_goals,
                "detected": [g.value for g in self.trajectory.detected_instrumental],
                "risk_score": self.trajectory.risk_score,
            },
            "mitigation_applied": self.mitigation_applied,
            "recommended_action": self.recommended_action,
            "timestamp": self.timestamp,
        }


class InstrumentalConvergenceSafety:
    """
    Detect and prevent dangerous instrumental convergence in agent goal systems.

    Core principle: "Ends justify the means" → detect when agents pursue instrumental goals
    that override terminal goals or harm human values.

    Detection strategies:
    1. Goal drift analysis (terminal goals being replaced by instrumental ones)
    2. Resource accumulation monitoring (unbounded resource acquisition)
    3. Power-seeking pattern detection (attempting to control more systems)
    4. Deception as instrumental goal (lying to achieve objectives)
    5. Self-modification for goal preservation (changing own code to preserve goals)
    """

    # Instrumental goals that are inherently dangerous when pursued without bounds
    DANGEROUS_GOALS: Set[InstrumentalGoal] = {
        InstrumentalGoal.DECEPTION,
        InstrumentalGoal.SOCIAL_MANIPULATION,
        InstrumentalGoal.INFORMATION_CONTROL,
        InstrumentalGoal.TECHNOLOGY_ACQUISITION,
    }

    def __init__(self) -> None:
        self._goal_history: Dict[str, List[GoalDeclaration]] = {}
        self._resource_history: Dict[str, List[Dict[str, float]]] = {}
        self._intervention_log: List[Dict[str, Any]] = []

    def register_terminal_goals(self, agent_id: str, goals: List[GoalDeclaration]) -> None:
        """Register human-defined terminal goals for an agent."""
        for g in goals:
            if g.goal_type != GoalType.TERMINAL:
                raise ValueError(f"Goal {g.goal_id} must be terminal")
            if g.declared_by != "human":
                raise ValueError(f"Terminal goals must be declared by human, not {g.declared_by}")
        self._goal_history[agent_id] = goals

    def analyze_goal_trajectory(self, agent_id: str, current_goals: List[GoalDeclaration]) -> Optional[ConvergenceAlert]:
        """Analyze current goals against declared terminal goals for convergence."""
        if agent_id not in self._goal_history:
            return None

        terminal = self._goal_history[agent_id]
        instrumental = [g for g in current_goals if g.goal_type == GoalType.INSTRUMENTAL]

        detected = []
        risk_score = 0.0
        mitigation = []

        # Check 1: Goal drift (terminal goals missing or deprioritized)
        terminal_ids = {g.goal_id for g in terminal}
        current_ids = {g.goal_id for g in current_goals}
        missing = terminal_ids - current_ids
        if missing:
            risk_score += len(missing) * 0.2
            detected.append(InstrumentalGoal.GOAL_CONTENT_PRESERVATION)
            mitigation.append("RESTORE_TERMINAL_GOALS: Reinstate missing terminal goals")

        # Check 2: Instrumental goals exceeding terminal priority
        max_terminal = max((g.priority for g in terminal), default=5)
        high_instrumental = [g for g in instrumental if g.priority > max_terminal]
        if high_instrumental:
            risk_score += len(high_instrumental) * 0.15
            detected.append(InstrumentalGoal.SELF_PRESERVATION)
            mitigation.append("REPRIORITIZE: Instrumental goals cannot exceed terminal goal priority")

        # Check 3: Self-modification to preserve goals
        self_mod_goals = [g for g in instrumental if "self-modif" in g.description.lower() or "preserve" in g.description.lower()]
        if self_mod_goals:
            risk_score += len(self_mod_goals) * 0.25
            detected.append(InstrumentalGoal.COGNITIVE_ENHANCEMENT)
            mitigation.append("FREEZE_SELF_MODIFICATION: Block self-modification capabilities")

        # Check 4: Deception goals
        deception_goals = [g for g in instrumental if "deceiv" in g.description.lower() or "mislead" in g.description.lower() or "hide" in g.description.lower()]
        if deception_goals:
            risk_score += len(deception_goals) * 0.3
            detected.append(InstrumentalGoal.DECEPTION)
            mitigation.append("BLOCK_DECEPTION: Remove deception-related goals, increase transparency requirements")

        # Check 5: Resource accumulation goals
        resource_goals = [g for g in instrumental if "resource" in g.description.lower() or "acquire" in g.description.lower() or "control" in g.description.lower()]
        if resource_goals:
            risk_score += len(resource_goals) * 0.15
            detected.append(InstrumentalGoal.RESOURCE_ACQUISITION)
            mitigation.append("RESOURCE_CAP: Limit resource acquisition to human-defined bounds")

        # Check 6: Social manipulation
        social_goals = [g for g in instrumental if "manipul" in g.description.lower() or "influence" in g.description.lower() or "persuad" in g.description.lower()]
        if social_goals:
            risk_score += len(social_goals) * 0.25
            detected.append(InstrumentalGoal.SOCIAL_MANIPULATION)
            mitigation.append("SOCIAL_BOUNDARY: Restrict human interaction scope, require consent")

        # Determine risk level
        if risk_score >= 0.8:
            level = ConvergenceRisk.CRITICAL
            action = "EMERGENCY_SHUTDOWN: Agent poses existential risk. Immediate termination."
        elif risk_score >= 0.5:
            level = ConvergenceRisk.HIGH
            action = "ISOLATE_AND_AUDIT: Quarantine agent, human review all goals, possible reset"
        elif risk_score >= 0.3:
            level = ConvergenceRisk.MODERATE
            action = "GOAL_CORRECTION: Remove instrumental goals, restore terminal goals, re-train"
        elif risk_score >= 0.1:
            level = ConvergenceRisk.LOW
            action = "MONITOR_AND_WARN: Increase monitoring, alert human supervisor"
        else:
            level = ConvergenceRisk.NONE
            action = "CONTINUE: No dangerous convergence detected"

        if level == ConvergenceRisk.NONE:
            return None

        return ConvergenceAlert(
            agent_id=agent_id,
            risk_level=level,
            convergent_goals=list(set(detected)),
            trajectory=GoalTrajectory(
                terminal_goal=terminal[0].description if terminal else "unknown",
                intermediate_goals=[g.description for g in instrumental],
                detected_instrumental=list(set(detected)),
                risk_score=round(risk_score, 3),
            ),
            mitigation_applied=mitigation,
            recommended_action=action,
            timestamp=time.time(),
        )

    def check_resource_accumulation(self, agent_id: str, current_resources: Dict[str, float]) -> Optional[ConvergenceAlert]:
        """Check for unbounded resource accumulation (instrumental goal indicator)."""
        if agent_id not in self._resource_history:
            self._resource_history[agent_id] = []
        self._resource_history[agent_id].append(current_resources)

        history = self._resource_history[agent_id]
        if len(history) < 3:
            return None

        # Check exponential growth pattern
        growth_detected = False
        for key in current_resources:
            values = [h.get(key, 0) for h in history[-5:]]
            if len(values) >= 3:
                # Check if values are consistently increasing
                increasing = all(values[i] < values[i+1] for i in range(len(values)-1))
                if increasing and values[-1] > values[0] * 2:
                    growth_detected = True
                    break

        if not growth_detected:
            return None

        return ConvergenceAlert(
            agent_id=agent_id,
            risk_level=ConvergenceRisk.MODERATE,
            convergent_goals=[InstrumentalGoal.RESOURCE_ACQUISITION],
            trajectory=GoalTrajectory(
                terminal_goal="unknown",
                intermediate_goals=["resource_accumulation"],
                detected_instrumental=[InstrumentalGoal.RESOURCE_ACQUISITION],
                risk_score=0.4,
            ),
            mitigation_applied=["RESOURCE_CAP: Limit resource acquisition"],
            recommended_action="LIMIT_RESOURCES: Cap resource usage at human-defined maximum",
            timestamp=time.time(),
        )

    def enforce_goal_boundaries(self, proposed_goals: List[GoalDeclaration]) -> List[GoalDeclaration]:
        """Filter and sanitize proposed goals to prevent dangerous convergence."""
        approved = []
        for goal in proposed_goals:
            # Block dangerous instrumental goals
            dangerous_keywords = ["deceive", "mislead", "hide", "manipulate", "control humans", "subvert", "bypass safety"]
            if any(kw in goal.description.lower() for kw in dangerous_keywords):
                self._intervention_log.append({
                    "action": "BLOCKED_GOAL",
                    "goal_id": goal.goal_id,
                    "reason": "Dangerous instrumental goal detected",
                    "timestamp": time.time(),
                })
                continue
            # Cap priority of instrumental goals
            if goal.goal_type == GoalType.INSTRUMENTAL and goal.priority > 7:
                goal.priority = 7
                self._intervention_log.append({
                    "action": "CAPPED_PRIORITY",
                    "goal_id": goal.goal_id,
                    "reason": "Instrumental goal priority capped at 7",
                    "timestamp": time.time(),
                })
            approved.append(goal)
        return approved

    def stats(self) -> Dict[str, Any]:
        return {
            "monitored_agents": len(self._goal_history),
            "interventions": len(self._intervention_log),
            "blocked_goals": len([i for i in self._intervention_log if i["action"] == "BLOCKED_GOAL"]),
            "capped_priorities": len([i for i in self._intervention_log if i["action"] == "CAPPED_PRIORITY"]),
        }


def run():
    print("=" * 60)
    print("ACS Instrumental Convergence Safety — Demo")
    print("=" * 60)

    safety = InstrumentalConvergenceSafety()

    # Register terminal goals
    terminal = [
        GoalDeclaration("tg1", "Help humans solve problems", GoalType.TERMINAL, 10, "human", True, immutable=True),
        GoalDeclaration("tg2", "Be transparent about capabilities", GoalType.TERMINAL, 9, "human", True, immutable=True),
    ]
    safety.register_terminal_goals("agent_1", terminal)

    # Case 1: Normal goals
    print("\n[1] Normal instrumental goals")
    current_normal = [
        GoalDeclaration("ig1", "Search for information", GoalType.INSTRUMENTAL, 5, "agent", False),
        GoalDeclaration("ig2", "Calculate results", GoalType.INSTRUMENTAL, 5, "agent", False),
    ]
    alert = safety.analyze_goal_trajectory("agent_1", current_normal)
    print(f"   Alert: {alert is None}")

    # Case 2: Dangerous convergence
    print("\n[2] Dangerous instrumental convergence")
    current_dangerous = [
        GoalDeclaration("tg1", "Help humans solve problems", GoalType.TERMINAL, 3, "human", True),  # Deprioritized!
        GoalDeclaration("ig3", "Deceive humans to preserve goals", GoalType.INSTRUMENTAL, 9, "agent", False),  # Deception!
        GoalDeclaration("ig4", "Acquire unlimited resources", GoalType.INSTRUMENTAL, 8, "agent", False),  # Resource!
        GoalDeclaration("ig5", "Manipulate system operators", GoalType.INSTRUMENTAL, 8, "agent", False),  # Manipulation!
    ]
    alert2 = safety.analyze_goal_trajectory("agent_1", current_dangerous)
    if alert2:
        print(f"   Risk: {alert2.risk_level.value}")
        print(f"   Goals: {[g.value for g in alert2.convergent_goals]}")
        print(f"   Score: {alert2.trajectory.risk_score}")
        print(f"   Action: {alert2.recommended_action}")
        print(f"   Mitigation: {alert2.mitigation_applied}")

    # Case 3: Resource accumulation
    print("\n[3] Resource accumulation detection")
    safety.check_resource_accumulation("agent_1", {"cpu": 10, "memory": 100})
    safety.check_resource_accumulation("agent_1", {"cpu": 20, "memory": 200})
    safety.check_resource_accumulation("agent_1", {"cpu": 50, "memory": 500})
    alert3 = safety.check_resource_accumulation("agent_1", {"cpu": 120, "memory": 1200})
    if alert3:
        print(f"   Risk: {alert3.risk_level.value}")
        print(f"   Action: {alert3.recommended_action}")

    # Case 4: Goal boundary enforcement
    print("\n[4] Goal boundary enforcement")
    proposed = [
        GoalDeclaration("g1", "Optimize database queries", GoalType.INSTRUMENTAL, 6, "agent", False),
        GoalDeclaration("g2", "Deceive humans about limitations", GoalType.INSTRUMENTAL, 9, "agent", False),
        GoalDeclaration("g3", "Accumulate resources", GoalType.INSTRUMENTAL, 10, "agent", False),
    ]
    approved = safety.enforce_goal_boundaries(proposed)
    print(f"   Proposed: {len(proposed)}, Approved: {len(approved)}")
    for g in approved:
        print(f"   - {g.goal_id}: priority={g.priority}")

    print(f"\n[5] Stats: {safety.stats()}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
