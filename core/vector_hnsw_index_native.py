"""Vector HNSW Index — Hierarchical Navigable Small World, multi-layer graph."""
from dataclasses import dataclass
from pathlib import Path
import json, math, random

@dataclass
class HNSWNode:
    id: int = 0
    vector: list[float] = None
    layer: int = 0
    neighbors: list[int] = None

    def __post_init__(self):
        if self.vector is None:
            self.vector = []
        if self.neighbors is None:
            self.neighbors = []

class VectorHNSWIndex:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._nodes: list[HNSWNode] = []
        self._entry_point: int | None = None
        self._max_layer = 0
        self._m = 5  # max neighbors per layer
        self._ef = 10  # search expansion factor
        self._persist_path = self.root / "vector_hnsw.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._nodes = [HNSWNode(**n) for n in data.get("nodes", [])]
            self._entry_point = data.get("entry_point")
            self._max_layer = data.get("max_layer", 0)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "nodes": [n.__dict__ for n in self._nodes],
            "entry_point": self._entry_point,
            "max_layer": self._max_layer
        }, indent=2))

    def _random_level(self) -> int:
        level = 0
        while random.random() < 0.5 and level < self._max_layer + 1:
            level += 1
        return level

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def insert(self, node_id: int, vector: list[float]) -> HNSWNode:
        layer = self._random_level()
        if layer > self._max_layer:
            self._max_layer = layer
        node = HNSWNode(id=node_id, vector=vector, layer=layer)
        if self._entry_point is None:
            self._entry_point = node_id
            self._nodes.append(node)
            self._save()
            return node
        # Simplified: connect to nearest neighbors at each layer
        for _ in range(min(self._m, len(self._nodes))):
            nearest = self._find_nearest(vector, exclude=node_id)
            if nearest is not None and nearest not in node.neighbors:
                node.neighbors.append(nearest)
        self._nodes.append(node)
        self._save()
        return node

    def _find_nearest(self, vector: list[float], exclude: int = None) -> int | None:
        best = None
        best_sim = -1.0
        for node in self._nodes:
            if node.id == exclude:
                continue
            sim = self._cosine_similarity(vector, node.vector)
            if sim > best_sim:
                best_sim = sim
                best = node.id
        return best

    def search(self, query: list[float], k: int = 5) -> list[tuple[int, float]]:
        results = []
        for node in self._nodes:
            sim = self._cosine_similarity(query, node.vector)
            results.append((node.id, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def to_dict(self) -> dict:
        return {"node_count": len(self._nodes), "max_layer": self._max_layer, "entry_point": self._entry_point}

    def get_stats(self) -> dict:
        return {"nodes": len(self._nodes), "max_layer": self._max_layer, "avg_neighbors": sum(len(n.neighbors) for n in self._nodes) / len(self._nodes) if self._nodes else 0}

__all__ = ["VectorHNSWIndex", "HNSWNode"]
