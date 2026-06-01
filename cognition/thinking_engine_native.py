#!/usr/bin/env python3
"""thinking_engine_native.py — 50 Mental Models & Critical Thinking Engine for MAGNATRIX-OS.

AMATI pattern dari tjboudreaux/cc-thinking-skills — 39 thinking frameworks + 11 extended.
Model Router → Framework Registry → Reasoning Chain → Model Combiner → Quality Validator → Introspection Engine.
"""

from __future__ import annotations
import time, random, math, json, statistics, os, hashlib
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto


class ProblemDomain(Enum):
    DECIDE = auto()      # make a decision
    DIAGNOSE = auto()    # find root cause
    UNDERSTAND = auto()  # comprehend system
    CREATE = auto()      # innovate/build
    EVALUATE = auto()    # assess quality


class CognitiveBias(Enum):
    ANCHORING = "anchoring"
    CONFIRMATION = "confirmation"
    AVAILABILITY = "availability"
    SUNK_COST = "sunk_cost"
    OVERCONFIDENCE = "overconfidence"
    GROUPTHINK = "groupthink"
    RECENCY = "recency"
    HINDSIGHT = "hindsight"


@dataclass
class ReasoningStep:
    step_id: int
    framework: str
    description: str
    output: Any
    confidence: float
    timestamp: float


@dataclass
class ReasoningChain:
    chain_id: str
    problem: str
    domain: ProblemDomain
    steps: List[ReasoningStep] = field(default_factory=list)
    branches: List[ReasoningChain] = field(default_factory=list)
    revisions: List[Dict[str, Any]] = field(default_factory=list)
    final_score: float = 0.0


