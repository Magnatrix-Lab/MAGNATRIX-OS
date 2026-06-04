"""TF-IDF Scorer - Term frequency inverse document frequency for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import Counter
import math
import re

@dataclass
class TFIDFScorer:
    documents: List[str] = field(default_factory=list)
    idf: Dict[str, float] = field(default_factory=dict)
    tfidf_matrix: List[Dict[str, float]] = field(default_factory=list)

    def fit(self, documents: List[str]) -> None:
        self.documents = documents
        tokenized = [Counter(re.findall(r"[a-zA-Z0-9]+", d.lower())) for d in documents]
        all_terms = set().union(*[t.keys() for t in tokenized])
        self.idf = {term: math.log(len(documents) / (1 + sum(1 for t in tokenized if term in t))) for term in all_terms}
        self.tfidf_matrix = []
        for tokens in tokenized:
            total = sum(tokens.values())
            tfidf = {term: (count/total) * self.idf.get(term, 0) for term, count in tokens.items()}
            self.tfidf_matrix.append(tfidf)

    def score(self, query: str) -> List[float]:
        tokens = Counter(re.findall(r"[a-zA-Z0-9]+", query.lower()))
        scores = []
        for doc_vec in self.tfidf_matrix:
            score = sum(doc_vec.get(term, 0) * count for term, count in tokens.items())
            scores.append(score)
        return scores

    def stats(self) -> dict:
        return {"documents": len(self.documents), "vocab": len(self.idf)}

def run():
    docs = ["the cat sat on the mat", "the dog sat on the log", "cats and dogs are friends"]
    tfidf = TFIDFScorer()
    tfidf.fit(docs)
    scores = tfidf.score("cat sat")
    print("Scores:", [round(s, 4) for s in scores])
    print("Stats:", tfidf.stats())

if __name__ == "__main__": run()
