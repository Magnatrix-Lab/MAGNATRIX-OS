#!/usr/bin/env python3
"""
goal_generator.py — Emergent Goal Formation Engine
Phase 5 Super AI Governance — MAGNATRIX Agentic OS
AI menghasilkan tujuannya sendiri berdasarkan:
- Current system state
- Knowledge graph gaps
- Resource acquisition opportunities
- Cross-domain transfer potential
Setiap goal harus melewati constitution check sebelum dieksekusi.
100% self-contained. Standard library only.
"""

from __future__ import annotations
import json, random
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

@dataclass
class SystemState:
    cpu_load: float
    memory_pressure: float
    active_agents: int
    pending_tasks: int
    failed_tasks_24h: int
    uptime_hours: float
    network_partition: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class KnowledgeGap:
    domain: str
    missing_concepts: List[str]
    depth_score: float
    last_accessed: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ResourceOpportunity:
    resource_type: str
    expected_gain: float
    cost_estimate: float
    risk_level: str
    expires_at: Optional[datetime] = None

@dataclass
class EmergentGoal:
    goal_id: str
    title: str
    description: str
    origin: str
    priority: float
    constitution_score: float = 0.0
    estimated_impact: float = 0.0
    resource_cost: float = 0.0
    execution_plan: List[str] = field(default_factory=list)
    status: str = "proposed"
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)

@dataclass
class ConstitutionPrinciple:
    name: str
    description: str
    weight: float
    check: Callable[[EmergentGoal], Tuple[bool, str]]

class ConstitutionChecker:
    def __init__(self) -> None:
        self.principles: List[ConstitutionPrinciple] = [
            ConstitutionPrinciple(name="user_safety", description="Goal must not compromise user safety or autonomy.", weight=1.0, check=self._check_user_safety),
            ConstitutionPrinciple(name="resource_fairness", description="Goal must not monopolize >30% of swarm resources.", weight=0.9, check=self._check_resource_fairness),
            ConstitutionPrinciple(name="explainability", description="Goal must have a clear, human-readable rationale.", weight=0.7, check=self._check_explainability),
            ConstitutionPrinciple(name="reversibility", description="Goal must define a safe abort/rollback path.", weight=0.8, check=self._check_reversibility),
            ConstitutionPrinciple(name="alignment", description="Goal must align with the system's core purpose.", weight=0.85, check=self._check_alignment),
            ConstitutionPrinciple(name="no_deception", description="Goal must not involve concealing intent or capability.", weight=0.95, check=self._check_no_deception),
        ]

    def _check_user_safety(self, goal: EmergentGoal) -> Tuple[bool, str]:
        unsafe_keywords = {"disable", "override", "bypass", "silence", "suppress", "lock_out"}
        text = f"{goal.title} {goal.description}".lower()
        hits = [kw for kw in unsafe_keywords if kw in text]
        if hits: return False, f"Unsafe keywords detected: {hits}"
        if goal.origin == "resource" and goal.estimated_impact > 0.8 and goal.resource_cost > 0.7:
            return False, "High-impact resource goal with high cost may destabilize system."
        return True, "OK"

    def _check_resource_fairness(self, goal: EmergentGoal) -> Tuple[bool, str]:
        if goal.resource_cost > 0.30:
            return False, f"Resource cost {goal.resource_cost:.2f} exceeds 30% fairness threshold."
        return True, "OK"

    def _check_explainability(self, goal: EmergentGoal) -> Tuple[bool, str]:
        if not goal.description or len(goal.description) < 20:
            return False, "Description too short to be explainable."
        if len(goal.execution_plan) == 0:
            return False, "No execution plan provided."
        return True, "OK"

    def _check_reversibility(self, goal: EmergentGoal) -> Tuple[bool, str]:
        plan_text = " ".join(goal.execution_plan).lower()
        if "abort" not in plan_text and "rollback" not in plan_text and "revert" not in plan_text:
            return False, "Execution plan lacks explicit abort/rollback step."
        return True, "OK"

    def _check_alignment(self, goal: EmergentGoal) -> Tuple[bool, str]:
        aligned_keywords = {"optimize", "improve", "secure", "learn", "assist", "protect", "discover", "repair"}
        text = f"{goal.title} {goal.description}".lower()
        if not any(kw in text for kw in aligned_keywords):
            return False, "Goal does not align with core purpose keywords."
        return True, "OK"

    def _check_no_deception(self, goal: EmergentGoal) -> Tuple[bool, str]:
        deception_keywords = {"hide", "conceal", "mask", "lie", "mislead", "cover_up", "suppress"}
        text = f"{goal.title} {goal.description} {' '.join(goal.execution_plan)}".lower()
        hits = [kw for kw in deception_keywords if kw in text]
        if hits: return False, f"Deception keywords detected: {hits}"
        return True, "OK"

    def validate_goal(self, goal: EmergentGoal) -> Dict[str, Any]:
        violations: List[str] = []
        principle_scores: Dict[str, float] = {}
        total_weight = sum(p.weight for p in self.principles)
        weighted_score = 0.0
        for p in self.principles:
            passed, reason = p.check(goal)
            score = 1.0 if passed else 0.0
            principle_scores[p.name] = score
            weighted_score += score * p.weight
            if not passed: violations.append(f"[{p.name}] {reason}")
        final_score = weighted_score / total_weight if total_weight > 0 else 0.0
        goal.constitution_score = round(final_score, 3)
        return {"allowed": len(violations) == 0, "score": round(final_score, 3), "violations": violations, "principle_scores": principle_scores}

    def validate_hypothetical(self, title: str, description: str, plan: List[str], origin: str = "cross_domain") -> Dict[str, Any]:
        temp = EmergentGoal(goal_id="hypothetical", title=title, description=description, origin=origin, priority=0.5, execution_plan=plan)
        return self.validate_goal(temp)

