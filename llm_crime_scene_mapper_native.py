"""Crime Scene Mapper — evidence, measurements, timeline, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Evidence:
    id: str
    x: float
    y: float
    type: str
    timestamp: float

class CrimeSceneMapper:
    def __init__(self):
        self.evidence: List[Evidence] = []
        self.dimensions: Tuple[float, float] = (0, 0)

    def add_evidence(self, e: Evidence):
        self.evidence.append(e)

    def distance_matrix(self) -> Dict[Tuple[str, str], float]:
        dists = {}
        for i in range(len(self.evidence)):
            for j in range(i + 1, len(self.evidence)):
                e1, e2 = self.evidence[i], self.evidence[j]
                d = math.sqrt((e1.x - e2.x)**2 + (e1.y - e2.y)**2)
                dists[(e1.id, e2.id)] = d
        return dists

    def timeline(self) -> List[Evidence]:
        return sorted(self.evidence, key=lambda e: e.timestamp)

    def proximity_search(self, x: float, y: float, radius: float) -> List[Evidence]:
        return [e for e in self.evidence if math.sqrt((e.x - x)**2 + (e.y - y)**2) <= radius]

    def chain_of_custody(self) -> List[str]:
        return [e.id for e in self.timeline()]

    def stats(self) -> Dict:
        return {"evidence_items": len(self.evidence), "area": self.dimensions[0] * self.dimensions[1]}

def run():
    csm = CrimeSceneMapper()
    csm.add_evidence(Evidence("E1", 1.0, 2.0, "blood", 0))
    csm.add_evidence(Evidence("E2", 3.0, 4.0, "bullet", 5))
    csm.add_evidence(Evidence("E3", 1.5, 2.5, "hair", 2))
    print(csm.stats())
    print("Timeline:", [e.id for e in csm.timeline()])
    print("Near (1,2):", [e.id for e in csm.proximity_search(1, 2, 1.5)])

if __name__ == "__main__":
    run()
