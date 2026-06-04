"""Vision Language Bridge - Image-text alignment for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

@dataclass
class VisionLanguageBridge:
    vocab: List[str] = field(default_factory=list)
    embeddings: Dict[str, List[float]] = field(default_factory=dict)

    def add_token(self, token: str, embedding: List[float]) -> None:
        self.vocab.append(token); self.embeddings[token] = embedding

    def align(self, image_regions: List[List[float]], text_tokens: List[str]) -> List[Tuple[int, str, float]]:
        alignments = []
        for i, region in enumerate(image_regions):
            for token in text_tokens:
                if token in self.embeddings:
                    emb = self.embeddings[token]
                    sim = sum(r*e for r,e in zip(region, emb)) / (math.sqrt(sum(r**2 for r in region))*math.sqrt(sum(e**2 for e in emb)))
                    alignments.append((i, token, round(sim, 4)))
        return sorted(alignments, key=lambda x: x[2], reverse=True)[:5]

    def stats(self) -> dict:
        return {"vocab": len(self.vocab), "embed_dim": len(list(self.embeddings.values())[0]) if self.embeddings else 0}

def run():
    vlb = VisionLanguageBridge()
    vlb.add_token("cat", [0.8, 0.1, 0.1])
    vlb.add_token("dog", [0.1, 0.8, 0.1])
    regions = [[0.7, 0.2, 0.1], [0.1, 0.9, 0.0]]
    print("Alignments:", vlb.align(regions, ["cat", "dog"]))
    print("Stats:", vlb.stats())

if __name__ == "__main__": run()
