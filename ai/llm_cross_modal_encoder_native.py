"""Cross Modal Encoder - Unified embedding for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
import math

@dataclass
class CrossModalEncoder:
    dim: int = 4
    projections: Dict[str, List[List[float]]] = field(default_factory=dict)

    def register_projection(self, modality: str, weight_matrix: List[List[float]]) -> None:
        self.projections[modality] = weight_matrix

    def encode(self, modality: str, features: List[float]) -> List[float]:
        W = self.projections.get(modality, [[0.0]*len(features) for _ in range(self.dim)])
        return [sum(features[j]*W[i][j] for j in range(len(features))) for i in range(self.dim)]

    def similarity(self, a_mod: str, a_feat: List[float], b_mod: str, b_feat: List[float]) -> float:
        ea = self.encode(a_mod, a_feat); eb = self.encode(b_mod, b_feat)
        dot = sum(x*y for x,y in zip(ea, eb))
        norm = math.sqrt(sum(x**2 for x in ea)) * math.sqrt(sum(x**2 for x in eb))
        return dot / norm if norm > 0 else 0.0

    def stats(self) -> dict:
        return {"dim": self.dim, "modalities": list(self.projections.keys())}

def run():
    cme = CrossModalEncoder(3)
    cme.register_projection("text", [[1,0],[0,1],[0,0]])
    cme.register_projection("image", [[0,1],[1,0],[0,0]])
    sim = cme.similarity("text", [1,0], "image", [0,1])
    print("Cross-modal sim:", round(sim, 4))
    print("Stats:", cme.stats())

if __name__ == "__main__": run()
