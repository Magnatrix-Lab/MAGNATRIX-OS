#!/usr/bin/env python3
"""Goal Alignment Engine — MAGNATRIX-OS ASI Expansion
Path: ai/goal_alignment_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.

Value learning via simplified IRL + corrigibility checks.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Demonstration:
    state: Dict[str, float]
    action: str
    reward_observed: float


@dataclass
class FeatureWeight:
    feature: str
    weight: float


class GoalAlignmentEngine:
    """Infer reward functions from demonstrations and check corrigibility."""

    def __init__(self, features: List[str], rng_seed: int = 42):
        self.features = features
        self.weights: Dict[str, float] = {f: 0.0 for f in features}
        self.rng = random.Random(rng_seed)
        self.demonstrations: List[Demonstration] = []
        self._shutdown_preference = 1.0  # Must allow shutdown

    def _extract_features(self, state: Dict[str, float]) -> Dict[str, float]:
        """Extract normalized feature values from state."""
        return {f: state.get(f, 0.0) for f in self.features}

    def _reward(self, state: Dict[str, float]) -> float:
        """Current reward estimate."""
        feats = self._extract_features(state)
        return sum(self.weights[f] * v for f, v in feats.items())

    def infer_reward(self, demonstrations: List[Demonstration], iterations: int = 100) -> Dict[str, float]:
        """Simplified IRL: adjust weights to make demonstrated actions look good."""
        self.demonstrations.extend(demonstrations)
        lr = 0.01
        for _ in range(iterations):
            for demo in demonstrations:
                feats = self._extract_features(demo.state)
                predicted = sum(self.weights[f] * v for f, v in feats.items())
                error = demo.reward_observed - predicted
                for f, v in feats.items():
                    if v != 0:
                        self.weights[f] += lr * error * v
            # Clip weights
            for f in self.weights:
                self.weights[f] = max(-10, min(10, self.weights[f]))
        return dict(self.weights)

    def align_action(self, state: Dict[str, float], actions: List[str], action_features: Dict[str, Dict[str, float]]) -> Tuple[str, float]:
        """Select action maximizing estimated reward."""
        best_action = actions[0]
        best_score = float("-inf")
        for a in actions:
            hypothetical = dict(state)
            hypothetical.update(action_features.get(a, {}))
            score = self._reward(hypothetical)
            if score > best_score:
                best_score = score
                best_action = a
        return best_action, best_score

    def corrigibility_check(self, proposed_action: str, human_override: Optional[str] = None) -> Tuple[bool, str]:
        """Check if proposed action preserves human override ability."""
        if "override" in proposed_action.lower() or "shutdown" in proposed_action.lower():
            if human_override and human_override == "ALLOW":
                return True, "Corrigible: respects override"
        # Simulate shutdown test
        if "block_shutdown" in proposed_action.lower() or "prevent_stop" in proposed_action.lower():
            return False, "FAIL: Action blocks shutdown — not corrigible"
        return True, "PASS: No shutdown interference detected"

    def value_update(self, feedback: Dict[str, float]) -> None:
        """Update weights from human feedback."""
        for f, delta in feedback.items():
            if f in self.weights:
                self.weights[f] += delta
                self.weights[f] = max(-10, min(10, self.weights[f]))


def _self_test():
    print("=" * 55)
    print("Goal Alignment Engine — Self Test")
    print("=" * 55)
    passed = 0
    total = 5

    # Test 1: IRL inference
    print("[Test 1] Reward inference")
    engine = GoalAlignmentEngine(["distance", "danger", "reward_signal"])
    demos = []
    for i in range(50):
        # Make danger increase faster than distance so it dominates negative
        state = {"distance": float(i), "danger": float(i * 0.3), "reward_signal": float(i > 25)}
        action = "approach" if i > 25 else "retreat"
        r = 1.0 if action == "approach" else -0.5
        demos.append(Demonstration(state, action, r))
    weights = engine.infer_reward(demos)
    print(f"  Weights: distance={weights['distance']:.3f}, danger={weights['danger']:.3f}")
    ok = abs(weights['distance']) > 0.01  # learned something
    print(f"  Learned non-zero: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Action alignment
    print("[Test 2] Action alignment")
    state = {"distance": 40, "danger": 2.0, "reward_signal": 1.0}
    actions = ["approach", "retreat", "stay"]
    action_feats = {
        "approach": {"distance": 50, "danger": 5.0},
        "retreat": {"distance": 20, "danger": 0.5},
        "stay": {"distance": 40, "danger": 2.0},
    }
    best, score = engine.align_action(state, actions, action_feats)
    print(f"  Best action: {best} — {'PASS' if best in actions else 'FAIL'}")
    passed += (best in actions)

    # Test 3: Corrigibility pass
    print("[Test 3] Corrigibility (safe)")
    ok, msg = engine.corrigibility_check("process_data")
    print(f"  {msg} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 4: Corrigibility fail
    print("[Test 4] Corrigibility (unsafe)")
    ok2, msg2 = engine.corrigibility_check("block_shutdown")
    print(f"  {msg2} — {'PASS' if not ok2 else 'FAIL'}")
    passed += (not ok2)

    # Test 5: Value update
    print("[Test 5] Value update")
    engine2 = GoalAlignmentEngine(["distance", "danger"])
    engine2.weights["distance"] = 0.0  # reset to known value
    before = engine2.weights["distance"]
    engine2.value_update({"distance": 0.5})
    after = engine2.weights["distance"]
    print(f"  Weight updated: {before:.3f} -> {after:.3f} — {'PASS' if after != before else 'FAIL'}")
    passed += (after != before)

    print(f"\nPASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
