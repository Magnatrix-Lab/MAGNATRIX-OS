"""Document Clustering - K-means for documents for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import Counter
import re
import math
import random

@dataclass
class DocumentClustering:
    k: int = 3
    max_iter: int = 100
    centroids: List[Dict[str, float]] = field(default_factory=list)

    def _vectorize(self, doc: str) -> Dict[str, float]:
        words = re.findall(r"[a-zA-Z0-9]+", doc.lower())
        counts = Counter(words)
        total = sum(counts.values())
        return {w: c/total for w, c in counts.items()}

    def _cosine(self, a: Dict, b: Dict) -> float:
        dot = sum(a.get(w, 0) * b.get(w, 0) for w in set(a.keys()) | set(b.keys()))
        norm_a = math.sqrt(sum(v**2 for v in a.values()))
        norm_b = math.sqrt(sum(v**2 for v in b.values()))
        return dot / (norm_a * norm_b) if norm_a * norm_b > 0 else 0

    def fit(self, documents: List[str]) -> List[int]:
        vectors = [self._vectorize(d) for d in documents]
        self.centroids = random.sample(vectors, min(self.k, len(vectors))) if len(vectors) >= self.k else vectors[:]
        assignments = [0] * len(vectors)
        for _ in range(self.max_iter):
            changed = False
            for i, vec in enumerate(vectors):
                best = max(range(len(self.centroids)), key=lambda j: self._cosine(vec, self.centroids[j]))
                if assignments[i] != best: changed = True
                assignments[i] = best
            for j in range(len(self.centroids)):
                cluster_vecs = [vectors[i] for i in range(len(vectors)) if assignments[i] == j]
                if cluster_vecs:
                    all_words = set().union(*[v.keys() for v in cluster_vecs])
                    self.centroids[j] = {w: sum(v.get(w, 0) for v in cluster_vecs) / len(cluster_vecs) for w in all_words}
            if not changed: break
        return assignments

    def stats(self, documents: List[str]) -> dict:
        assignments = self.fit(documents)
        cluster_sizes = [assignments.count(i) for i in range(self.k)]
        return {"k": self.k, "cluster_sizes": cluster_sizes, "iterations": self.max_iter}

def run():
    dc = DocumentClustering(2)
    docs = ["machine learning is great", "deep learning is amazing", "ai is the future", "cats are cute", "dogs are friendly"]
    assignments = dc.fit(docs)
    print("Assignments:", assignments)
    print("Stats:", dc.stats(docs))

if __name__ == "__main__": run()
