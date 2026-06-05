"""Personality Profiler — Big Five, trait scoring, profiles, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class PersonalityProfiler:
    traits: Dict[str, List[int]] = field(default_factory=lambda: {
        "openness": [], "conscientiousness": [], "extraversion": [], "agreeableness": [], "neuroticism": []
    })

    def add_score(self, trait: str, score: int):
        if trait in self.traits:
            self.traits[trait].append(score)

    def profile(self) -> Dict[str, float]:
        return {trait: sum(scores) / len(scores) if scores else 0.0 for trait, scores in self.traits.items()}

    def dominant_trait(self) -> str:
        p = self.profile()
        return max(p, key=p.get)

    def similarity(self, other: 'PersonalityProfiler') -> float:
        p1 = self.profile()
        p2 = other.profile()
        if not p1 or not p2:
            return 0.0
        dot = sum(p1.get(t, 0) * p2.get(t, 0) for t in self.traits)
        n1 = sum(v**2 for v in p1.values()) ** 0.5
        n2 = sum(v**2 for v in p2.values()) ** 0.5
        return dot / (n1 * n2) if n1 * n2 > 0 else 0.0

    def stats(self) -> Dict:
        return {"profile": self.profile(), "dominant": self.dominant_trait()}

def run():
    pp = PersonalityProfiler()
    for t in pp.traits:
        pp.add_score(t, 7)
    pp.add_score("openness", 9)
    print(pp.stats())

if __name__ == "__main__":
    run()
