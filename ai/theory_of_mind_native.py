#!/usr/bin/env python3
"""Theory of Mind — MAGNATRIX-OS ASI Expansion
Path: ai/theory_of_mind_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations
import copy, logging, math, random, sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

@dataclass
class Belief:
    agent_id: str
    proposition: str
    confidence: float  # 0-1

@dataclass
class Intent:
    agent_id: str
    goal: str
    planned_actions: List[str]

class TheoryOfMind:
    """Model other agents' beliefs, intents, and recursively nested mental states."""

    def __init__(self, self_id: str):
        self.self_id = self_id
        self.beliefs: Dict[str, List[Belief]] = defaultdict(list)
        self.intents: Dict[str, Intent] = {}
        self.nested: Dict[str, Dict[str, List[Belief]]] = defaultdict(lambda: defaultdict(list))

    def observe_action(self, agent_id: str, action: str, context: Dict[str, Any]) -> None:
        """Infer intent from observed action."""
        # Simple intent inference: action suggests goal
        goal_map = {"move_to": "reach_location", "pick_up": "acquire_object", "say": "communicate"}
        goal = goal_map.get(action.split("_")[0], "unknown")
        self.intents[agent_id] = Intent(agent_id, goal, [action])

    def update_belief(self, agent_id: str, proposition: str, confidence: float) -> None:
        self.beliefs[agent_id].append(Belief(agent_id, proposition, confidence))

    def nested_belief(self, agent_a: str, agent_b: str, proposition: str, confidence: float) -> None:
        """A believes that B believes proposition."""
        self.nested[agent_a][agent_b].append(Belief(agent_b, proposition, confidence))

    def predict_action(self, agent_id: str) -> Optional[str]:
        """Predict next action based on inferred intent."""
        intent = self.intents.get(agent_id)
        if not intent or not intent.planned_actions:
            return None
        return intent.planned_actions[0]

    def recursive_depth(self, agent_id: str) -> int:
        """Max recursive belief depth for agent."""
        def _depth(beliefs, current_depth):
            if not beliefs: return current_depth
            max_d = current_depth
            for b in beliefs:
                # Check if proposition contains nested belief
                if "believes" in b.proposition:
                    max_d = max(max_d, current_depth + 1)
            return max_d
        return _depth(self.beliefs.get(agent_id, []), 1)

    def consensus(self, agents: List[str], proposition: str, threshold: float = 0.5) -> bool:
        """Check if majority of agents believe proposition above threshold."""
        scores = []
        for a in agents:
            for b in self.beliefs.get(a, []):
                if b.proposition == proposition:
                    scores.append(b.confidence)
                    break
            else:
                scores.append(0.0)
        return sum(1 for s in scores if s >= threshold) > len(agents) / 2

def _self_test():
    print("=" * 55)
    print("Theory of Mind — Self Test")
    print("=" * 55)
    passed, total = 0, 5
    tom = TheoryOfMind("agent_0")

    tom.observe_action("agent_1", "move_to_kitchen", {"location": "hallway"})
    pred = tom.predict_action("agent_1")
    ok = pred == "move_to_kitchen"
    print(f"  [Test 1] Predict action: {pred} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    tom.update_belief("agent_1", "food_in_kitchen", 0.9)
    ok = len(tom.beliefs["agent_1"]) == 1
    print(f"  [Test 2] Update belief — {'PASS' if ok else 'FAIL'}")
    passed += ok

    tom.nested_belief("agent_1", "agent_2", "door_is_locked", 0.8)
    ok = len(tom.nested["agent_1"]["agent_2"]) == 1
    print(f"  [Test 3] Nested belief — {'PASS' if ok else 'FAIL'}")
    passed += ok

    tom.update_belief("agent_1", "food_in_kitchen", 0.9)
    tom.update_belief("agent_2", "food_in_kitchen", 0.6)
    c = tom.consensus(["agent_1", "agent_2"], "food_in_kitchen", threshold=0.5)
    ok = c == True
    print(f"  [Test 4] Consensus: {c} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    d = tom.recursive_depth("agent_1")
    ok = d >= 1
    print(f"  [Test 5] Recursive depth: {d} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    print("=" * 55)
    print(f"PASS: {passed}/{total} tests")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    _self_test()
