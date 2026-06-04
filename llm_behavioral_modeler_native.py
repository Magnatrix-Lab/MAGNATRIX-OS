"""Behavioral Modeler — sequence patterns, habit detection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
from collections import Counter, defaultdict
import math
import time

class BehaviorPattern(Enum):
    REPETITIVE = auto()
    SEQUENTIAL = auto()
    CYCLICAL = auto()
    EXPLORATORY = auto()
    GOAL_DIRECTED = auto()

@dataclass
class BehaviorProfile:
    user_id: str
    patterns: List[Tuple[str, ...]]
    frequencies: Dict[str, int]
    dominant_pattern: Optional[str] = None

class BehavioralModeler:
    def __init__(self, ngram_size: int = 3):
        self.ngram_size = ngram_size
        self.profiles: Dict[str, BehaviorProfile] = {}
        self.sequences: Dict[str, List[str]] = {}
        self.transitions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def add_sequence(self, user_id: str, actions: List[str]):
        if user_id not in self.sequences:
            self.sequences[user_id] = []
        self.sequences[user_id].extend(actions)
        for i in range(len(actions) - 1):
            self.transitions[actions[i]][actions[i+1]] += 1

    def extract_patterns(self, user_id: str) -> List[Tuple[str, ...]]:
        seq = self.sequences.get(user_id, [])
        if len(seq) < self.ngram_size:
            return []
        ngrams = []
        for i in range(len(seq) - self.ngram_size + 1):
            ngrams.append(tuple(seq[i:i+self.ngram_size]))
        freq = Counter(ngrams)
        return [ng for ng, count in freq.most_common(10) if count > 1]

    def predict_next(self, current_action: str) -> Optional[str]:
        transitions = self.transitions.get(current_action, {})
        if not transitions:
            return None
        return max(transitions, key=transitions.get)

    def calculate_entropy(self, user_id: str) -> float:
        seq = self.sequences.get(user_id, [])
        if not seq:
            return 0.0
        freq = Counter(seq)
        total = len(seq)
        entropy = 0.0
        for count in freq.values():
            p = count / total
            entropy -= p * math.log2(p)
        return entropy

    def classify_behavior(self, user_id: str) -> str:
        seq = self.sequences.get(user_id, [])
        if not seq:
            return "UNKNOWN"
        entropy = self.calculate_entropy(user_id)
        patterns = self.extract_patterns(user_id)
        if len(patterns) > 5 and entropy < 2.0:
            return BehaviorPattern.REPETITIVE.name
        elif entropy > 3.0:
            return BehaviorPattern.EXPLORATORY.name
        elif len(set(seq)) < len(seq) * 0.5:
            return BehaviorPattern.CYCLICAL.name
        return BehaviorPattern.SEQUENTIAL.name

    def get_profile(self, user_id: str) -> BehaviorProfile:
        patterns = self.extract_patterns(user_id)
        seq = self.sequences.get(user_id, [])
        freq = Counter(seq)
        dominant = self.classify_behavior(user_id)
        return BehaviorProfile(user_id, patterns, dict(freq), dominant)

    def stats(self) -> Dict:
        return {"users": len(self.sequences), "total_actions": sum(len(v) for v in self.sequences.values()), "transitions": len(self.transitions)}

def run():
    modeler = BehavioralModeler(ngram_size=2)
    modeler.add_sequence("user1", ["login", "browse", "search", "view", "add_cart", "checkout", "logout"])
    modeler.add_sequence("user1", ["login", "browse", "view", "add_cart", "checkout", "logout"])
    modeler.add_sequence("user1", ["login", "search", "view", "add_cart", "checkout", "logout"])
    print("Patterns:", modeler.extract_patterns("user1"))
    print("Next after login:", modeler.predict_next("login"))
    print("Entropy:", modeler.calculate_entropy("user1"))
    print(modeler.get_profile("user1"))
    print(modeler.stats())

if __name__ == "__main__":
    run()
