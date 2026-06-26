#!/usr/bin/env python3
"""
Full-Text Search Engine for MAGNATRIX-OS
Inverted index, TF-IDF ranking, fuzzy search, prefix matching, highlighting.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import math
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class Document:
    """A searchable document."""
    id: str
    content: str
    title: str = ""
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    indexed_at: float = field(default_factory=time.time)


@dataclass
class SearchResult:
    """Result from a search query."""
    doc_id: str
    score: float
    highlights: List[str] = field(default_factory=list)
    matched_terms: List[str] = field(default_factory=list)


class Tokenizer:
    """Text tokenization for indexing."""

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text into lowercase terms."""
        text = text.lower()
        # Keep alphanumeric and spaces, replace rest with space
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        tokens = text.split()
        # Remove stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall", "can", "need", "dare", "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through", "during", "before", "after", "above", "below", "between", "under", "and", "but", "or", "yet", "so", "if", "because", "although", "though", "while", "where", "when", "that", "which", "who", "whom", "whose", "what", "this", "these", "those", "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "through", "during", "before", "after", "above", "below", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once"}
        return [t for t in tokens if t not in stop_words and len(t) > 1]

    @staticmethod
    def normalize(token: str) -> str:
        """Simple stemming (remove common suffixes)."""
        suffixes = ["ing", "ed", "er", "est", "ly", "tion", "ness", "ment", "able", "ible"]
        for suffix in suffixes:
            if token.endswith(suffix) and len(token) > len(suffix) + 2:
                return token[:-len(suffix)]
        return token


