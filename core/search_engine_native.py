#!/usr/bin/env python3
"""
Search Engine for MAGNATRIX-OS
Full-text indexing, TF-IDF ranking, boolean search, and
phrase matching. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass
class Document:
    doc_id: str
    title: str
    content: str
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    timestamp: float = dataclasses.field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "metadata": self.metadata,
        }


@dataclasses.dataclass
class SearchResult:
    doc_id: str
    score: float
    title: str
    snippet: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "score": round(self.score, 4),
            "title": self.title,
            "snippet": self.snippet,
        }


class SearchEngine:
    """Lightweight full-text search engine with TF-IDF ranking."""

    def __init__(self, index_dir: Optional[str] = None) -> None:
        self._documents: Dict[str, Document] = {}
        self._index: Dict[str, Set[str]] = {}  # term -> doc_ids
        self._doc_freq: Dict[str, int] = {}  # term -> document frequency
        self._term_freq: Dict[str, Dict[str, int]] = {}  # doc_id -> {term: count}
        self._doc_lengths: Dict[str, int] = {}
        self._avg_doc_length = 0.0
        self.index_dir = Path(index_dir) if index_dir else None
        if self.index_dir:
            self.index_dir.mkdir(parents=True, exist_ok=True)
        self._load_index()

    # ------------------------------------------------------------------
    # Tokenization
    # ------------------------------------------------------------------

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return [t.lower() for t in re.findall(r"\b\w+\b", text) if len(t) > 1]

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def add_document(self, doc: Document) -> None:
        self._documents[doc.doc_id] = doc
        terms = self.tokenize(doc.title + " " + doc.content)
        self._term_freq[doc.doc_id] = {}
        for term in terms:
            self._term_freq[doc.doc_id][term] = self._term_freq[doc.doc_id].get(term, 0) + 1
            if doc.doc_id not in self._index.setdefault(term, set()):
                self._index[term].add(doc.doc_id)
                self._doc_freq[term] = self._doc_freq.get(term, 0) + 1
        self._doc_lengths[doc.doc_id] = len(terms)
        self._avg_doc_length = sum(self._doc_lengths.values()) / max(1, len(self._doc_lengths))
        self._save_index()

    def remove_document(self, doc_id: str) -> bool:
        if doc_id not in self._documents:
            return False
        del self._documents[doc_id]
        for term, docs in list(self._index.items()):
            if doc_id in docs:
                docs.discard(doc_id)
                self._doc_freq[term] = self._doc_freq.get(term, 0) - 1
                if self._doc_freq[term] <= 0:
                    del self._doc_freq[term]
                    del self._index[term]
        self._term_freq.pop(doc_id, None)
        self._doc_lengths.pop(doc_id, None)
        self._avg_doc_length = sum(self._doc_lengths.values()) / max(1, len(self._doc_lengths))
        self._save_index()
        return True

    def update_document(self, doc: Document) -> None:
        self.remove_document(doc.doc_id)
        self.add_document(doc)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        query_terms = self.tokenize(query)
        if not query_terms:
            return []
        # Find candidate documents
        candidates: Set[str] = set()
        for term in query_terms:
            if term in self._index:
                if not candidates:
                    candidates = self._index[term].copy()
                else:
                    candidates &= self._index[term]
        if not candidates:
            # OR fallback
            for term in query_terms:
                if term in self._index:
                    candidates |= self._index[term]
        if not candidates:
            return []
        # Score with TF-IDF + BM25-like
        scored = []
        N = len(self._documents)
        for doc_id in candidates:
            doc = self._documents[doc_id]
            score = 0.0
            for term in query_terms:
                tf = self._term_freq.get(doc_id, {}).get(term, 0)
                df = self._doc_freq.get(term, 0)
                if df == 0:
                    continue
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
                # BM25-like scoring
                k1 = 1.5
                b = 0.75
                doc_len = self._doc_lengths.get(doc_id, 0)
                norm = (1 - b + b * (doc_len / max(1, self._avg_doc_length)))
                score += idf * ((tf * (k1 + 1)) / (tf + k1 * norm))
            snippet = self._make_snippet(doc.content, query_terms)
            scored.append(SearchResult(doc_id, score, doc.title, snippet, doc.metadata))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    def _make_snippet(self, content: str, query_terms: List[str], max_len: int = 200) -> str:
        lower = content.lower()
        for term in query_terms:
            idx = lower.find(term)
            if idx != -1:
                start = max(0, idx - 60)
                end = min(len(content), idx + max_len)
                return content[start:end].replace("\n", " ")
        return content[:max_len]

    def search_phrase(self, phrase: str, limit: int = 10) -> List[SearchResult]:
        results = self.search(phrase, limit=limit * 2)
        filtered = []
        lower_phrase = phrase.lower()
        for r in results:
            doc = self._documents.get(r.doc_id)
            if doc and lower_phrase in (doc.title + " " + doc.content).lower():
                filtered.append(r)
        return filtered[:limit]

    def search_boolean(self, query_terms: List[str], must_include: bool = True, limit: int = 10) -> List[SearchResult]:
        if must_include:
            return self.search(" ".join(query_terms), limit)
        else:
            # OR search
            all_results = []
            for term in query_terms:
                all_results.extend(self.search(term, limit))
            seen = set()
            unique = []
            for r in all_results:
                if r.doc_id not in seen:
                    seen.add(r.doc_id)
                    unique.append(r)
            return unique[:limit]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_index(self) -> None:
        if not self.index_dir:
            return
        data = {
            "documents": {k: {"doc_id": d.doc_id, "title": d.title, "content": d.content, "metadata": d.metadata, "timestamp": d.timestamp} for k, d in self._documents.items()},
            "doc_freq": self._doc_freq,
            "term_freq": {k: dict(v) for k, v in self._term_freq.items()},
            "doc_lengths": self._doc_lengths,
        }
        with open(self.index_dir / "search_index.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _load_index(self) -> None:
        if not self.index_dir:
            return
        path = self.index_dir / "search_index.json"
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, d in data.get("documents", {}).items():
                self._documents[k] = Document(d["doc_id"], d["title"], d["content"], d.get("metadata", {}), d.get("timestamp", 0))
            self._doc_freq = data.get("doc_freq", {})
            self._term_freq = {k: dict(v) for k, v in data.get("term_freq", {}).items()}
            self._doc_lengths = data.get("doc_lengths", {})
            self._avg_doc_length = sum(self._doc_lengths.values()) / max(1, len(self._doc_lengths))
            # Rebuild index
            for term, doc_ids in self._doc_freq.items():
                self._index[term] = set(self._term_freq.keys())  # approximate rebuild
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        total_terms = len(self._index)
        total_docs = len(self._documents)
        avg_terms = sum(len(v) for v in self._term_freq.values()) / max(1, len(self._term_freq))
        return {
            "documents": total_docs,
            "unique_terms": total_terms,
            "avg_terms_per_doc": round(avg_terms, 2),
            "avg_doc_length": round(self._avg_doc_length, 2),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="magnatrix_search_")
    engine = SearchEngine(index_dir=tmp)
    print("=== Search Engine Demo ===\n")
    # Add documents
    docs = [
        Document("d1", "Python Basics", "Python is a programming language. Python is easy to learn.", {"category": "programming"}),
        Document("d2", "Machine Learning", "Machine learning uses Python and statistics. Deep learning is a subset.", {"category": "ai"}),
        Document("d3", "Cooking Guide", "How to cook pasta. Italian recipes are delicious.", {"category": "cooking"}),
        Document("d4", "Python Advanced", "Advanced Python topics include decorators and generators. Python is powerful.", {"category": "programming"}),
    ]
    for d in docs:
        engine.add_document(d)
    # Search
    print("Search 'python':")
    for r in engine.search("python", limit=3):
        print(f"  [{r.score:.4f}] {r.title} — {r.snippet[:60]}")
    # Phrase search
    print("\nPhrase search 'machine learning':")
    for r in engine.search_phrase("machine learning", limit=3):
        print(f"  [{r.score:.4f}] {r.title} — {r.snippet[:60]}")
    # Stats
    print(f"\nStats: {engine.stats()}")
    # Cleanup
    import shutil
    shutil.rmtree(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
