"""Graph Embedder - Node embedding for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import random
import math

class EmbeddingMethod(Enum):
    RANDOM_WALK = auto()
    ADJACENCY = auto()
    DEGREE = auto()

@dataclass
class GraphEmbedder:
    dim: int = 3
    method: EmbeddingMethod = EmbeddingMethod.RANDOM_WALK
    walks_per_node: int = 3
    walk_length: int = 5
    embeddings: Dict[str, List[float]] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=dict)

    def fit(self, edges: Dict[str, List[str]], seed: int = 42) -> None:
        random.seed(seed)
        self.edges = edges
        nodes = list(edges.keys())
        if self.method == EmbeddingMethod.RANDOM_WALK:
            for node in nodes:
                walks = []
                for _ in range(self.walks_per_node):
                    walk = [node]
                    for _ in range(self.walk_length):
                        neighbors = self.edges.get(walk[-1], [])
                        if neighbors:
                            walk.append(random.choice(neighbors))
                    walks.append(walk)
                context = [n for walk in walks for n in walk]
                vec = [0.0] * self.dim
                for n in context:
                    idx = hash(n) % self.dim
                    vec[idx] += 1.0
                self.embeddings[node] = [v / max(vec) for v in vec]
        elif self.method == EmbeddingMethod.ADJACENCY:
            all_nodes = sorted(set(nodes).union(*[set(v) for v in edges.values()]))
            idx_map = {n: i for i, n in enumerate(all_nodes)}
            for node in nodes:
                vec = [0.0] * self.dim
                for neighbor in edges.get(node, []):
                    if neighbor in idx_map:
                        vec[idx_map[neighbor] % self.dim] = 1.0
                self.embeddings[node] = vec
        elif self.method == EmbeddingMethod.DEGREE:
            for node in nodes:
                deg = len(edges.get(node, []))
                vec = [0.0] * self.dim
                vec[0] = deg
                self.embeddings[node] = vec

    def similarity(self, a: str, b: str) -> float:
        ea, eb = self.embeddings.get(a, []), self.embeddings.get(b, [])
        if not ea or not eb: return 0.0
        dot = sum(x*y for x, y in zip(ea, eb))
        norm = math.sqrt(sum(x**2 for x in ea)) * math.sqrt(sum(x**2 for x in eb))
        return dot / norm if norm > 0 else 0.0

    def stats(self) -> dict:
        return {"method": self.method.name, "dim": self.dim, "nodes": len(self.embeddings)}

def run():
    ge = GraphEmbedder(4, EmbeddingMethod.RANDOM_WALK)
    edges = {"A": ["B", "C"], "B": ["A", "C"], "C": ["A", "B", "D"], "D": ["C"]}
    ge.fit(edges)
    print("Embeddings:", {k: [round(v, 4) for v in vec] for k, vec in ge.embeddings.items()})
    print("A-B similarity:", round(ge.similarity("A", "B"), 4))
    print("Stats:", ge.stats())

if __name__ == "__main__":
    run()
