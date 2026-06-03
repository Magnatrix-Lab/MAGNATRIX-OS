"""
llm_search_index_native.py
MAGNATRIX-OS Search Index Engine
Native Python, stdlib only.
Provides inverted index construction, BM25 scoring, boolean queries, and faceted search.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class QueryType(Enum):
    TERM = "term"
    PHRASE = "phrase"
    BOOLEAN = "boolean"
    WILDCARD = "wildcard"


@dataclass
class Document:
    id: str
    content: str
    fields: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "content": self.content[:200], "fields": self.fields, "score": self.score}


@dataclass
class SearchResult:
    documents: List[Document]
    total: int
    query_time_ms: float
    query: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "query": self.query,
            "query_time_ms": self.query_time_ms,
            "documents": [d.to_dict() for d in self.documents],
        }


@dataclass
class FacetResult:
    field: str
    values: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {"field": self.field, "values": self.values}


class SearchIndexEngine:
    """
    Inverted index search engine with BM25 scoring.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._docs: Dict[str, Document] = {}
        self._index: Dict[str, Set[str]] = {}  # term -> doc_ids
        self._doc_freqs: Dict[str, int] = {}  # term -> frequency in corpus
        self._doc_lengths: Dict[str, int] = {}  # doc_id -> token count
        self._avg_dl: float = 0.0
        self._total_docs: int = 0

    def _tokenize(self, text: str) -> List[str]:
        return [t.lower() for t in re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())]

    def _update_stats(self) -> None:
        if self._doc_lengths:
            self._avg_dl = sum(self._doc_lengths.values()) / len(self._doc_lengths)
        self._total_docs = len(self._docs)

    def add_document(self, doc: Document) -> None:
        tokens = self._tokenize(doc.content)
        self._docs[doc.id] = doc
        self._doc_lengths[doc.id] = len(tokens)
        for token in set(tokens):
            if token not in self._index:
                self._index[token] = set()
            self._index[token].add(doc.id)
        self._update_stats()

    def remove_document(self, doc_id: str) -> bool:
        if doc_id not in self._docs:
            return False
        tokens = self._tokenize(self._docs[doc_id].content)
        for token in set(tokens):
            if token in self._index:
                self._index[token].discard(doc_id)
        del self._docs[doc_id]
        del self._doc_lengths[doc_id]
        self._update_stats()
        return True

    def _idf(self, term: str) -> float:
        df = len(self._index.get(term, set()))
        if df == 0:
            return 0.0
        return math.log((self._total_docs - df + 0.5) / (df + 0.5) + 1.0)

    def _bm25(self, doc_id: str, term: str) -> float:
        tokens = self._tokenize(self._docs[doc_id].content)
        tf = tokens.count(term)
        dl = self._doc_lengths[doc_id]
        idf = self._idf(term)
        denom = tf + self.k1 * (1 - self.b + self.b * (dl / self._avg_dl)) if self._avg_dl > 0 else tf + self.k1
        return idf * (tf * (self.k1 + 1)) / denom

    def search(self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> SearchResult:
        import time
        start = time.time()
        query_terms = self._tokenize(query)
        if not query_terms:
            return SearchResult(documents=[], total=0, query_time_ms=0, query=query)

        candidate_ids: Optional[Set[str]] = None
        for term in query_terms:
            hits = self._index.get(term, set())
            if candidate_ids is None:
                candidate_ids = set(hits)
            else:
                candidate_ids &= hits
        if candidate_ids is None:
            candidate_ids = set()

        # Apply filters
        if filters:
            for field, value in filters.items():
                candidate_ids = {did for did in candidate_ids if self._docs[did].fields.get(field) == value}

        # Score
        scored: List[Tuple[str, float]] = []
        for doc_id in candidate_ids:
            score = sum(self._bm25(doc_id, term) for term in query_terms)
            scored.append((doc_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        docs = []
        for doc_id, score in top:
            doc = Document(id=self._docs[doc_id].id, content=self._docs[doc_id].content,
                           fields=self._docs[doc_id].fields, score=score)
            docs.append(doc)

        elapsed = (time.time() - start) * 1000
        return SearchResult(documents=docs, total=len(scored), query_time_ms=elapsed, query=query)

    def boolean_search(self, must: List[str] = None, should: List[str] = None, must_not: List[str] = None) -> List[Document]:
        must = must or []
        should = should or []
        must_not = must_not or []
        result: Set[str] = set(self._docs.keys())

        for term in must:
            result &= self._index.get(term, set())
        for term in must_not:
            result -= self._index.get(term, set())
        if should:
            should_hits = set()
            for term in should:
                should_hits |= self._index.get(term, set())
            result &= should_hits

        return [self._docs[did] for did in result]

    def facet_search(self, field: str, query: Optional[str] = None) -> FacetResult:
        docs = list(self._docs.values())
        if query:
            docs = self.search(query, top_k=1000).documents
        values: Dict[str, int] = {}
        for doc in docs:
            val = doc.fields.get(field)
            if val is not None:
                values[str(val)] = values.get(str(val), 0) + 1
        return FacetResult(field=field, values=values)

    def suggest(self, prefix: str, limit: int = 5) -> List[str]:
        prefix = prefix.lower()
        matches = [term for term in self._index.keys() if term.startswith(prefix)]
        matches.sort(key=lambda t: len(self._index[t]), reverse=True)
        return matches[:limit]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_documents": self._total_docs,
            "total_terms": len(self._index),
            "avg_doc_length": round(self._avg_dl, 2),
            "index_size": sum(len(v) for v in self._index.values()),
        }

    def export_index(self, path: str) -> None:
        data = {
            "docs": {k: {"content": v.content, "fields": v.fields} for k, v in self._docs.items()},
            "index": {k: list(v) for k, v in self._index.items()},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def clear(self) -> None:
        self._docs.clear()
        self._index.clear()
        self._doc_lengths.clear()
        self._avg_dl = 0.0
        self._total_docs = 0


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Search Index Engine")
    print("=" * 60)

    engine = SearchIndexEngine(k1=1.2, b=0.75)

    docs = [
        Document("1", "Large language models are powerful tools for natural language processing tasks.", {"category": "ai", "year": 2023}),
        Document("2", "Neural networks form the backbone of modern deep learning systems.", {"category": "ai", "year": 2022}),
        Document("3", "Python is a versatile programming language for data science and AI development.", {"category": "dev", "year": 2023}),
        Document("4", "Machine learning algorithms require large datasets for training.", {"category": "ai", "year": 2021}),
        Document("5", "Natural language processing enables machines to understand human text.", {"category": "nlp", "year": 2023}),
    ]

    for d in docs:
        engine.add_document(d)

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\n--- Search: 'language models' ---")
    result = engine.search("language models", top_k=3)
    print(f"  Total: {result.total}, Time: {result.query_time_ms:.2f}ms")
    for d in result.documents:
        print(f"  [{d.score:.4f}] {d.id}: {d.content[:60]}...")

    print("\n--- Search: 'neural' ---")
    result = engine.search("neural", top_k=3)
    for d in result.documents:
        print(f"  [{d.score:.4f}] {d.id}: {d.content[:60]}...")

    print("\n--- Boolean Search (must: 'language', must_not: 'python') ---")
    docs = engine.boolean_search(must=["language"], must_not=["python"])
    for d in docs:
        print(f"  {d.id}: {d.content[:60]}...")

    print("\n--- Facet: category ---")
    facet = engine.facet_search("category")
    print(facet.to_dict())

    print("\n--- Suggest: 'la' ---")
    suggestions = engine.suggest("la", limit=5)
    print(f"  Suggestions: {suggestions}")

    print("\nSearch Index test complete.")


if __name__ == "__main__":
    run()
