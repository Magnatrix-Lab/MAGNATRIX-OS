"""Vector ANN Query Engine — Approximate nearest neighbor routing."""
from dataclasses import dataclass
from pathlib import Path
import json, math, heapq

@dataclass
class ANNQuery:
    query_id: str = ""
    query_vector: list[float] = None
    k: int = 5
    ef: int = 10
    results: list[dict] = None

    def __post_init__(self):
        if self.query_vector is None:
            self.query_vector = []
        if self.results is None:
            self.results = []

class VectorANNQueryEngine:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._queries: list[ANNQuery] = []
        self._candidate_pool_size = 100
        self._persist_path = self.root / "vector_ann.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._queries = [ANNQuery(**q) for q in data.get("queries", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "queries": [q.__dict__ for q in self._queries]
        }, indent=2))

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query_vector: list[float], candidates: list[dict], k: int = 5, ef: int = 10) -> ANNQuery:
        query_id = f"q-{len(self._queries)}"
        # Expand candidate pool
        pool = candidates[:self._candidate_pool_size]
        # Scoring
        scored = []
        for c in pool:
            vec = c.get("vector", [])
            if vec:
                score = self._cosine(query_vector, vec)
                scored.append((score, c))
        # Refinement: sort and take top
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:ef]
        # Rerank with more precise scoring (simulated)
        results = [{"id": c[1].get("id"), "score": c[0], "metadata": c[1].get("metadata", {})} for c in top[:k]]
        query = ANNQuery(query_id=query_id, query_vector=query_vector, k=k, ef=ef, results=results)
        self._queries.append(query)
        self._save()
        return query

    def to_dict(self) -> dict:
        return {"query_count": len(self._queries)}

    def get_stats(self) -> dict:
        return {"queries": len(self._queries), "avg_results": sum(len(q.results) for q in self._queries) / len(self._queries) if self._queries else 0}

__all__ = ["VectorANNQueryEngine", "ANNQuery"]
