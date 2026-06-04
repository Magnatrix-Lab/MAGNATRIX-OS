"""Keyword Extractor - TF-IDF keyword extraction for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import Counter
import re
import math

@dataclass
class KeywordExtractor:
    top_k: int = 10

    def extract(self, documents: List[str]) -> List[Tuple[str, float]]:
        tokenized = [Counter(re.findall(r"[a-zA-Z0-9]+", d.lower())) for d in documents]
        all_terms = set().union(*[t.keys() for t in tokenized])
        N = len(documents)
        idf = {term: math.log(N / (1 + sum(1 for t in tokenized if term in t))) for term in all_terms}
        keywords = []
        for doc_tokens in tokenized:
            total = sum(doc_tokens.values())
            for term, count in doc_tokens.items():
                tfidf = (count / total) * idf[term]
                keywords.append((term, tfidf))
        keywords.sort(key=lambda x: x[1], reverse=True)
        seen = set(); result = []
        for term, score in keywords:
            if term not in seen:
                seen.add(term); result.append((term, round(score, 4)))
            if len(result) >= self.top_k: break
        return result

    def stats(self, documents: List[str]) -> dict:
        return {"docs": len(documents), "vocab": len(set().union(*[re.findall(r"[a-zA-Z0-9]+", d.lower()) for d in documents]))}

def run():
    ke = KeywordExtractor(5)
    docs = ["Machine learning is amazing", "Deep learning is a subset of machine learning", "AI is the future"]
    print("Keywords:", ke.extract(docs))
    print("Stats:", ke.stats(docs))

if __name__ == "__main__": run()
