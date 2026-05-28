#!/usr/bin/env python3
"""Theory of Mind — MAGNATRIX-OS ASI Expansion
Path: ai/theory_of_mind_native.py
License: AGPL-3.0
Authors: MAGNATRIX-Lab
Depends: Python 3.11+ stdlib only.

Model other agents' beliefs, desires, intentions. Recursive belief modeling
(I believe that you believe that I believe...).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("theory_of_mind")


@dataclass
class Belief:
    proposition: str
    confidence: float
    source: str = "observation"

@dataclass
class Desire:
    goal: str
    urgency: float
    feasibility: float

@dataclass
class Intention:
    action: str
    target: str
    plan_steps: List[str] = field(default_factory=list)

@dataclass
class MentalState:
    agent_id: str
    beliefs: List[Belief] = field(default_factory=list)
    desires: List[Desire] = field(default_factory=list)
    intentions: List[Intention] = field(default_factory=list)
    trust_level: float = 0.5
    deception_tendency: float = 0.0


class AgentModel:
    def __init__(self, agent_id: str, observed_state: MentalState, depth: int = 1, max_depth: int = 3) -> None:
        self.agent_id = agent_id
        self.observed = observed_state
        self.depth = depth
        self.max_depth = max_depth
        self._belief_model: Dict[str, float] = {}
        self._goal_model: Dict[str, float] = {}
        self._intention_history: List[str] = []
        self._action_history: List[Tuple[str, str]] = []
        # Seed belief model from observed beliefs
        for b in observed_state.beliefs:
            self._belief_model[b.proposition] = b.confidence

    def observe_action(self, action: str, context: Dict[str, Any]) -> None:
        self._intention_history.append(action)
        self._action_history.append((action, json.dumps(context)))
        self._goal_model[action] = self._goal_model.get(action, 0.0) + 0.1
        for belief in self.observed.beliefs:
            if belief.proposition in action and belief.confidence < 0.5:
                self.observed.deception_tendency = min(1.0, self.observed.deception_tendency + 0.05)

    def observe_statement(self, proposition: str, claimed_truth: bool) -> None:
        # Check consistency with observed beliefs
        for belief in self.observed.beliefs:
            if belief.proposition.lower() in proposition.lower() or proposition.lower() in belief.proposition.lower():
                # If we believe X and claim not-X, that's inconsistent
                if belief.confidence > 0.7 and not claimed_truth:
                    self.observed.deception_tendency = min(1.0, self.observed.deception_tendency + 0.15)
                if belief.confidence < 0.3 and claimed_truth:
                    self.observed.deception_tendency = min(1.0, self.observed.deception_tendency + 0.15)
        # Check consistency with observed actions
        consistent = self._is_consistent(proposition, claimed_truth)
        if not consistent:
            self.observed.deception_tendency = min(1.0, self.observed.deception_tendency + 0.1)
        # Bayesian-ish update of belief model
        current = self._belief_model.get(proposition, 0.5)
        if claimed_truth:
            self._belief_model[proposition] = current + (1 - current) * self.observed.trust_level * 0.3
        else:
            self._belief_model[proposition] = current * (1 - self.observed.trust_level * 0.3)

    def _is_consistent(self, proposition: str, claimed_truth: bool) -> bool:
        for action, _ in self._action_history:
            if proposition.lower() in action.lower():
                return claimed_truth
        return True

    def predict_action(self, situation: Dict[str, Any]) -> str:
        ranked = sorted(self.observed.desires, key=lambda d: d.urgency * d.feasibility, reverse=True)
        if not ranked:
            return "inaction"
        return f"pursue_{ranked[0].goal}"

    def belief(self, proposition: str) -> float:
        return self._belief_model.get(proposition, 0.5)

    def intention(self) -> Optional[str]:
        if self.observed.intentions:
            return self.observed.intentions[0].action
        ranked = sorted(self.observed.desires, key=lambda d: d.urgency, reverse=True)
        if ranked:
            return f"achieve_{ranked[0].goal}"
        return None

    def detect_deception(self, threshold: float = 0.3) -> bool:
        return self.observed.deception_tendency > threshold

    def recursive_belief(self, proposition: str, depth: int = 1) -> str:
        if depth <= 0:
            return f"{self.agent_id} believes '{proposition}'"
        inner = self.recursive_belief(proposition, depth - 1)
        if depth % 2 == 1:
            return f"I believe that {self.agent_id} believes that ({inner})"
        else:
            return f"I believe that {self.agent_id} believes that I believe that ({inner})"

    def summary(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "predicted_action": self.predict_action({}),
            "top_beliefs": sorted(self._belief_model.items(), key=lambda x: -x[1])[:5],
            "top_goals": [(d.goal, d.urgency) for d in sorted(self.observed.desires, key=lambda d: -d.urgency)[:3]],
            "deception_likelihood": self.observed.deception_tendency,
            "model_depth": self.depth,
        }


class TheoryOfMindNetwork:
    def __init__(self) -> None:
        self._models: Dict[str, AgentModel] = {}
        self._my_id: str = "self"

    def register(self, agent_id: str, observed_state: MentalState) -> AgentModel:
        model = AgentModel(agent_id, observed_state)
        self._models[agent_id] = model
        return model

    def get(self, agent_id: str) -> Optional[AgentModel]:
        return self._models.get(agent_id)

    def common_knowledge(self, proposition: str) -> List[str]:
        believers = []
        for aid, model in self._models.items():
            if model.belief(proposition) > 0.7:
                believers.append(aid)
        return believers

    def deception_chain(self) -> List[Tuple[str, str]]:
        deceptive = []
        for aid, model in self._models.items():
            if model.detect_deception(threshold=0.3):
                for other_id, other_model in self._models.items():
                    if other_id != aid and other_model.observed.trust_level > 0.5:
                        deceptive.append((aid, other_id))
        return deceptive


def _self_test() -> int:
    passed = 0
    total = 0
    def check(name, condition):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name}")

    print("=" * 55)
    print("Theory of Mind — Self Test")
    print("=" * 55)

    print("\n[1] Basic belief modeling")
    state = MentalState("agent_A", beliefs=[Belief("sky_is_blue", 0.9)])
    model = AgentModel("agent_A", state)
    model.observe_statement("sky_is_blue", True)
    check("Belief tracked", model.belief("sky_is_blue") > 0.5)

    print("\n[2] Deception detection")
    state2 = MentalState("agent_B", beliefs=[Belief("door_is_locked", 0.9)], trust_level=0.8)
    model2 = AgentModel("agent_B", state2)
    for _ in range(4):
        model2.observe_action("lock_door", {})
        model2.observe_statement("door_is_locked", False)
    check("Deception detected", model2.detect_deception())

    print("\n[3] Action prediction")
    state3 = MentalState("agent_C", desires=[Desire("reach_goal", 0.9, 0.8)])
    model3 = AgentModel("agent_C", state3)
    action = model3.predict_action({})
    check("Predicted action toward goal", "pursue" in action.lower() or "achieve" in action.lower())

    print("\n[4] Intention inference")
    state4 = MentalState("agent_D", intentions=[Intention("move_north", "base")])
    model4 = AgentModel("agent_D", state4)
    intent = model4.intention()
    check("Intention extracted", intent is not None and "move" in intent.lower())

    print("\n[5] Recursive belief depth 3")
    state5 = MentalState("agent_E", beliefs=[Belief("X_exists", 0.7)])
    model5 = AgentModel("agent_E", state5, depth=3, max_depth=3)
    recursive = model5.recursive_belief("X_exists", depth=3)
    check("Depth 3 recursive belief", recursive.count("believe") >= 3)

    print("\n[6] Multi-agent network")
    net = TheoryOfMindNetwork()
    net.register("Alice", MentalState("Alice", beliefs=[Belief("secret", 0.9)]))
    net.register("Bob", MentalState("Bob", beliefs=[Belief("secret", 0.3)]))
    common = net.common_knowledge("secret")
    check("Common knowledge identifies believers", "Alice" in common and "Bob" not in common)

    print("\n[7] Deception chain")
    liar_state = MentalState("Liar", beliefs=[Belief("truth", 0.1)], deception_tendency=0.6)
    victim_state = MentalState("Victim", beliefs=[Belief("truth", 0.5)], trust_level=0.9)
    net2 = TheoryOfMindNetwork()
    net2.register("Liar", liar_state)
    net2.register("Victim", victim_state)
    chains = net2.deception_chain()
    check("Deception chain detected", any(c[0] == "Liar" for c in chains))

    print("\n[8] Belief update from multiple observations")
    state6 = MentalState("agent_F", trust_level=0.5)
    model6 = AgentModel("agent_F", state6)
    for _ in range(10):
        model6.observe_statement("rain", True)
    b = model6.belief("rain")
    check("Belief converged upward", b > 0.6)

    print("\n" + "=" * 55)
    print(f"PASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
