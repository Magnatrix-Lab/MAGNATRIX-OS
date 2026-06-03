"""LLM Topic Modeler — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class TopicModeler:
    def __init__(self) -> None:
        self._stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall", "can", "need", "dare", "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through", "during", "before", "after", "above", "below", "between", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just", "and", "but", "if", "or", "because", "until", "while", "about", "against", "up", "down", "out", "off", "over", "under", "again", "further", "then", "once"}
        self._documents: List[str] = []
        self._vocabulary: Dict[str, int] = {}

    def add_document(self, text: str) -> None:
        self._documents.append(text)
        words = self._extract_words(text)
        for word in words:
            self._vocabulary[word] = self._vocabulary.get(word, 0) + 1

    def _extract_words(self, text: str) -> List[str]:
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in self._stopwords and len(w) > 2]

    def get_top_terms(self, n: int = 10) -> List[tuple]:
        sorted_terms = sorted(self._vocabulary.items(), key=lambda x: x[1], reverse=True)
        return sorted_terms[:n]

    def get_document_topics(self, text: str, top_k: int = 3) -> List[str]:
        words = self._extract_words(text)
        word_counts = {}
        for w in words:
            word_counts[w] = word_counts.get(w, 0) + 1
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:top_k]]

    def get_similarity(self, doc1: str, doc2: str) -> float:
        words1 = set(self._extract_words(doc1))
        words2 = set(self._extract_words(doc2))
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union

    def get_stats(self) -> Dict[str, Any]:
        return {"documents": len(self._documents), "vocabulary": len(self._vocabulary), "avg_doc_length": sum(len(self._extract_words(d)) for d in self._documents) / len(self._documents) if self._documents else 0.0}

def run() -> None:
    print("Topic Modeler test")
    e = TopicModeler()
    e.add_document("Machine learning is transforming artificial intelligence applications.")
    e.add_document("Deep learning neural networks are powerful tools for pattern recognition.")
    e.add_document("Natural language processing helps computers understand human text.")
    print("  Top terms: " + str(e.get_top_terms(5)))
    print("  Doc topics: " + str(e.get_document_topics("Machine learning neural networks are powerful.")))
    print("  Similarity: " + str(e.get_similarity(self._documents[0], self._documents[1])))
    print("  Stats: " + str(e.get_stats()))
    print("Topic Modeler test complete.")

if __name__ == "__main__":
    run()
