"""Narrative Engine — branching, choice weights, state tracking, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class NarrativeEngine:
    states: Dict = field(default_factory=dict)
    choices: List[Dict] = field(default_factory=list)

    def choice_weights(self) -> List[Dict]:
        return [{"text": c["text"], "weight": c.get("weight", 1.0)} for c in self.choices]

    def branch_probability(self, choice_index: int) -> float:
        total = sum(c.get("weight", 1) for c in self.choices)
        return self.choices[choice_index].get("weight", 1) / total if total > 0 and choice_index < len(self.choices) else 0.0

    def state_check(self, flag: str) -> bool:
        return self.states.get(flag, False)

    def stats(self) -> Dict:
        return {"choices": self.choice_weights(), "flag_count": len(self.states)}

def run():
    ne = NarrativeEngine(states={"met_king": True}, choices=[{"text": "Attack", "weight": 2}, {"text": "Flee", "weight": 5}, {"text": "Talk", "weight": 3}])
    print(ne.stats())

if __name__ == "__main__":
    run()
