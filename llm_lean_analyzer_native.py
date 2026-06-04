"""Lean Analyzer — waste identification, value stream, flow efficiency, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class LeanAnalyzer:
    steps: List[Dict] = field(default_factory=list)
    """Each step: {name, value_time, wait_time}"""

    def total_lead_time(self) -> float:
        return sum(s.get("value_time", 0) + s.get("wait_time", 0) for s in self.steps)

    def value_added_time(self) -> float:
        return sum(s.get("value_time", 0) for s in self.steps)

    def flow_efficiency(self) -> float:
        total = self.total_lead_time()
        return self.value_added_time() / total if total > 0 else 0.0

    def waste_pct(self) -> float:
        return 1 - self.flow_efficiency()

    def bottlenecks(self) -> List[str]:
        if not self.steps:
            return []
        max_wait = max(s.get("wait_time", 0) for s in self.steps)
        return [s["name"] for s in self.steps if s.get("wait_time", 0) == max_wait and max_wait > 0]

    def seven_wastes(self, issues: List[str]) -> Dict[str, int]:
        wastes = {"transport": 0, "inventory": 0, "motion": 0, "waiting": 0, "overproduction": 0, "overprocessing": 0, "defects": 0}
        keywords = {"transport": ["move", "carry"], "inventory": ["stock", "buffer"], "motion": ["walk", "reach"], "waiting": ["idle", "delay"], "overproduction": ["early", "extra"], "overprocessing": ["unnecessary", "redundant"], "defects": ["error", "rework"]}
        for issue in issues:
            for waste, words in keywords.items():
                if any(w in issue.lower() for w in words):
                    wastes[waste] += 1
        return wastes

    def stats(self) -> Dict:
        return {"lead_time": self.total_lead_time(), "va_time": self.value_added_time(), "efficiency": round(self.flow_efficiency(), 3)}

def run():
    la = LeanAnalyzer([
        {"name": "Cut", "value_time": 5, "wait_time": 2},
        {"name": "Weld", "value_time": 10, "wait_time": 8},
        {"name": "Paint", "value_time": 3, "wait_time": 15},
    ])
    print(la.stats())
    print("Bottlenecks:", la.bottlenecks())
    print("Wastes:", la.seven_wastes(["move material", "delay in weld", "rework paint"]))

if __name__ == "__main__":
    run()