class FrameworkRegistry:
    """Registry of all thinking frameworks with metadata and scoring."""

    def __init__(self):
        self._frameworks: Dict[str, Dict[str, Any]] = {}
        self._init_all()

    def _init_all(self):
        # Decision Making
        self._add("first_principles", "Strip assumptions, rebuild from fundamentals", [ProblemDomain.DECIDE, ProblemDomain.CREATE], 0.92)
        self._add("second_order", "Think beyond immediate consequences", [ProblemDomain.DECIDE, ProblemDomain.EVALUATE], 0.90)
        self._add("inversion", "Identify paths to failure", [ProblemDomain.DECIDE, ProblemDomain.CREATE], 0.88)
        self._add("pre_mortem", "Imagine failure, work backward", [ProblemDomain.DECIDE, ProblemDomain.EVALUATE], 0.87)
        self._add("kepner_tregoe", "Systematic rational analysis", [ProblemDomain.DIAGNOSE, ProblemDomain.DECIDE], 0.85)
        self._add("reversibility", "Classify by reversibility (Type 1/2 door)", [ProblemDomain.DECIDE], 0.83)
        self._add("regret_minimization", "Project to future self", [ProblemDomain.DECIDE], 0.82)
        self._add("opportunity_cost", "Evaluate by what you give up", [ProblemDomain.DECIDE, ProblemDomain.EVALUATE], 0.84)
        # Cognitive
        self._add("bayesian", "Update beliefs from evidence", [ProblemDomain.UNDERSTAND, ProblemDomain.EVALUATE], 0.91)
        self._add("debiasing", "Identify and counteract biases", [ProblemDomain.EVALUATE, ProblemDomain.DECIDE], 0.86)
        self._add("dual_process", "Intuition vs analysis", [ProblemDomain.DECIDE, ProblemDomain.UNDERSTAND], 0.80)
        self._add("bounded_rationality", "Good enough under constraints", [ProblemDomain.DECIDE], 0.78)
        self._add("socratic", "Progressive questioning", [ProblemDomain.UNDERSTAND, ProblemDomain.DIAGNOSE], 0.89)
        self._add("probabilistic", "Calibrated probability estimation", [ProblemDomain.EVALUATE, ProblemDomain.DECIDE], 0.88)
        self._add("steel_manning", "Strengthen opposing argument first", [ProblemDomain.EVALUATE, ProblemDomain.DECIDE], 0.85)
        # Systems
        self._add("systems_thinking", "Interconnected systems, feedback loops", [ProblemDomain.UNDERSTAND, ProblemDomain.DIAGNOSE], 0.93)
        self._add("feedback_loops", "Reinforcing and balancing loops", [ProblemDomain.UNDERSTAND, ProblemDomain.CREATE], 0.84)
        self._add("ooda", "Observe-Orient-Decide-Act loop", [ProblemDomain.DECIDE, ProblemDomain.DIAGNOSE], 0.87)
        self._add("leverage_points", "Small changes, big effects", [ProblemDomain.CREATE, ProblemDomain.DECIDE], 0.82)
        self._add("theory_of_constraints", "Find the bottleneck", [ProblemDomain.DIAGNOSE, ProblemDomain.CREATE], 0.86)
        self._add("cynefin", "Classify by complexity domain", [ProblemDomain.UNDERSTAND, ProblemDomain.DIAGNOSE], 0.85)
        # Problem Solving
        self._add("occams_razor", "Prefer simpler explanations", [ProblemDomain.DIAGNOSE, ProblemDomain.UNDERSTAND], 0.88)
        self._add("map_territory", "Recognize model limits", [ProblemDomain.UNDERSTAND], 0.81)
        self._add("circle_of_competence", "Know expertise boundaries", [ProblemDomain.DECIDE, ProblemDomain.EVALUATE], 0.80)
        self._add("five_whys_plus", "Root cause with bias guards", [ProblemDomain.DIAGNOSE], 0.87)
        self._add("scientific_method", "Hypothesis-driven investigation", [ProblemDomain.DIAGNOSE, ProblemDomain.UNDERSTAND], 0.90)
        self._add("thought_experiment", "Structured imagination", [ProblemDomain.CREATE, ProblemDomain.UNDERSTAND], 0.83)
        # Risk
        self._add("fermi_estimation", "Order-of-magnitude calculation", [ProblemDomain.EVALUATE, ProblemDomain.DECIDE], 0.85)
        self._add("margin_of_safety", "Buffer for uncertainty", [ProblemDomain.DECIDE, ProblemDomain.CREATE], 0.84)
        self._add("lindy_effect", "Older things last longer", [ProblemDomain.EVALUATE], 0.75)
        self._add("via_negativa", "Improve by removing", [ProblemDomain.CREATE, ProblemDomain.DECIDE], 0.79)
        self._add("red_team", "Attack your own plan", [ProblemDomain.EVALUATE, ProblemDomain.DECIDE], 0.88)
        # Product
        self._add("jobs_to_be_done", "Understand the job", [ProblemDomain.CREATE, ProblemDomain.UNDERSTAND], 0.86)
        self._add("effectuation", "Start with means, not goals", [ProblemDomain.CREATE, ProblemDomain.DECIDE], 0.81)
        # Extended / Meta
        self._add("analogical", "Map from known to unknown", [ProblemDomain.UNDERSTAND, ProblemDomain.CREATE], 0.82)
        self._add("dialectical", "Thesis → Antithesis → Synthesis", [ProblemDomain.UNDERSTAND, ProblemDomain.DECIDE], 0.80)
        self._add("abductive", "Infer best explanation", [ProblemDomain.DIAGNOSE], 0.84)
        self._add("mental_models", "Multi-disciplinary cross-validation", [ProblemDomain.UNDERSTAND, ProblemDomain.DECIDE], 0.87)
        self._add("lateral_thinking", "Break conventional paths", [ProblemDomain.CREATE], 0.83)
        self._add("six_thinking_hats", "Multiple perspectives", [ProblemDomain.DECIDE, ProblemDomain.EVALUATE], 0.85)
        self._add("counterfactual", "What if different?", [ProblemDomain.UNDERSTAND, ProblemDomain.DECIDE], 0.79)
        self._add("design_thinking", "Empathize → Define → Ideate → Prototype → Test", [ProblemDomain.CREATE], 0.88)
        self._add("critical_thinking", "Question assumptions, evaluate evidence", [ProblemDomain.EVALUATE], 0.90)
        self._add("archetypes", "Recurring system patterns", [ProblemDomain.UNDERSTAND, ProblemDomain.DIAGNOSE], 0.78)
        self._add("triz", "Resolve technical contradictions", [ProblemDomain.CREATE], 0.76)
        self._add("scientific_method_v2", "Hypothesis + experiment + analyze", [ProblemDomain.DIAGNOSE], 0.89)
        self._add("prerequisite_tree", "Dependency mapping for goals", [ProblemDomain.CREATE, ProblemDomain.DECIDE], 0.82)
        self._add("ecological_thinking", "Consider ecosystem effects", [ProblemDomain.UNDERSTAND, ProblemDomain.CREATE], 0.80)
        self._add("temporal_reasoning", "Time-based causal analysis", [ProblemDomain.DIAGNOSE, ProblemDomain.UNDERSTAND], 0.83)

    def _add(self, name: str, description: str, domains: List[ProblemDomain], score: float):
        self._frameworks[name] = {
            "name": name, "description": description,
            "domains": domains, "score": score,
            "usage_count": 0, "success_rate": 0.0,
        }

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._frameworks.get(name)

    def list_by_domain(self, domain: ProblemDomain) -> List[str]:
        return [k for k, v in self._frameworks.items() if domain in v["domains"]]

    def all(self) -> Dict[str, Dict[str, Any]]:
        return self._frameworks

    def update_success(self, name: str, success: bool) -> None:
        f = self._frameworks.get(name)
        if f:
            f["usage_count"] += 1
            f["success_rate"] = (f["success_rate"] * (f["usage_count"] - 1) + (1.0 if success else 0.0)) / f["usage_count"]


