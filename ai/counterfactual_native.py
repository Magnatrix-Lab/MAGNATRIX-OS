#!/usr/bin/env python3
"""Counterfactual Planning — MAGNATRIX-OS ASI Expansion
Path: ai/counterfactual_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations
import copy, logging, math, random, sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

@dataclass
class State:
    vars: Dict[str, float]
    def copy(self) -> State: return State(copy.deepcopy(self.vars))

@dataclass
class Action:
    name: str; effects: Dict[str, callable]

@dataclass
class Counterfactual:
    action: Action; state_if: State; outcome: float; probability: float

class WorldModel:
    """Deterministic world model for counterfactual simulation."""
    def __init__(self, rules: List[Tuple[str, callable]]):
        self.rules = rules
    def apply(self, state: State, action: Action) -> State:
        s = state.copy()
        for k, f in action.effects.items():
            s.vars[k] = f(s.vars.get(k, 0.0))
        for name, rule in self.rules:
            s.vars = rule(s.vars)
        return s

class CounterfactualPlanner:
    """Generate and evaluate counterfactual scenarios."""

    def __init__(self, world: WorldModel):
        self.world = world
        self.history: List[Tuple[State, Action, State]] = []

    def simulate(self, state: State, action: Action, steps: int = 1) -> State:
        s = state.copy()
        for _ in range(steps):
            s = self.world.apply(s, action)
        return s

    def counterfactuals(self, observed: Tuple[State, Action, State], alternatives: List[Action]) -> List[Counterfactual]:
        """What would have happened if a different action was taken?"""
        obs_state, obs_action, obs_result = observed
        results = []
        for alt in alternatives:
            if alt.name == obs_action.name:
                continue
            sim = self.simulate(obs_state, alt)
            # Outcome = sum of state variable changes
            outcome = sum(sim.vars.values())
            prob = 1.0 / len(alternatives)  # uniform prior
            results.append(Counterfactual(alt, sim, outcome, prob))
        return sorted(results, key=lambda c: -c.outcome)

    def regret(self, observed: Tuple[State, Action, State], alternatives: List[Action]) -> float:
        """Regret = best counterfactual outcome - observed outcome."""
        cfs = self.counterfactuals(observed, alternatives)
        if not cfs: return 0.0
        obs_outcome = sum(observed[2].vars.values())
        best = max(c.outcome for c in cfs)
        return best - obs_outcome

    def learn(self, state: State, action: Action, result: State) -> None:
        self.history.append((state, action, result))

def _self_test():
    print("=" * 55)
    print("Counterfactual Planning — Self Test")
    print("=" * 55)
    passed, total = 0, 5

    # Grid world: x, y position
    rules = [("bounds", lambda v: {k: max(0, min(10, v.get(k, 0))) for k in v})]
    world = WorldModel(rules)
    planner = CounterfactualPlanner(world)

    # Actions: move in 4 directions
    up = Action("up", {"y": lambda y: y + 1})
    down = Action("down", {"y": lambda y: y - 1})
    right = Action("right", {"x": lambda x: x + 1})
    left = Action("left", {"x": lambda x: x - 1})

    s0 = State({"x": 5, "y": 5})
    s1 = planner.simulate(s0, up)
    ok = s1.vars["y"] == 6
    print(f"  [Test 1] Simulation: y={s1.vars['y']} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    observed = (s0, up, s1)
    alts = [down, right, left]
    cfs = planner.counterfactuals(observed, alts)
    ok = len(cfs) == 3
    print(f"  [Test 2] Counterfactuals: {len(cfs)} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    best_cf = cfs[0]
    ok = best_cf.outcome >= max(c.outcome for c in cfs)
    print(f"  [Test 3] Best CF sorted first — {'PASS' if ok else 'FAIL'}")
    passed += ok

    regret = planner.regret(observed, alts)
    ok = regret >= 0
    print(f"  [Test 4] Regret={regret:.1f} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    planner.learn(s0, up, s1)
    ok = len(planner.history) == 1
    print(f"  [Test 5] History recorded — {'PASS' if ok else 'FAIL'}")
    passed += ok

    print("=" * 55)
    print(f"PASS: {passed}/{total} tests")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    _self_test()
