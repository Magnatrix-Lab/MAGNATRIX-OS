"""Vector Similarity Search — Cosine, Euclidean, Manhattan, Hamming."""
from dataclasses import dataclass
from pathlib import Path
import json, math

@dataclass
class SearchResult:
    id: int = 0
    score: float = 0.0
    metric: str = ""

class VectorSimilaritySearch:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._queries: list[dict] = []
        self._persist_path = self.root / "vector_search.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._queries = data.get("queries", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({"queries": self._queries}, indent=2))

    def cosine(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def euclidean(self, a: list[float], b: list[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def manhattan(self, a: list[float], b: list[float]) -> float:
        return sum(abs(x - y) for x, y in zip(a, b))

    def hamming(self, a: list[int], b: list[int]) -> float:
        return sum(x != y for x, y in zip(a, b))

    def top_k(self, query: list[float], candidates: list[dict], k: int = 5, metric: str = "cosine") -> list[SearchResult]:
        results = []
        for cand in candidates:
            vec = cand.get("vector", [])
            if not vec:
                continue
            if metric == "cosine":
                score = self.cosine(query, vec)
            elif metric == "euclidean":
                score = -self.euclidean(query, vec)  # negative for sorting
            elif metric == "manhattan":
                score = -self.manhattan(query, vec)
            else:
                score = 0.0
            results.append(SearchResult(id=cand.get("id", 0), score=score, metric=metric))
        results.sort(key=lambda x: x.score, reverse=True)
        self._queries.append({"metric": metric, "k": k, "candidates": len(candidates)})
        self._save()
        return results[:k]

    def to_dict(self) -> dict:
        return {"query_count": len(self._queries)}

    def get_stats(self) -> dict:
        metrics = {}
        for q in self._queries:
            m = q.get("metric", "unknown")
            metrics[m] = metrics.get(m, 0) + 1
        return {"queries": len(self._queries), "by_metric": metrics}

__all__ = ["VectorSimilaritySearch", "SearchResult"]