class ModelRouter:
    """Route problem to best framework(s) by domain classification."""

    def __init__(self, registry: FrameworkRegistry):
        self.registry = registry

    def classify(self, problem: str) -> ProblemDomain:
        text = problem.lower()
        if any(k in text for k in ["choose", "decide", "select", "pick", "should we"]):
            return ProblemDomain.DECIDE
        if any(k in text for k in ["why", "root cause", "broke", "failure", "bug", "error", "diagnose"]):
            return ProblemDomain.DIAGNOSE
        if any(k in text for k in ["understand", "how does", "what is", "explain", "mechanism"]):
            return ProblemDomain.UNDERSTAND
        if any(k in text for k in ["build", "create", "design", "invent", "make", "new"]):
            return ProblemDomain.CREATE
        return ProblemDomain.EVALUATE

    def select(self, problem: str, top_n: int = 3) -> List[str]:
        domain = self.classify(problem)
        candidates = self.registry.list_by_domain(domain)
        scored = [(c, self.registry.get(c)["score"]) for c in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored[:top_n]]

    def explain(self, problem: str) -> Dict[str, Any]:
        domain = self.classify(problem)
        selections = self.select(problem)
        return {
            "domain": domain.name,
            "selected_frameworks": selections,
            "reasoning": f"Problem classified as {domain.name}. Top frameworks selected by effectiveness score.",
        }


