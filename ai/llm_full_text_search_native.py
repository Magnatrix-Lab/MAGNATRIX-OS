"""LLM Full Text Search Engine — Native Python (stdlib only)."""
from __future__ import annotations
import re, math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class FullTextSearchEngine:
    def __init__(self) -> None:
        self._index: Dict[str, Dict[str, int]] = {}
        self._doc_count: int = 0
        self._doc_lengths: Dict[str, int] = {}

    def add_document(self, doc_id: str, text: str) -> None:
        words = re.findall(r'\b\w+\b', text.lower())
        self._doc_lengths[doc_id] = len(words)
        self._doc_count += 1
        for word in words:
            if word not in self._index:
                self._index[word] = {}
            self._index[word][doc_id] = self._index[word].get(doc_id, 0) + 1

    def search(self, query: str, top_k: int = 5) -> List[tuple]:
        query_words = re.findall(r'\b\w+\b', query.lower())
        if not query_words:
            return []
        scores = {}
        for word in query_words:
            postings = self._index.get(word, {})
            idf = math.log(self._doc_count / (len(postings) + 1)) + 1
            for doc_id, freq in postings.items():
                tf = freq / self._doc_lengths.get(doc_id, 1)
                scores[doc_id] = scores.get(doc_id, 0) + tf * idf
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        return {"terms": len(self._index), "documents": self._doc_count, "avg_doc_length": sum(self._doc_lengths.values()) / len(self._doc_lengths) if self._doc_lengths else 0}

def run() -> None:
    print("Full Text Search Engine test")
    e = FullTextSearchEngine()
    e.add_document("d1", "machine learning is powerful")
    e.add_document("d2", "deep learning neural networks")
    e.add_document("d3", "machine learning and deep learning")
    results = e.search("machine learning", 3)
    print("  Results: " + str(results))
    print("  Stats: " + str(e.get_stats()))
    print("Full Text Search Engine test complete.")

if __name__ == "__main__":
    run()
