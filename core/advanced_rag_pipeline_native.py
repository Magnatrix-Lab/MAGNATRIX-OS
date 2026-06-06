#!/usr/bin/env python3
"""
Advanced RAG Pipeline for MAGNATRIX-OS
Multi-hop reasoning, hybrid search, reranking, contextual compression.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import math
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass
class Chunk:
    id: str
    text: str
    source: str
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    score: float = 0.0
    embedding: Optional[List[float]] = None


@dataclasses.dataclass
class RetrievalResult:
    chunk: Chunk
    score: float
    retrieval_method: str


@dataclasses.dataclass
class Answer:
    text: str
    citations: List[Dict[str, Any]]
    confidence: float
    reasoning_steps: List[str]


class HybridSearcher:
    """Combine dense + sparse + graph retrieval."""

    def __init__(self) -> None:
        self._chunks: List[Chunk] = []
        self._inverted_index: Dict[str, Set[int]] = {}  # word -> chunk indices

    def add_chunks(self, chunks: List[Chunk]) -> None:
        start_idx = len(self._chunks)
        for i, chunk in enumerate(chunks):
            idx = start_idx + i
            self._chunks.append(chunk)
            # Build inverted index
            words = self._tokenize(chunk.text)
            for word in words:
                self._inverted_index.setdefault(word, set()).add(idx)

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b[a-z]+\b', text.lower())

    def _keyword_score(self, query: str, chunk_idx: int) -> float:
        query_words = set(self._tokenize(query))
        chunk_words = set(self._tokenize(self._chunks[chunk_idx].text))
        if not query_words:
            return 0.0
        overlap = len(query_words & chunk_words)
        return overlap / len(query_words)

    def _semantic_similarity(self, query: str, chunk: Chunk) -> float:
        # Simplified: term frequency overlap as proxy for semantic similarity
        query_words = set(self._tokenize(query))
        chunk_words = set(self._tokenize(chunk.text))
        if not query_words or not chunk_words:
            return 0.0
        overlap = len(query_words & chunk_words)
        return overlap / math.sqrt(len(query_words) * len(chunk_words))

    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        # Sparse retrieval via inverted index
        query_words = self._tokenize(query)
        candidate_indices: Set[int] = set()
        for word in query_words:
            candidate_indices |= self._inverted_index.get(word, set())

        if not candidate_indices:
            candidate_indices = set(range(len(self._chunks)))

        # Score candidates
        results = []
        for idx in candidate_indices:
            chunk = self._chunks[idx]
            keyword_score = self._keyword_score(query, idx)
            semantic_score = self._semantic_similarity(query, chunk)

            # RRF fusion: reciprocal rank fusion
            # Simplified weighted sum
            fused_score = 0.4 * keyword_score + 0.6 * semantic_score

            results.append(RetrievalResult(
                chunk=chunk,
                score=fused_score,
                retrieval_method="hybrid",
            ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


class Reranker:
    """Cross-encoder style reranking."""

    def rerank(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        reranked = []
        for i, result in enumerate(results):
            # Heuristic scoring factors:
            # 1. Position bonus (top results get boost)
            position_score = max(0, 1.0 - i * 0.1)

            # 2. Query term density in chunk
            query_words = set(re.findall(r'\b[a-z]+\b', query.lower()))
            chunk_words = set(re.findall(r'\b[a-z]+\b', result.chunk.text.lower()))
            density = len(query_words & chunk_words) / max(1, len(chunk_words))

            # 3. Freshness (if timestamp available)
            freshness = 1.0
            if "timestamp" in result.chunk.metadata:
                age = time.time() - result.chunk.metadata["timestamp"]
                freshness = max(0.5, 1.0 - age / (86400 * 30))  # Decay over 30 days

            # Combine scores
            new_score = (
                0.3 * result.score +  # Original retrieval score
                0.2 * position_score +
                0.3 * density +
                0.2 * freshness
            )

            reranked.append(RetrievalResult(
                chunk=result.chunk,
                score=new_score,
                retrieval_method=f"{result.retrieval_method}+reranked",
            ))

        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked


class ContextualCompressor:
    """Compress retrieved chunks into concise context."""

    def compress(self, results: List[RetrievalResult], max_tokens: int = 2000) -> str:
        # Remove redundant sentences
        unique_sentences = []
        seen = set()
        for result in results:
            sentences = re.split(r'(?<=[.!?])\s+', result.chunk.text)
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                # Deduplication via normalized form
                normalized = re.sub(r'\s+', ' ', sent.lower())
                if normalized not in seen and len(normalized) > 20:
                    seen.add(normalized)
                    unique_sentences.append((sent, result.chunk.source))

        # Build context within token budget (approximate: 1 token ~ 4 chars)
        context_parts = []
        current_chars = 0
        max_chars = max_tokens * 4

        for sent, source in unique_sentences:
            if current_chars + len(sent) > max_chars:
                break
            context_parts.append(f"[{source}] {sent}")
            current_chars += len(sent) + len(source) + 4

        return "\n".join(context_parts)


class QueryDecomposer:
    """Decompose complex queries into sub-queries."""

    def decompose(self, query: str) -> List[str]:
        # Simple decomposition: split by "and" for multi-part questions
        parts = []

        # Check for comparison questions
        if " compare " in query.lower() or " difference between " in query.lower():
            entities = re.findall(r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', query)
            if len(entities) >= 2:
                parts.append(f"What is {entities[0]}?")
                parts.append(f"What is {entities[1]}?")
                parts.append(f"Compare {entities[0]} and {entities[1]}")
                return parts

        # Check for multi-hop questions
        if " who " in query.lower() and " created " in query.lower():
            parts.append(query)
            parts.append(f"What else did the creator of {query} create?")
            return parts

        # Default: single query
        parts.append(query)
        return parts


class MultiHopRAG:
    """Multi-hop retrieval and reasoning."""

    def __init__(self, searcher: HybridSearcher, reranker: Reranker, compressor: ContextualCompressor) -> None:
        self._searcher = searcher
        self._reranker = reranker
        self._compressor = compressor
        self._decomposer = QueryDecomposer()

    def answer(self, query: str, max_hops: int = 2) -> Answer:
        """Multi-hop question answering."""
        reasoning_steps = []
        all_results = []

        # Step 1: Decompose query
        sub_queries = self._decomposer.decompose(query)
        reasoning_steps.append(f"Decomposed into {len(sub_queries)} sub-queries: {sub_queries}")

        # Step 2: Initial retrieval for each sub-query
        for sub_q in sub_queries:
            results = self._searcher.search(sub_q, top_k=5)
            reasoning_steps.append(f"Retrieved {len(results)} chunks for: {sub_q}")
            all_results.extend(results)

        # Step 3: Rerank
        reranked = self._reranker.rerank(query, all_results)
        reasoning_steps.append(f"Reranked to {len(reranked)} top results")

        # Step 4: Multi-hop expansion (if needed)
        if max_hops > 1:
            # Extract entities from top results and search again
            entities = self._extract_entities(reranked[:3])
            for entity in entities:
                follow_up = f"What is known about {entity}?"
                hop_results = self._searcher.search(follow_up, top_k=3)
                reasoning_steps.append(f"Hop 2: Retrieved {len(hop_results)} for '{entity}'")
                reranked.extend(hop_results)

            # Re-rerank after hop
            reranked = self._reranker.rerank(query, reranked)

        # Step 5: Compress context
        context = self._compressor.compress(reranked, max_tokens=2000)
        reasoning_steps.append(f"Compressed context to {len(context)} chars")

        # Step 6: Generate answer (simplified - would use LLM in production)
        answer_text = self._generate_answer(query, context, reranked)

        # Build citations
        citations = [
            {
                "chunk_id": r.chunk.id,
                "source": r.chunk.source,
                "score": r.score,
                "text": r.chunk.text[:100] + "...",
            }
            for r in reranked[:5]
        ]

        confidence = min(1.0, sum(r.score for r in reranked[:3]) / 3)

        return Answer(
            text=answer_text,
            citations=citations,
            confidence=confidence,
            reasoning_steps=reasoning_steps,
        )

    def _extract_entities(self, results: List[RetrievalResult]) -> List[str]:
        entities = []
        for r in results:
            # Extract capitalized words as entities
            found = re.findall(r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', r.chunk.text)
            entities.extend(found[:2])  # Take top 2 per chunk
        return list(set(entities))[:5]  # Unique, max 5

    def _generate_answer(self, query: str, context: str, results: List[RetrievalResult]) -> str:
        # Simplified answer generation (template-based)
        # In production, this would call local_llm_manager_native.py
        if not results:
            return "No relevant information found to answer this query."

        # Summarize key points from top chunks
        key_points = []
        for r in results[:3]:
            sentences = re.split(r'(?<=[.!?])\s+', r.chunk.text)
            if sentences:
                key_points.append(sentences[0])

        return f"Based on the retrieved information:\n\n" + "\n".join(f"- {p}" for p in key_points)


class AdvancedRAGPipeline:
    """Main RAG orchestrator."""

    def __init__(self) -> None:
        self.searcher = HybridSearcher()
        self.reranker = Reranker()
        self.compressor = ContextualCompressor()
        self.rag = MultiHopRAG(self.searcher, self.reranker, self.compressor)

    def add_documents(self, chunks: List[Chunk]) -> None:
        self.searcher.add_chunks(chunks)

    def query(self, question: str, max_hops: int = 2) -> Dict[str, Any]:
        answer = self.rag.answer(question, max_hops=max_hops)
        return {
            "question": question,
            "answer": answer.text,
            "confidence": answer.confidence,
            "citations": answer.citations,
            "reasoning_steps": answer.reasoning_steps,
        }

    def stats(self) -> Dict[str, Any]:
        return {
            "chunks": len(self.searcher._chunks),
            "indexed_terms": len(self.searcher._inverted_index),
        }


def _demo() -> None:
    print("=== Advanced RAG Pipeline Demo ===\n")

    rag = AdvancedRAGPipeline()

    # Add sample documents
    docs = [
        Chunk(id="d1", text="Alice is a software engineer at Google. She created the Kubernetes project in 2014.", source="tech_blog"),
        Chunk(id="d2", text="Kubernetes is an open-source container orchestration platform. It was originally designed by Google.", source="wikipedia"),
        Chunk(id="d3", text="Bob is a researcher at Microsoft. He works on cloud computing and distributed systems.", source="research_paper"),
        Chunk(id="d4", text="Google is located in Mountain View, California. It was founded in 1998 by Larry Page and Sergey Brin.", source="company_info"),
        Chunk(id="d5", text="Microsoft is located in Redmond, Washington. It was founded in 1975 by Bill Gates and Paul Allen.", source="company_info"),
        Chunk(id="d6", text="Container orchestration helps manage containerized applications at scale. Kubernetes is the most popular tool.", source="dev_guide"),
    ]
    rag.add_documents(docs)
    print(f"Added {len(docs)} documents\n")

    # Query 1: Simple factual
    print("--- Query 1: Simple Factual ---")
    result1 = rag.query("What is Kubernetes?")
    print(f"Q: {result1['question']}")
    print(f"A: {result1['answer'][:150]}...")
    print(f"Confidence: {result1['confidence']:.2f}")
    print(f"Steps: {len(result1['reasoning_steps'])}")
    print()

    # Query 2: Multi-hop (who created Kubernetes -> where do they work)
    print("--- Query 2: Multi-hop ---")
    result2 = rag.query("Who created Kubernetes and where do they work?")
    print(f"Q: {result2['question']}")
    print(f"A: {result2['answer'][:150]}...")
    print(f"Confidence: {result2['confidence']:.2f}")
    print(f"Reasoning:")
    for step in result2['reasoning_steps']:
        print(f"  - {step}")
    print()

    # Stats
    print("--- Stats ---")
    stats = rag.stats()
    print(f"  Chunks: {stats['chunks']}")
    print(f"  Indexed terms: {stats['indexed_terms']}")
    print()

    print("=== Advanced RAG Demo Complete ===")


if __name__ == "__main__":
    _demo()