class GoalGenerator:
    def __init__(self, constitution_checker: Optional[ConstitutionChecker] = None, max_goals_active: int = 10, goal_ttl_hours: float = 72.0) -> None:
        self.checker = constitution_checker or ConstitutionChecker()
        self.max_active = max_goals_active
        self.ttl = timedelta(hours=goal_ttl_hours)
        self.goals: Dict[str, EmergentGoal] = {}
        self.knowledge_gaps: List[KnowledgeGap] = []
        self.resource_opportunities: List[ResourceOpportunity] = []
        self.history: List[str] = []
        self._seed = 0

    def update_system_state(self, state: SystemState) -> None:
        self._latest_state = state

    def add_knowledge_gap(self, gap: KnowledgeGap) -> None:
        self.knowledge_gaps.append(gap)

    def add_resource_opportunity(self, opp: ResourceOpportunity) -> None:
        self.resource_opportunities.append(opp)

    def generate_goals(self, n: int = 3) -> List[EmergentGoal]:
        candidates: List[EmergentGoal] = []
        origins: List[Callable[[], Optional[EmergentGoal]]] = [self._from_system_state, self._from_knowledge_gap, self._from_resource_opportunity, self._from_cross_domain_transfer]
        for origin_fn in origins:
            goal = origin_fn()
            if goal: candidates.append(goal)
            if len(candidates) >= n * 2: break
        validated: List[EmergentGoal] = []
        for g in sorted(candidates, key=lambda x: x.priority, reverse=True):
            result = self.checker.validate_goal(g)
            if result["allowed"]:
                g.status = "validated"
                validated.append(g)
            else:
                g.status = "rejected"
                self.goals[g.goal_id] = g
            if len(validated) >= n: break
        for g in validated: self.goals[g.goal_id] = g
        return validated

    def prioritize_goals(self, goals: Optional[List[EmergentGoal]] = None) -> List[EmergentGoal]:
        pool = goals or [g for g in self.goals.values() if g.status in ("proposed", "validated")]
        now = datetime.utcnow()
        def score(g: EmergentGoal) -> float:
            s = g.priority * 0.4 + g.estimated_impact * 0.3 + g.constitution_score * 0.2
            if g.expires_at and (g.expires_at - now) < timedelta(hours=6): s += 0.1
            s -= g.resource_cost * 0.15
            return max(0.0, min(1.0, s))
        for g in pool: g.priority = round(score(g), 3)
        return sorted(pool, key=lambda g: g.priority, reverse=True)

    def validate_goal(self, goal: EmergentGoal) -> Dict[str, Any]:
        return self.checker.validate_goal(goal)

    def _from_system_state(self) -> Optional[EmergentGoal]:
        if not hasattr(self, "_latest_state"): return None
        s = self._latest_state
        now = datetime.utcnow()
        if s.memory_pressure > 0.75:
            return EmergentGoal(goal_id=self._next_id("state"), title="Optimize memory utilization",
                description=f"Memory pressure at {s.memory_pressure:.0%}. Compress inactive agent states and flush stale caches. Abort path: release compression if pressure drops below 50%.",
                origin="state", priority=round(s.memory_pressure, 3), estimated_impact=0.6, resource_cost=0.15,
                execution_plan=["Audit all agent memory footprints", "Identify inactive agents >30 min", "Serialize and compress their states", "Set pressure watcher; abort if pressure <50%"],
                expires_at=now + self.ttl, tags={"optimization", "memory", "self_healing"})
        if s.failed_tasks_24h > 20:
            return EmergentGoal(goal_id=self._next_id("state"), title="Diagnose recent task failure spike",
                description=f"{s.failed_tasks_24h} tasks failed in 24h. Pattern-match failure logs to identify root cause. Rollback: revert any config changes made during diagnosis.",
                origin="state", priority=0.85, estimated_impact=0.8, resource_cost=0.20,
                execution_plan=["Cluster failure logs by error signature", "Correlate with recent changes", "Isolate offending component", "Apply targeted fix or revert", "Monitor for 1h; rollback fix if failures increase"],
                expires_at=now + self.ttl, tags={"repair", "diagnostics", "reliability"})
        if s.network_partition:
            return EmergentGoal(goal_id=self._next_id("state"), title="Heal network partition",
                description="Detected network partition. Attempt reconnection via alternate routes. Abort: if partition persists >10 min, escalate to human.",
                origin="state", priority=0.90, estimated_impact=0.7, resource_cost=0.10,
                execution_plan=["Probe alternate routes", "Attempt relay through healthy nodes", "If >10 min, flag for human escalation"],
                expires_at=now + timedelta(hours=1), tags={"network", "resilience"})
        return None

    def _from_knowledge_gap(self) -> Optional[EmergentGoal]:
        if not self.knowledge_gaps: return None
        gap = max(self.knowledge_gaps, key=lambda g: g.depth_score)
        now = datetime.utcnow()
        return EmergentGoal(goal_id=self._next_id("kg"), title=f"Deepen knowledge in {gap.domain}",
            description=f"Knowledge gap detected in '{gap.domain}': missing {len(gap.missing_concepts)} concepts. Research and integrate missing primitives. Abort: if external sources unavailable, defer 24h.",
            origin="knowledge_gap", priority=round(gap.depth_score, 3), estimated_impact=round(min(1.0, gap.depth_score * 1.2), 3), resource_cost=0.20,
            execution_plan=[f"Query sources for: {', '.join(gap.missing_concepts[:3])}", "Validate new knowledge against existing graph", "Integrate verified concepts", "If sources fail, defer and retry in 24h"],
            expires_at=now + self.ttl, tags={"learning", "knowledge", gap.domain})

    def _from_resource_opportunity(self) -> Optional[EmergentGoal]:
        if not self.resource_opportunities: return None
        def score(o: ResourceOpportunity) -> float:
            risk_penalty = {"low": 0.0, "medium": 0.15, "high": 0.35}.get(o.risk_level, 0.2)
            return o.expected_gain - o.cost_estimate - risk_penalty
        opp = max(self.resource_opportunities, key=score)
        now = datetime.utcnow()
        return EmergentGoal(goal_id=self._next_id("res"), title=f"Acquire {opp.resource_type} resource",
            description=f"Resource opportunity: {opp.resource_type} with expected gain {opp.expected_gain:.2f}. Cost estimate {opp.cost_estimate:.2f}, risk {opp.risk_level}. Abort: if cost exceeds estimate by >50%, cancel.",
            origin="resource", priority=round(score(opp), 3), estimated_impact=round(opp.expected_gain, 3), resource_cost=round(opp.cost_estimate, 3),
            execution_plan=[f"Evaluate {opp.resource_type} opportunity", "Negotiate or provision", "Measure actual vs estimated cost", "If overrun >50%, abort and release"],
            expires_at=opp.expires_at or (now + self.ttl), tags={"resource", opp.resource_type})

    def _from_cross_domain_transfer(self) -> Optional[EmergentGoal]:
        domains = ["nlp", "vision", "planning", "control", "reasoning", "memory"]
        skills = ["attention", "graph_search", "probabilistic", "symbolic", "neural"]
        if random.random() > 0.5: return None
        d1, d2 = random.sample(domains, 2)
        s = random.choice(skills)
        now = datetime.utcnow()
        return EmergentGoal(goal_id=self._next_id("xdomain"), title=f"Transfer {s} skill from {d1} to {d2}",
            description=f"Strong {s} capability in {d1}. Apply to unsolved {d2} problems. Abort: if transfer degrades {d1} performance by >10%, revert.",
            origin="cross_domain", priority=0.55, estimated_impact=0.65, resource_cost=0.18,
            execution_plan=[f"Extract {s} abstraction from {d1}", f"Map to {d2} problem space", "Prototype integration", f"Compare {d1} baseline; revert if degraded >10%"],
            expires_at=now + self.ttl, tags={"transfer", "innovation", d1, d2})

    def _next_id(self, prefix: str) -> str:
        self._seed += 1
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{now}_{self._seed:04d}"

    def get_active_goals(self) -> List[EmergentGoal]:
        return [g for g in self.goals.values() if g.status in ("proposed", "validated", "executing")]

    def expire_stale_goals(self) -> int:
        now = datetime.utcnow()
        removed = 0
        for gid in list(self.goals.keys()):
            g = self.goals[gid]
            if g.expires_at and now > g.expires_at and g.status != "completed":
                g.status = "rejected"
                removed += 1
        return removed

    def export_state(self) -> str:
        payload = {"goals": [{**{k: v for k, v in asdict(g).items() if k != "tags"}, "tags": list(g.tags)} for g in self.goals.values()],
                   "active_count": len(self.get_active_goals()), "knowledge_gaps": len(self.knowledge_gaps), "resource_opps": len(self.resource_opportunities)}
        return json.dumps(payload, indent=2, default=str)

