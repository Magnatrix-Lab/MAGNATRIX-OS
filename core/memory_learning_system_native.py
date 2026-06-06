#!/usr/bin/env python3
"""
Memory & Learning System for MAGNATRIX-OS
Episodic, semantic, procedural memory with preference learning and experience replay.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import math
import os
import random
import time
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass
class Episode:
    id: str
    timestamp: float
    who: str
    what: str
    where: str
    outcome: str
    importance: float = 1.0
    tags: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "who": self.who,
            "what": self.what,
            "where": self.where,
            "outcome": self.outcome,
            "importance": self.importance,
            "tags": self.tags,
        }


@dataclasses.dataclass
class Fact:
    key: str
    value: Any
    confidence: float = 1.0
    created_at: float = dataclasses.field(default_factory=time.time)
    last_accessed: float = dataclasses.field(default_factory=time.time)
    access_count: int = 0
    strength: float = 1.0  # Forgetting curve strength

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "strength": self.strength,
        }


@dataclasses.dataclass
class UserPreference:
    domain: str
    preference: str
    value: Any
    rank: int = 0  # Higher = more preferred
    stability: float = 1.0  # How stable this preference is
    first_seen: float = dataclasses.field(default_factory=time.time)
    last_updated: float = dataclasses.field(default_factory=time.time)
    occurrences: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "preference": self.preference,
            "value": self.value,
            "rank": self.rank,
            "stability": self.stability,
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
            "occurrences": self.occurrences,
        }


class EpisodicMemory:
    """Store and retrieve experience episodes."""

    def __init__(self, max_episodes: int = 1000) -> None:
        self._episodes: List[Episode] = []
        self._max_episodes = max_episodes
        self._by_tag: Dict[str, List[int]] = {}

    def add(self, episode: Episode) -> None:
        self._episodes.append(episode)
        for tag in episode.tags:
            self._by_tag.setdefault(tag, []).append(len(self._episodes) - 1)

        # Trim old episodes
        if len(self._episodes) > self._max_episodes:
            removed = self._episodes.pop(0)
            for tag in removed.tags:
                if tag in self._by_tag:
                    self._by_tag[tag] = [i for i in self._by_tag[tag] if i > 0]
                    self._by_tag[tag] = [i - 1 for i in self._by_tag[tag]]

    def recall(self, tag: Optional[str] = None, who: Optional[str] = None, limit: int = 10) -> List[Episode]:
        if tag and tag in self._by_tag:
            indices = self._by_tag[tag]
            episodes = [self._episodes[i] for i in indices]
        else:
            episodes = list(self._episodes)

        if who:
            episodes = [e for e in episodes if e.who == who]

        # Sort by importance * recency
        episodes.sort(key=lambda e: e.importance * e.timestamp, reverse=True)
        return episodes[:limit]

    def summarize(self, n_recent: int = 5) -> str:
        recent = self._episodes[-n_recent:]
        return " | ".join(f"{e.who}: {e.what} -> {e.outcome}" for e in recent)


class SemanticMemory:
    """Fact storage with forgetting curve and reinforcement."""

    FORGETTING_RATE = 0.001  # Per-second decay
    REINFORCEMENT_RATE = 0.1  # Per access

    def __init__(self) -> None:
        self._facts: Dict[str, Fact] = {}

    def add(self, key: str, value: Any, confidence: float = 1.0) -> None:
        if key in self._facts:
            # Update existing fact (consolidation)
            existing = self._facts[key]
            existing.value = value
            existing.confidence = max(existing.confidence, confidence)
            existing.strength = min(1.0, existing.strength + self.REINFORCEMENT_RATE)
            existing.access_count += 1
        else:
            self._facts[key] = Fact(key=key, value=value, confidence=confidence)

    def get(self, key: str) -> Optional[Fact]:
        fact = self._facts.get(key)
        if fact:
            fact.last_accessed = time.time()
            fact.access_count += 1
            fact.strength = min(1.0, fact.strength + self.REINFORCEMENT_RATE)
        return fact

    def recall(self, key: str) -> Optional[Any]:
        fact = self.get(key)
        if fact is None:
            return None

        # Apply forgetting curve
        elapsed = time.time() - fact.last_accessed
        fact.strength = max(0.0, fact.strength - self.FORGETTING_RATE * elapsed)

        if fact.strength < 0.1:
            return None  # Forgotten

        return fact.value

    def consolidate(self) -> None:
        """Merge similar facts and remove forgotten ones."""
        to_remove = []
        for key, fact in self._facts.items():
            elapsed = time.time() - fact.last_accessed
            fact.strength = max(0.0, fact.strength - self.FORGETTING_RATE * elapsed)
            if fact.strength < 0.05:
                to_remove.append(key)

        for key in to_remove:
            del self._facts[key]

    def query(self, prefix: str) -> List[Fact]:
        return [f for f in self._facts.values() if f.key.startswith(prefix)]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_facts": len(self._facts),
            "avg_strength": sum(f.strength for f in self._facts.values()) / max(1, len(self._facts)),
            "avg_confidence": sum(f.confidence for f in self._facts.values()) / max(1, len(self._facts)),
        }


class PreferenceLearning:
    """Learn and track user preferences."""

    def __init__(self) -> None:
        self._preferences: Dict[str, List[UserPreference]] = {}

    def observe(self, domain: str, preference: str, value: Any, positive: bool = True) -> None:
        key = f"{domain}:{preference}"
        if key not in self._preferences:
            self._preferences[key] = []

        # Find existing preference
        existing = None
        for p in self._preferences[key]:
            if p.value == value:
                existing = p
                break

        if existing:
            existing.occurrences += 1
            existing.last_updated = time.time()
            if positive:
                existing.rank += 1
                existing.stability = min(1.0, existing.stability + 0.05)
            else:
                existing.rank -= 1
                existing.stability = max(0.0, existing.stability - 0.05)
        else:
            self._preferences[key].append(UserPreference(
                domain=domain,
                preference=preference,
                value=value,
                rank=1 if positive else -1,
            ))

    def get_preference(self, domain: str, preference: str) -> Optional[UserPreference]:
        key = f"{domain}:{preference}"
        prefs = self._preferences.get(key, [])
        if not prefs:
            return None
        # Return highest ranked
        prefs.sort(key=lambda p: p.rank * p.stability, reverse=True)
        return prefs[0]

    def get_top_preferences(self, domain: str, n: int = 5) -> List[UserPreference]:
        all_prefs = []
        for key, prefs in self._preferences.items():
            if key.startswith(f"{domain}:"):
                all_prefs.extend(prefs)
        all_prefs.sort(key=lambda p: p.rank * p.stability, reverse=True)
        return all_prefs[:n]


class ExperienceReplay:
    """Sample past experiences for learning."""

    def __init__(self, memory: EpisodicMemory) -> None:
        self._memory = memory
        self._priorities: Dict[str, float] = {}

    def sample(self, n: int = 10, strategy: str = "priority") -> List[Episode]:
        episodes = self._memory._episodes
        if not episodes:
            return []

        if strategy == "random":
            return random.sample(episodes, min(n, len(episodes)))
        elif strategy == "priority":
            # Sample by importance
            weights = [e.importance for e in episodes]
            total = sum(weights)
            if total == 0:
                return random.sample(episodes, min(n, len(episodes)))
            probs = [w / total for w in weights]
            return random.choices(episodes, weights=probs, k=min(n, len(episodes)))
        elif strategy == "recent":
            return episodes[-n:]
        else:
            return episodes[:n]

    def prioritize(self, episode_id: str, importance: float) -> None:
        self._priorities[episode_id] = importance


class MemoryLearningSystem:
    """Main memory and learning orchestrator."""

    def __init__(self, persistence_path: str = "./memory.json") -> None:
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.preferences = PreferenceLearning()
        self.replay = ExperienceReplay(self.episodic)
        self._persistence_path = persistence_path

    def record_episode(self, who: str, what: str, where: str, outcome: str, tags: Optional[List[str]] = None) -> None:
        episode = Episode(
            id=f"ep_{int(time.time())}_{random.randint(1000, 9999)}",
            timestamp=time.time(),
            who=who,
            what=what,
            where=where,
            outcome=outcome,
            tags=tags or [],
        )
        self.episodic.add(episode)

    def learn_fact(self, key: str, value: Any, confidence: float = 1.0) -> None:
        self.semantic.add(key, value, confidence)

    def learn_preference(self, domain: str, preference: str, value: Any, positive: bool = True) -> None:
        self.preferences.observe(domain, preference, value, positive)

    def recall(self, query: str) -> Dict[str, Any]:
        # Try semantic memory first
        fact_value = self.semantic.recall(query)
        if fact_value:
            return {"type": "fact", "value": fact_value}

        # Try episodic memory
        episodes = self.episodic.recall(tag=query)
        if episodes:
            return {"type": "episodes", "value": [e.to_dict() for e in episodes[:3]]}

        # Try preferences
        pref = self.preferences.get_preference(query, "general")
        if pref:
            return {"type": "preference", "value": pref.to_dict()}

        return {"type": "unknown", "value": None}

    def get_personalization(self, domain: str) -> Dict[str, Any]:
        prefs = self.preferences.get_top_preferences(domain, n=5)
        return {
            "domain": domain,
            "preferences": [p.to_dict() for p in prefs],
            "style": "adaptive" if prefs else "default",
        }

    def save(self) -> None:
        data = {
            "episodes": [e.to_dict() for e in self.episodic._episodes],
            "facts": {k: v.to_dict() for k, v in self.semantic._facts.items()},
        }
        with open(self._persistence_path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self) -> None:
        if not os.path.exists(self._persistence_path):
            return
        with open(self._persistence_path, "r") as f:
            data = json.load(f)
        for e_data in data.get("episodes", []):
            self.episodic.add(Episode(**e_data))
        for k, v_data in data.get("facts", {}).items():
            self.semantic._facts[k] = Fact(**v_data)

    def stats(self) -> Dict[str, Any]:
        return {
            "episodes": len(self.episodic._episodes),
            "facts": len(self.semantic._facts),
            "semantic_stats": self.semantic.stats(),
            "preferences": sum(len(v) for v in self.preferences._preferences.values()),
        }


def _demo() -> None:
    print("=== Memory & Learning System Demo ===\n")

    memory = MemoryLearningSystem()

    # Demo 1: Episodic memory
    print("--- Recording Episodes ---")
    memory.record_episode("user", "asked about Python", "chat", "answered correctly", ["python", "question"])
    memory.record_episode("user", "asked about AI", "chat", "provided summary", ["ai", "question"])
    memory.record_episode("user", "complained about speed", "chat", "acknowledged", ["feedback", "performance"])
    print(f"  Recorded 3 episodes\n")

    # Demo 2: Semantic memory
    print("--- Learning Facts ---")
    memory.learn_fact("user:name", "Alice", confidence=0.9)
    memory.learn_fact("user:role", "developer", confidence=0.8)
    memory.learn_fact("user:language", "Python", confidence=0.95)
    print(f"  Learned 3 facts\n")

    # Demo 3: Preference learning
    print("--- Learning Preferences ---")
    memory.learn_preference("response", "format", "concise", positive=True)
    memory.learn_preference("response", "format", "detailed", positive=False)
    memory.learn_preference("response", "format", "concise", positive=True)  # Reinforce
    memory.learn_preference("topic", "interest", "AI", positive=True)
    memory.learn_preference("topic", "interest", "sports", positive=False)
    print(f"  Learned preferences\n")

    # Demo 4: Recall
    print("--- Recall Tests ---")
    print(f"  Recall 'user:name': {memory.recall('user:name')}")
    print(f"  Recall 'python': {memory.recall('python')['type']}")
    print(f"  Recall 'nonexistent': {memory.recall('nonexistent')['type']}")
    print()

    # Demo 5: Personalization
    print("--- Personalization ---")
    personal = memory.get_personalization("response")
    print(f"  Response style: {personal['style']}")
    for p in personal['preferences']:
        print(f"    {p['preference']}={p['value']} (rank={p['rank']}, stability={p['stability']:.2f})")
    print()

    # Demo 6: Experience replay
    print("--- Experience Replay ---")
    samples = memory.replay.sample(3, strategy="priority")
    print(f"  Sampled {len(samples)} episodes")
    for s in samples:
        print(f"    {s.who}: {s.what}")
    print()

    # Demo 7: Forgetting curve
    print("--- Forgetting Curve ---")
    memory.learn_fact("temp:now", "important", confidence=1.0)
    print(f"  Before sleep: strength=1.0")
    # Simulate time passing (reduce strength directly for demo)
    memory.semantic._facts["temp:now"].strength = 0.5
    print(f"  After decay: strength=0.5")
    print(f"  Can recall: {memory.semantic.recall('temp:now') is not None}")
    print()

    # Demo 8: Stats
    print("--- Stats ---")
    stats = memory.stats()
    print(f"  Episodes: {stats['episodes']}")
    print(f"  Facts: {stats['facts']}")
    print(f"  Avg semantic strength: {stats['semantic_stats']['avg_strength']:.2f}")
    print(f"  Preferences: {stats['preferences']}")
    print()

    print("=== Memory & Learning Demo Complete ===")


if __name__ == "__main__":
    _demo()
