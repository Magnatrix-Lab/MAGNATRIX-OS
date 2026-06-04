"""Query Expander - Query expansion for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from collections import defaultdict
import re
import math

@dataclass
class QueryExpander:
    co_occurrence: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    vocab: Set[str] = field(default_factory=set)

    def fit(self, documents: List[str], window: int = 5) -> None:
        for doc in documents:
            tokens = re.findall(r"[a-zA-Z0-9]+", doc.lower())
            self.vocab.update(tokens)
            for i in range(len(tokens)):
                for j in range(max(0, i-window), min(len(tokens), i+window+1)):
                    if i != j:
                        self.co_occurrence[tokens[i]][tokens[j]] += 1

    def expand(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
        candidates = defaultdict(float)
        for token in tokens:
            for neighbor, count in self.co_occurrence.get(token, {}).items():
                if neighbor not in tokens:
                    candidates[neighbor] += count
        return sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def stats(self) -> dict:
        return {"vocab": len(self.vocab), "co_occurrence_entries": sum(len(v) for v in self.co_occurrence.values())}

def run():
    qe = QueryExpander()
    docs = ["machine learning is great for ai", "deep learning is a subset of machine learning", "ai and machine learning are related"]
    qe.fit(docs)
    print("Expand 'machine':", qe.expand("machine"))
    print("Stats:", qe.stats())

if __name__ == "__main__": run()