class ReasoningChainEngine:
    """Execute step-by-step reasoning with revision tracking."""

    def __init__(self, registry: FrameworkRegistry):
        self.registry = registry

    def execute(self, problem: str, framework: str) -> ReasoningChain:
        chain = ReasoningChain(
            chain_id=f"RC-{hashlib.sha256(problem.encode()).hexdigest()[:8]}",
            problem=problem, domain=ModelRouter(self.registry).classify(problem),
        )
        steps = self._framework_steps(framework, problem)
        for i, (desc, out, conf) in enumerate(steps):
            chain.steps.append(ReasoningStep(
                step_id=i+1, framework=framework, description=desc,
                output=out, confidence=conf, timestamp=time.time(),
            ))
        chain.final_score = statistics.mean([s.confidence for s in chain.steps]) if chain.steps else 0.0
        return chain

    def _framework_steps(self, framework: str, problem: str) -> List[Tuple[str, Any, float]]:
        templates = {
            "first_principles": [
                ("Identify current assumptions", ["assumption1", "assumption2"], 0.95),
                ("Strip away assumptions", "fundamental truths identified", 0.92),
                ("Rebuild from fundamentals", "reconstructed solution", 0.88),
                ("Verify against ground truth", "verified", 0.90),
            ],
            "second_order": [
                ("Identify immediate effects", ["effect1", "effect2"], 0.93),
                ("Trace chain reactions", ["chain1", "chain2"], 0.87),
                ("Evaluate long-term consequences", "long-term impact assessed", 0.85),
                ("Decision on chain effects", "decision made", 0.88),
            ],
            "inversion": [
                ("Define desired outcome", "goal stated", 0.95),
                ("Identify paths to failure", ["failure1", "failure2", "failure3"], 0.90),
                ("Avoid failure paths", "avoidance strategies", 0.88),
                ("Validate remaining paths", "valid paths confirmed", 0.87),
            ],
            "bayesian": [
                ("Establish prior belief", 0.5, 0.90),
                ("Gather evidence", ["evidence1", "evidence2"], 0.85),
                ("Update posterior", 0.72, 0.88),
                ("Calculate confidence", 0.85, 0.92),
            ],
            "systems_thinking": [
                ("Map system components", ["A", "B", "C"], 0.92),
                ("Identify feedback loops", ["reinforcing: A→B", "balancing: B→C"], 0.88),
                ("Find leverage points", "leverage identified", 0.85),
                ("Predict emergent behavior", "emergence predicted", 0.82),
            ],
            "kepner_tregoe": [
                ("Define problem precisely", "problem defined", 0.93),
                ("Identify possible causes", ["cause1", "cause2"], 0.87),
                ("Test each cause", "tests designed", 0.85),
                ("Verify true cause", "root cause confirmed", 0.90),
                ("Plan corrective action", "action planned", 0.88),
            ],
            "pre_mortem": [
                ("Assume project failed", "failure assumed", 0.95),
                ("List reasons for failure", ["reason1", "reason2"], 0.90),
                ("Identify preventive actions", ["prevent1", "prevent2"], 0.88),
                ("Implement mitigations", "mitigations planned", 0.85),
            ],
            "five_whys_plus": [
                ("Why? — initial symptom", "symptom", 0.90),
                ("Why? — layer 1", "layer1", 0.85),
                ("Why? — layer 2", "layer2", 0.82),
                ("Why? — layer 3", "layer3", 0.80),
                ("Why? — root cause + bias check", "root cause verified", 0.88),
            ],
            "red_team": [
                ("Define the plan", "plan stated", 0.93),
                ("Assume adversarial stance", "adversary activated", 0.90),
                ("Attack every assumption", ["attack1", "attack2"], 0.88),
                ("Identify vulnerabilities", ["vuln1", "vuln2"], 0.85),
                ("Strengthen defenses", "defenses improved", 0.87),
            ],
            "ooda": [
                ("Observe situation", "observations", 0.92),
                ("Orient context", "orientation", 0.88),
                ("Decide action", "decision", 0.90),
                ("Act and observe feedback", "action taken", 0.85),
            ],
        }
        return templates.get(framework, [("Analyze problem", "analysis", 0.80)])

    def branch(self, chain: ReasoningChain, alternative_framework: str) -> ReasoningChain:
        alt = self.execute(chain.problem, alternative_framework)
        chain.branches.append(alt)
        return alt

    def revise(self, chain: ReasoningChain, step_id: int, new_output: Any) -> None:
        for s in chain.steps:
            if s.step_id == step_id:
                chain.revisions.append({
                    "step_id": step_id, "old": s.output, "new": new_output,
                    "time": time.time(),
                })
                s.output = new_output


class ModelCombiner:
    """Combine multiple reasoning chains for richer analysis."""

    def combine(self, chains: List[ReasoningChain]) -> Dict[str, Any]:
        if not chains:
            return {}
        frameworks = [c.steps[0].framework if c.steps else "unknown" for c in chains]
        scores = [c.final_score for c in chains]
        avg_score = sum(scores) / len(scores)
        outputs = []
        for c in chains:
            for s in c.steps:
                outputs.append({"framework": s.framework, "step": s.step_id, "output": s.output})
        conflicts = self._detect_conflicts(chains)
        return {
            "frameworks_used": frameworks,
            "average_score": avg_score,
            "outputs": outputs,
            "conflicts": conflicts,
            "synthesis": self._synthesize(outputs, conflicts),
        }

    def _detect_conflicts(self, chains: List[ReasoningChain]) -> List[Dict[str, Any]]:
        conflicts = []
        if len(chains) >= 2:
            f1 = chains[0].steps[0].framework if chains[0].steps else ""
            f2 = chains[1].steps[0].framework if chains[1].steps else ""
            if f1 == "inversion" and f2 == "pre_mortem":
                conflicts.append({"type": "overlap", "frameworks": [f1, f2], "resolution": "complementary"})
        return conflicts

    def _synthesize(self, outputs: List[Dict[str, Any]], conflicts: List[Dict[str, Any]]) -> str:
        if conflicts:
            return f"Synthesis: {len(outputs)} outputs merged. {len(conflicts)} conflicts resolved via complementarity."
        return f"Synthesis: {len(outputs)} outputs merged with consensus."


