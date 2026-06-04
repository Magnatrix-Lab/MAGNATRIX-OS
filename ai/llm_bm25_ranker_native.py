"""BM25 Ranker - Best match ranking for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from collections import Counter
import math
import re

@dataclass
class BM25Ranker:
    k1: float = 1.5; b: float = 0.75
    documents: List[List[str]] = field(default_factory=list)
    doc_lengths: List[int] = field(default_factory=list)
    avgdl: float = 0.0
    idf: Dict[str, float] = field(default_factory=dict)
    term_freq: List[Dict[str, int]] = field(default_factory=list)

    def fit(self, documents: List[str]) -> None:
        self.documents = [re.findall(r"[a-zA-Z0-9]+", d.lower()) for d in documents]
        self.doc_lengths = [len(d) for d in self.documents]
        self.avgdl = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0
        self.term_freq = [Counter(d) for d in self.documents]
        all_terms = set().union(*self.documents)
        N = len(self.documents)
        self.idf = {term: math.log((N - sum(1 for d in self.documents if term in d) + 0.5) / (sum(1 for d in self.documents if term in d) + 0.5) + 1) for term in all_terms}

    def score(self, query: str) -> List[float]:
        tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
        scores = []
        for i, doc in enumerate(self.documents):
            score = 0.0
            for term in tokens:
                if term in self.term_freq[i]:
                    f = self.term_freq[i][term]
                    idf = self.idf.get(term, 0)
                    score += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * self.doc_lengths[i] / self.avgdl))
            scores.append(score)
        return scores

    def stats(self) -> dict:
        return {"documents": len(self.documents), "avgdl": round(self.avgdl, 2)}

def run():
    docs = ["the cat sat on the mat", "the dog sat on the log", "cats and dogs are friends"]
    bm25 = BM25Ranker()
    bm25.fit(docs)
    scores = bm25.score("cat sat")
    print("Scores:", [round(s, 4) for s in scores])
    print("Stats:", bm25.stats())

if __name__ == "__main__": run()
