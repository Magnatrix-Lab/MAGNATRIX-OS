"""LLM Causal Analyzer — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class CausalDirection(Enum):
    CAUSE_TO_EFFECT = auto()
    EFFECT_TO_CAUSE = auto()
    BIDIRECTIONAL = auto()
    UNKNOWN = auto()

@dataclass
class CausalLink:
    id: str
    cause: str
    effect: str
    strength: float
    direction: CausalDirection = CausalDirection.CAUSE_TO_EFFECT
    metadata: Dict[str, Any] = field(default_factory=dict)

class CausalAnalyzer:
    def __init__(self) -> None:
        self._links: List[CausalLink] = []
        self._causes: Dict[str, List[str]] = {}
        self._effects: Dict[str, List[str]] = {}

    def add_link(self, link: CausalLink) -> None:
        self._links.append(link)
        if link.cause not in self._causes:
            self._causes[link.cause] = []
        self._causes[link.cause].append(link.id)
        if link.effect not in self._effects:
            self._effects[link.effect] = []
        self._effects[link.effect].append(link.id)

    def get_effects(self, cause: str) -> List[str]:
        link_ids = self._causes.get(cause, [])
        return [self._links[i].effect for i, lid in enumerate(link_ids) if lid in [l.id for l in self._links]]

    def get_causes(self, effect: str) -> List[str]:
        link_ids = self._effects.get(effect, [])
        return [self._links[i].cause for i, lid in enumerate(link_ids) if lid in [l.id for l in self._links]]

    def find_causal_chain(self, start: str, end: str, max_depth: int = 5) -> List[str]:
        visited = set()
        queue = [(start, [start])]
        while queue:
            current, path = queue.pop(0)
            if current == end:
                return path
            if len(path) >= max_depth:
                continue
            visited.add(current)
            for link in self._links:
                if link.cause == current and link.effect not in visited:
                    queue.append((link.effect, path + [link.effect]))
        return []

    def get_stats(self) -> Dict[str, Any]:
        return {"links": len(self._links), "causes": len(self._causes), "effects": len(self._effects)}

def run() -> None:
    print("Causal Analyzer test")
    e = CausalAnalyzer()
    e.add_link(CausalLink("l1", "rain", "wet_ground", 0.9))
    e.add_link(CausalLink("l2", "wet_ground", "slippery", 0.8))
    e.add_link(CausalLink("l3", "slippery", "fall", 0.7))
    print("  Effects of rain: " + str(e.get_effects("rain")))
    print("  Causes of fall: " + str(e.get_causes("fall")))
    print("  Chain rain to fall: " + str(e.find_causal_chain("rain", "fall")))
    print("  Stats: " + str(e.get_stats()))
    print("Causal Analyzer test complete.")

if __name__ == "__main__":
    run()