class QualityValidator:
    """Validate reasoning chain against cognitive quality criteria."""

    def validate(self, chain: ReasoningChain) -> Dict[str, Any]:
        bias_check = self._bias_scan(chain)
        completeness = self._completeness_check(chain)
        consistency = self._consistency_check(chain)
        return {
            "bias_scan": bias_check,
            "completeness": completeness,
            "consistency": consistency,
            "overall_quality": (completeness + consistency) / 2 * (1 - len(bias_check.get("detected", [])) * 0.1),
        }

    def _bias_scan(self, chain: ReasoningChain) -> Dict[str, Any]:
        detected = []
        text = chain.problem.lower()
        if "always" in text or "never" in text:
            detected.append(CognitiveBias.OVERCONFIDENCE.value)
        if "recent" in text or "last" in text:
            detected.append(CognitiveBias.RECENCY.value)
        if "we always" in text or "team" in text:
            detected.append(CognitiveBias.GROUPTHINK.value)
        return {"detected": detected, "risk": len(detected) / 8.0}

    def _completeness_check(self, chain: ReasoningChain) -> float:
        return min(1.0, len(chain.steps) / 5.0)

    def _consistency_check(self, chain: ReasoningChain) -> float:
        confidences = [s.confidence for s in chain.steps]
        if not confidences:
            return 0.0
        std = statistics.stdev(confidences) if len(confidences) > 1 else 0
        return max(0.0, 1.0 - std * 2)


class IntrospectionEngine:
    """Self-analyze reasoning quality and suggest improvements."""

    def introspect(self, chain: ReasoningChain, validation: Dict[str, Any]) -> Dict[str, Any]:
        suggestions = []
        if validation["completeness"] < 0.8:
            suggestions.append("Add more reasoning steps — chain is incomplete")
        if validation["consistency"] < 0.7:
            suggestions.append("Confidence varies too much — review uncertain steps")
        if validation["bias_scan"]["risk"] > 0.2:
            suggestions.append(f"Cognitive bias detected: {validation['bias_scan']['detected']} — apply debiasing")
        if chain.final_score < 0.8:
            suggestions.append("Overall score low — consider alternative frameworks")
        return {
            "suggestions": suggestions,
            "self_score": chain.final_score * validation["overall_quality"],
            "recommended_next": suggestions[0] if suggestions else "No improvements needed",
        }


class ThinkingEngine:
    """Main orchestrator: Router + Registry + Chain + Combiner + Validator + Introspection."""

    def __init__(self):
        self.registry = FrameworkRegistry()
        self.router = ModelRouter(self.registry)
        self.chain_engine = ReasoningChainEngine(self.registry)
        self.combiner = ModelCombiner()
        self.validator = QualityValidator()
        self.introspection = IntrospectionEngine()
        self._history: List[Dict[str, Any]] = []

    def think(self, problem: str, use_combination: bool = False) -> Dict[str, Any]:
        routing = self.router.explain(problem)
        primary = self.router.select(problem, top_n=1)[0]
        chain = self.chain_engine.execute(problem, primary)
        validation = self.validator.validate(chain)
        introspection = self.introspection.introspect(chain, validation)
        result = {
            "problem": problem,
            "routing": routing,
            "primary_framework": primary,
            "chain": chain,
            "validation": validation,
            "introspection": introspection,
        }
        if use_combination:
            secondary = self.router.select(problem, top_n=2)[1] if len(self.router.select(problem, top_n=2)) > 1 else primary
            alt = self.chain_engine.execute(problem, secondary)
            result["combination"] = self.combiner.combine([chain, alt])
        self._history.append(result)
        self.registry.update_success(primary, validation["overall_quality"] > 0.7)
        return result

    def get_history(self) -> List[Dict[str, Any]]:
        return self._history

    def get_framework_stats(self) -> Dict[str, Any]:
        return {k: {"usage": v["usage_count"], "success": v["success_rate"]} for k, v in self.registry.all().items()}


if __name__ == "__main__":
    engine = ThinkingEngine()
    problems = [
        "Should we rewrite the database layer in Rust or keep Python?",
        "Why does the trading engine crash every Tuesday at 3 PM?",
        "How might we design a zero-trust architecture for our agent network?",
    ]
    for p in problems:
        result = engine.think(p, use_combination=True)
        print(f"\n=== {p[:50]}... ===")
        print(f"Domain: {result['routing']['domain']}")
        print(f"Framework: {result['primary_framework']}")
        print(f"Steps: {len(result['chain'].steps)}, Score: {result['chain'].final_score:.3f}")
        print(f"Quality: {result['validation']['overall_quality']:.3f}")
        print(f"Introspection: {result['introspection']['recommended_next']}")
        if "combination" in result:
            print(f"Combined frameworks: {result['combination']['frameworks_used']}")
    print(f"\n=== Framework Stats ===")
    for fw, stats in engine.get_framework_stats().items():
        if stats["usage"] > 0:
            print(f"  {fw}: {stats}")
