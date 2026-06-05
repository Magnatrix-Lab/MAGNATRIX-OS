"""Feedback Loop System — RLHF-style preference learning, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import random
import math

class Preference(Enum):
    A = auto()
    B = auto()
    TIE = auto()

@dataclass
class PreferencePair:
    pair_id: str
    prompt: Dict
    response_a: Dict
    response_b: Dict
    preference: Optional[Preference] = None
    reward_a: float = 0.0
    reward_b: float = 0.0

class FeedbackLoop:
    def __init__(self, learning_rate: float = 0.01):
        self.lr = learning_rate
        self.pairs: List[PreferencePair] = []
        self.reward_model: Dict[str, float] = {}
        self.policy_weights: Dict[str, float] = {}

    def add_pair(self, pair_id: str, prompt: Dict, response_a: Dict, response_b: Dict, preference: Preference):
        pair = PreferencePair(pair_id, prompt, response_a, response_b, preference)
        self.pairs.append(pair)
        self._update_reward_model(pair)
        self._update_policy(pair)

    def _score(self, response: Dict, weights: Dict[str, float]) -> float:
        return sum(response.get(k, 0) * weights.get(k, 0) for k in set(response) | set(weights))

    def _update_reward_model(self, pair: PreferencePair):
        for k in set(pair.response_a) | set(pair.response_b):
            if k not in self.reward_model:
                self.reward_model[k] = random.gauss(0, 0.1)
        delta = 0.0
        if pair.preference == Preference.A:
            delta = 1.0
        elif pair.preference == Preference.B:
            delta = -1.0
        for k in set(pair.response_a) | set(pair.response_b):
            diff = pair.response_a.get(k, 0) - pair.response_b.get(k, 0)
            self.reward_model[k] += self.lr * delta * diff
        pair.reward_a = self._score(pair.response_a, self.reward_model)
        pair.reward_b = self._score(pair.response_b, self.reward_model)

    def _update_policy(self, pair: PreferencePair):
        for k in set(pair.response_a) | set(pair.response_b):
            if k not in self.policy_weights:
                self.policy_weights[k] = random.gauss(0, 0.1)
        if pair.preference == Preference.A:
            for k in pair.response_a:
                self.policy_weights[k] += self.lr * pair.response_a[k] * 0.1
        elif pair.preference == Preference.B:
            for k in pair.response_b:
                self.policy_weights[k] += self.lr * pair.response_b[k] * 0.1

    def predict_preference(self, response_a: Dict, response_b: Dict) -> Preference:
        ra = self._score(response_a, self.reward_model)
        rb = self._score(response_b, self.reward_model)
        if abs(ra - rb) < 0.01:
            return Preference.TIE
        return Preference.A if ra > rb else Preference.B

    def stats(self) -> Dict:
        prefs = {}
        for p in self.pairs:
            if p.preference:
                prefs[p.preference.name] = prefs.get(p.preference.name, 0) + 1
        return {"pairs": len(self.pairs), "preferences": prefs, "reward_keys": len(self.reward_model), "policy_keys": len(self.policy_weights)}

def run():
    loop = FeedbackLoop(learning_rate=0.05)
    for i in range(10):
        a = {"quality": random.random(), "length": random.random()}
        b = {"quality": random.random(), "length": random.random()}
        pref = Preference.A if a["quality"] > b["quality"] else Preference.B
        loop.add_pair(f"p{i}", {"task": "summarize"}, a, b, pref)
    print(loop.stats())
    print("Reward model:", loop.reward_model)

if __name__ == "__main__":
    run()
