"""Personality Profiler — Big Five/OCEAN traits, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class TraitDimension(Enum):
    OPENNESS = auto()
    CONSCIENTIOUSNESS = auto()
    EXTRAVERSION = auto()
    AGREEABLENESS = auto()
    NEUROTICISM = auto()

@dataclass
class PersonalityProfile:
    user_id: str
    traits: Dict[str, float]
    dominant_trait: str
    profile_type: str

class PersonalityProfiler:
    def __init__(self):
        self.question_mapping = {
            "creative": TraitDimension.OPENNESS,
            "organized": TraitDimension.CONSCIENTIOUSNESS,
            "outgoing": TraitDimension.EXTRAVERSION,
            "kind": TraitDimension.AGREEABLENESS,
            "anxious": TraitDimension.NEUROTICISM,
        }
        self.profiles: Dict[str, PersonalityProfile] = {}

    def score(self, user_id: str, responses: Dict[str, int]) -> PersonalityProfile:
        traits = {t.name: 0.0 for t in TraitDimension}
        counts = {t.name: 0 for t in TraitDimension}
        for question, score in responses.items():
            trait = self.question_mapping.get(question)
            if trait:
                traits[trait.name] += score
                counts[trait.name] += 1
        for trait in traits:
            if counts[trait] > 0:
                traits[trait] = traits[trait] / counts[trait]
            traits[trait] = max(0, min(1, traits[trait] / 5))
        dominant = max(traits, key=traits.get)
        profile_type = self._classify(traits)
        profile = PersonalityProfile(user_id, traits, dominant, profile_type)
        self.profiles[user_id] = profile
        return profile

    def _classify(self, traits: Dict[str, float]) -> str:
        o, c, e, a, n = traits.get("OPENNESS", 0), traits.get("CONSCIENTIOUSNESS", 0), traits.get("EXTRAVERSION", 0), traits.get("AGREEABLENESS", 0), traits.get("NEUROTICISM", 0)
        if o > 0.7 and e > 0.7:
            return "EXPLORER"
        if c > 0.7 and a > 0.7:
            return "SUPPORTER"
        if e > 0.7 and n < 0.3:
            return "LEADER"
        if n > 0.7:
            return "SENSITIVE"
        if o > 0.7 and c < 0.3:
            return "CREATOR"
        return "BALANCED"

    def compare(self, user1: str, user2: str) -> float:
        p1 = self.profiles.get(user1)
        p2 = self.profiles.get(user2)
        if not p1 or not p2:
            return 0.0
        diff = sum((p1.traits.get(t, 0) - p2.traits.get(t, 0)) ** 2 for t in p1.traits)
        return 1.0 - math.sqrt(diff / len(p1.traits))

    def stats(self) -> Dict:
        return {"profiles": len(self.profiles), "dimensions": len(TraitDimension), "types": list(set(p.profile_type for p in self.profiles.values()))}

def run():
    profiler = PersonalityProfiler()
    p1 = profiler.score("user1", {"creative": 5, "organized": 3, "outgoing": 4, "kind": 4, "anxious": 2})
    p2 = profiler.score("user2", {"creative": 2, "organized": 5, "outgoing": 2, "kind": 5, "anxious": 1})
    print(p1)
    print(p2)
    print("Compatibility:", profiler.compare("user1", "user2"))
    print(profiler.stats())

if __name__ == "__main__":
    run()