class InvertedIndex:
    """Inverted index for full-text search."""

    def __init__(self) -> None:
        self._index: Dict[str, Set[str]] = {}  # term -> set of doc_ids
        self._doc_freq: Dict[str, int] = {}  # term -> document frequency
        self._doc_lengths: Dict[str, int] = {}  # doc_id -> token count
        self._docs: Dict[str, Document] = {}
        self._total_docs = 0
        self._lock = threading.Lock()

    def add_document(self, doc: Document) -> None:
        with self._lock:
            tokens = Tokenizer.tokenize(doc.content + " " + doc.title)
            tokens = [Tokenizer.normalize(t) for t in tokens]
            self._docs[doc.id] = doc
            self._doc_lengths[doc.id] = len(tokens)

            # Track which terms appear in this doc (for df)
            seen_terms = set()
            for token in tokens:
                if token not in self._index:
                    self._index[token] = set()
                self._index[token].add(doc.id)
                seen_terms.add(token)

            for term in seen_terms:
                self._doc_freq[term] = self._doc_freq.get(term, 0) + 1

            self._total_docs += 1

    def remove_document(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id not in self._docs:
                return False
            doc = self._docs[doc_id]
            tokens = Tokenizer.tokenize(doc.content + " " + doc.title)
            tokens = [Tokenizer.normalize(t) for t in tokens]

            for token in tokens:
                if token in self._index and doc_id in self._index[token]:
                    self._index[token].remove(doc_id)
                    if not self._index[token]:
                        del self._index[token]
                    self._doc_freq[token] = self._doc_freq.get(token, 0) - 1

            del self._docs[doc_id]
            del self._doc_lengths[doc_id]
            self._total_docs -= 1
            return True

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Search with TF-IDF scoring."""
        query_tokens = Tokenizer.tokenize(query)
        query_tokens = [Tokenizer.normalize(t) for t in query_tokens]
        if not query_tokens:
            return []

        with self._lock:
            # Collect candidate documents
            candidates: Set[str] = set()
            for token in query_tokens:
                if token in self._index:
                    candidates |= self._index[token]

            if not candidates:
                return []

            # Score candidates with TF-IDF
            results = []
            for doc_id in candidates:
                doc = self._docs[doc_id]
                tokens = Tokenizer.tokenize(doc.content + " " + doc.title)
                tokens = [Tokenizer.normalize(t) for t in tokens]

                score = 0.0
                matched = []
                for qt in query_tokens:
                    tf = tokens.count(qt) / len(tokens) if tokens else 0
                    idf = math.log(self._total_docs / (self._doc_freq.get(qt, 1) + 1)) + 1
                    score += tf * idf
                    if qt in tokens:
                        matched.append(qt)

                # Normalize by doc length
                score /= math.log(self._doc_lengths.get(doc_id, 1) + 1)

                highlights = self._highlight(doc, query_tokens)
                results.append(SearchResult(doc_id=doc_id, score=score, highlights=highlights, matched_terms=matched))

            results.sort(key=lambda r: r.score, reverse=True)
            return results[:top_k]

    def prefix_search(self, prefix: str, top_k: int = 10) -> List[SearchResult]:
        """Prefix search for auto-complete."""
        prefix = prefix.lower()
        with self._lock:
            matching_terms = [t for t in self._index.keys() if t.startswith(prefix)]
            candidates: Set[str] = set()
            for term in matching_terms:
                candidates |= self._index[term]

            results = []
            for doc_id in candidates:
                doc = self._docs[doc_id]
                results.append(SearchResult(doc_id=doc_id, score=1.0, highlights=[doc.title or doc.content[:100]]))

            return results[:top_k]

    def fuzzy_search(self, query: str, max_distance: int = 2, top_k: int = 10) -> List[SearchResult]:
        """Fuzzy search with Levenshtein distance."""
        query_tokens = Tokenizer.tokenize(query)
        query_tokens = [Tokenizer.normalize(t) for t in query_tokens]
        if not query_tokens:
            return []

        with self._lock:
            candidates: Set[str] = set()
            for qt in query_tokens:
                for term in self._index.keys():
                    if self._levenshtein(qt, term) <= max_distance:
                        candidates |= self._index[term]

            results = []
            for doc_id in candidates:
                doc = self._docs[doc_id]
                tokens = Tokenizer.tokenize(doc.content + " " + doc.title)
                tokens = [Tokenizer.normalize(t) for t in tokens]

                score = 0.0
                matched = []
                for qt in query_tokens:
                    best_match = min((self._levenshtein(qt, t), t) for t in tokens) if tokens else (100, "")
                    if best_match[0] <= max_distance:
                        tf = tokens.count(best_match[1]) / len(tokens) if tokens else 0
                        idf = math.log(self._total_docs / (self._doc_freq.get(best_match[1], 1) + 1)) + 1
                        score += tf * idf * (1 / (best_match[0] + 1))
                        matched.append(best_match[1])

                if score > 0:
                    highlights = self._highlight(doc, query_tokens)
                    results.append(SearchResult(doc_id=doc_id, score=score, highlights=highlights, matched_terms=matched))

            results.sort(key=lambda r: r.score, reverse=True)
            return results[:top_k]

    def _levenshtein(self, a: str, b: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(a) < len(b):
            return self._levenshtein(b, a)
        if len(b) == 0:
            return len(a)

        previous_row = list(range(len(b) + 1))
        for i, c1 in enumerate(a):
            current_row = [i + 1]
            for j, c2 in enumerate(b):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _highlight(self, doc: Document, query_tokens: List[str]) -> List[str]:
        """Generate highlighted snippets."""
        content = doc.content
        snippets = []
        for qt in query_tokens:
            pattern = re.compile(r".{0,50}" + re.escape(qt) + r".{0,50}", re.IGNORECASE)
            for match in pattern.finditer(content):
                snippet = match.group(0)
                # Mark the matched term
                snippet = re.sub(re.escape(qt), f"**{qt}**", snippet, flags=re.IGNORECASE)
                snippets.append(snippet)
                if len(snippets) >= 3:
                    break
            if len(snippets) >= 3:
                break
        return snippets[:3]

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self._docs.get(doc_id)

    def list_documents(self) -> List[str]:
        return list(self._docs.keys())

    def stats(self) -> Dict[str, Any]:
        return {
            "total_documents": self._total_docs,
            "unique_terms": len(self._index),
            "avg_doc_length": sum(self._doc_lengths.values()) / len(self._doc_lengths) if self._doc_lengths else 0,
        }

    def save(self, path: str) -> str:
        data = {
            "docs": [{"id": d.id, "content": d.content, "title": d.title, "source": d.source, "metadata": d.metadata} for d in self._docs.values()],
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def load(self, path: str) -> bool:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            for d in data.get("docs", []):
                self.add_document(Document(**d))
            return True
        except Exception:
            return False


class SearchEngine:
    """Main search engine for MAGNATRIX-OS."""

    def __init__(self, repo_root: str = "") -> None:
        self.root = Path(repo_root).resolve() if repo_root else Path.cwd()
        self.index = InvertedIndex()
        self._initialized = False

    def index_module_docs(self, registry: Any) -> int:
        """Index all module documentation."""
        count = 0
        try:
            modules = registry.list_modules() if registry else []
            for m in modules:
                doc = Document(
                    id=f"module_{m.get('name', 'unknown')}",
                    content=m.get("description", ""),
                    title=f"Module: {m.get('name', 'unknown')}",
                    source="registry",
                    metadata={"state": m.get("state"), "load_ms": m.get("load_ms", 0)},
                )
                self.index.add_document(doc)
                count += 1
        except Exception:
            pass
        return count

    def search(self, query: str, fuzzy: bool = False, top_k: int = 10) -> List[Dict[str, Any]]:
        if fuzzy:
            results = self.index.fuzzy_search(query, top_k=top_k)
        else:
            results = self.index.search(query, top_k=top_k)

        return [
            {
                "id": r.doc_id,
                "score": round(r.score, 4),
                "highlights": r.highlights,
                "matched": r.matched_terms,
                "doc": self.index.get_document(r.doc_id),
            }
            for r in results
        ]

    def autocomplete(self, prefix: str, top_k: int = 5) -> List[str]:
        results = self.index.prefix_search(prefix, top_k=top_k)
        return [r.doc_id for r in results]

    def stats(self) -> Dict[str, Any]:
        return self.index.stats()


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Full-Text Search Engine Demo ===\n")
    engine = SearchEngine()

    # Index sample documents
    docs = [
        Document("1", "MAGNATRIX-OS is a private uncensored AI operating system built in pure Python.", "MAGNATRIX-OS Overview", "docs"),
        Document("2", "The local LLM manager supports Ollama integration with automatic model pulling.", "LLM Manager", "core"),
        Document("3", "Document intelligence allows uploading PDF CSV TXT and chatting with documents via RAG.", "Document Intelligence", "core"),
        Document("4", "The WebSocket engine provides real-time chat log streaming and metrics push.", "WebSocket Engine", "core"),
        Document("5", "Security policy engine includes RBAC per module audit trail and compliance reports.", "Security Policy", "core"),
    ]
    for doc in docs:
        engine.index.add_document(doc)

    print(f"Indexed {engine.index.stats()['total_documents']} documents")

    # Search
    queries = ["AI operating system", "Ollama", "document chat", "real-time", "security audit"]
    for q in queries:
        print(f"\nQuery: '{q}'")
        results = engine.search(q, top_k=3)
        for r in results:
            print(f"  {r['id']}: {r['doc'].title} (score: {r['score']})")
            for h in r['highlights'][:2]:
                print(f"    > {h[:80]}...")

    # Fuzzy search
    print("\nFuzzy search 'Olloma' (typo):")
    results = engine.search("Olloma", fuzzy=True, top_k=3)
    for r in results:
        print(f"  {r['id']}: {r['doc'].title} (score: {r['score']})")

    # Prefix search
    print("\nPrefix search 'doc':")
    for r in engine.autocomplete("doc"):
        print(f"  {r}")

    print(f"\nStats: {engine.stats()}")


if __name__ == "__main__":
    _demo()
