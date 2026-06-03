"""LLM Inverted Index Engine — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class InvertedIndexEngine:
    def __init__(self) -> None:
        self._index: Dict[str, Set[str]] = {}
        self._docs: Dict[str, str] = {}
        self._term_freq: Dict[str, Dict[str, int]] = {}

    def add_document(self, doc_id: str, text: str) -> None:
        self._docs[doc_id] = text
        words = text.lower().split()
        for word in words:
            if word not in self._index:
                self._index[word] = set()
                self._term_freq[word] = {}
            self._index[word].add(doc_id)
            self._term_freq[word][doc_id] = self._term_freq[word].get(doc_id, 0) + 1

    def search(self, term: str) -> List[str]:
        return list(self._index.get(term.lower(), set()))

    def search_and(self, terms: List[str]) -> List[str]:
        if not terms:
            return []
        results = set(self._index.get(terms[0].lower(), set()))
        for term in terms[1:]:
            results &= self._index.get(term.lower(), set())
        return list(results)

    def search_or(self, terms: List[str]) -> List[str]:
        results = set()
        for term in terms:
            results.update(self._index.get(term.lower(), set()))
        return list(results)

    def get_term_freq(self, term: str, doc_id: str) -> int:
        return self._term_freq.get(term.lower(), {}).get(doc_id, 0)

    def get_stats(self) -> Dict[str, Any]:
        return {"terms": len(self._index), "documents": len(self._docs), "avg_postings": sum(len(v) for v in self._index.values()) / len(self._index) if self._index else 0}

def run() -> None:
    print("Inverted Index Engine test")
    e = InvertedIndexEngine()
    e.add_document("d1", "the quick brown fox")
    e.add_document("d2", "the lazy dog jumps")
    e.add_document("d3", "the fox and the dog")
    print("  'the': " + str(e.search("the")))
    print("  'fox': " + str(e.search("fox")))
    print("  AND['the','fox']: " + str(e.search_and(["the", "fox"])))
    print("  OR['fox','dog']: " + str(e.search_or(["fox", "dog"])))
    print("  Stats: " + str(e.get_stats()))
    print("Inverted Index Engine test complete.")

if __name__ == "__main__":
    run()