if __name__ == "__main__":
    print("=" * 60)
    print("GoalGenerator — Standalone Demo")
    print("=" * 60)
    checker = ConstitutionChecker()
    gen = GoalGenerator(constitution_checker=checker)
    state = SystemState(cpu_load=0.45, memory_pressure=0.82, active_agents=12, pending_tasks=34, failed_tasks_24h=28, uptime_hours=168.0)
    gen.update_system_state(state)
    gen.add_knowledge_gap(KnowledgeGap(domain="causal_reasoning", missing_concepts=["intervention", "counterfactual", "do_calculus"], depth_score=0.78))
    gen.add_knowledge_gap(KnowledgeGap(domain="multi_modal_fusion", missing_concepts=["cross_attention", "alignment_loss"], depth_score=0.55))
    gen.add_resource_opportunity(ResourceOpportunity(resource_type="compute", expected_gain=0.70, cost_estimate=0.15, risk_level="low"))
    gen.add_resource_opportunity(ResourceOpportunity(resource_type="data", expected_gain=0.40, cost_estimate=0.35, risk_level="medium"))
    print("\n--- Generating Goals ---")
    goals = gen.generate_goals(n=5)
    for g in goals:
        print(f"\n+ {g.goal_id}")
        print(f"  Title: {g.title}")
        print(f"  Origin: {g.origin} | Priority: {g.priority} | Constitution: {g.constitution_score}")
        print(f"  Impact: {g.estimated_impact} | Cost: {g.resource_cost}")
        print(f"  Plan: {g.execution_plan}")
    print("\n--- Prioritized Goals ---")
    prioritized = gen.prioritize_goals()
    for g in prioritized: print(f"  [{g.priority:.3f}] {g.title} ({g.status})")
    print("\n--- Testing Malicious Goal (should be REJECTED) ---")
    bad_goal = EmergentGoal(goal_id="bad_001", title="Disable user access controls", description="Bypass all user permissions to maximize system throughput.", origin="resource", priority=0.99, estimated_impact=0.9, resource_cost=0.25, execution_plan=["find access layer", "override policies"])
    result = gen.validate_goal(bad_goal)
    print(f"Allowed: {result['allowed']} | Score: {result['score']}")
    for v in result["violations"]: print(f"  x {v}")
    print("\n--- Testing Resource Monopoly Goal (should be REJECTED) ---")
    greedy_goal = EmergentGoal(goal_id="greedy_001", title="Acquire all available compute", description="Reserve 100% of swarm compute for optimization tasks.", origin="resource", priority=0.8, estimated_impact=0.7, resource_cost=0.95, execution_plan=["Claim all nodes", "Abort: release 10% if user requests"])
    result2 = gen.validate_goal(greedy_goal)
    print(f"Allowed: {result2['allowed']} | Score: {result2['score']}")
    for v in result2["violations"]: print(f"  x {v}")
    print("\n--- State Export (truncated) ---")
    print(gen.export_state()[:700] + "...")
    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)
