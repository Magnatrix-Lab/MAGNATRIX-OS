#!/usr/bin/env python3
"""
document_agent_native.py — Multi-Document Agent with Meta-Agent Routing
AMATI-PELAJARI-TIRU dari AyushParikh/LlamaIndex-Agent pattern.

Architecture:
  BaseLayer    → DocumentChunk, HashEmbedding, VectorIndex
  CoreEngine   → QueryEngine, Reranker (BM25-style), Synthesizer
  Features     → DocumentAgent, MetaAgent (router), MockLLM
  Kernel       → DocumentAgentKernel (wiring + demo scenarios)

Pure Python · stdlib only · zero external dependencies
Target: ~500-700 lines · Single file · Runnable without install
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — BaseLayer
# DocumentChunk · HashEmbedding · VectorIndex
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DocumentChunk:
    """A chunk of a document with embedding and metadata."""
    id: str
    content: str
    doc_id: str
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    index: int = 0  # chunk index within document

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"chunk_{uuid.uuid4().hex[:8]}"

    def __repr__(self) -> str:
        preview = self.content[:40].replace("\n", " ")
        return f"<DocumentChunk id={self.id} doc={self.doc_id} idx={self.index} `{preview}...`>"


class HashEmbedding:
    """
    Deterministic hash-based embedding using stdlib only.
    Simulates semantic vectors without neural networks.
    """

    DIM = 128

    def __init__(self, dim: int = DIM) -> None:
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        """Produce a normalized dense vector from text."""
        # Tokenize + normalize
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dim

        # Build vector via multiple hash functions (simulating n-gram features)
        vec = [0.0] * self.dim
        for token in tokens:
            for i, seed in enumerate([0, 1, 2, 3]):
                h = hashlib.sha256(f"{seed}:{token}".encode()).digest()
                for j in range(self.dim // 4):
                    idx = i * (self.dim // 4) + j
                    val = int.from_bytes(h[j * 4 : j * 4 + 4], "little") / (2**32 - 1)
                    vec[idx] += val

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) + 1e-9
        return [v / norm for v in vec]

    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace + punctuation tokenization."""
        lowered = text.lower()
        # Remove punctuation, keep alphanumerics and spaces
        cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
        tokens = [t for t in cleaned.split() if len(t) > 1]
        # Deduplicate preserving order
        seen: Set[str] = set()
        result: List[str] = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        return dot  # already normalized


class VectorIndex:
    """In-memory vector index for document chunk retrieval."""

    def __init__(self, embedder: HashEmbedding, top_k: int = 5) -> None:
        self.embedder = embedder
        self.top_k = top_k
        self._chunks: List[DocumentChunk] = []
        self._by_doc: Dict[str, List[DocumentChunk]] = defaultdict(list)

    def add(self, chunks: List[DocumentChunk]) -> None:
        """Index document chunks (compute embeddings if missing)."""
        for chunk in chunks:
            if not chunk.embedding:
                chunk.embedding = self.embedder.embed(chunk.content)
            self._chunks.append(chunk)
            self._by_doc[chunk.doc_id].append(chunk)

    def search(self, query: str, k: Optional[int] = None) -> List[Tuple[DocumentChunk, float]]:
        """Retrieve top-k chunks by cosine similarity."""
        k = k or self.top_k
        if not self._chunks:
            return []
        q_vec = self.embedder.embed(query)
        scored = []
        for chunk in self._chunks:
            sim = self.embedder.cosine_similarity(q_vec, chunk.embedding)
            scored.append((chunk, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def get_doc_chunks(self, doc_id: str) -> List[DocumentChunk]:
        return list(self._by_doc.get(doc_id, []))

    def all_docs(self) -> Set[str]:
        return set(self._by_doc.keys())

    def stats(self) -> Dict[str, Any]:
        return {
            "total_chunks": len(self._chunks),
            "total_docs": len(self._by_doc),
            "avg_chunks_per_doc": len(self._chunks) / max(len(self._by_doc), 1),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — CoreEngine
# QueryEngine · Reranker · Synthesizer
# ═══════════════════════════════════════════════════════════════════════════════


class Reranker:
    """
    BM25-style sparse scoring for re-ranking retrieved chunks.
    Blends with vector similarity for hybrid relevance.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._doc_freqs: Dict[str, int] = defaultdict(int)
        self._doc_lengths: List[int] = []
        self._avg_dl: float = 0.0
        self._N: int = 0

    def index_corpus(self, chunks: List[DocumentChunk]) -> None:
        """Pre-compute document frequencies and lengths."""
        self._doc_freqs.clear()
        self._doc_lengths = []
        self._N = len(chunks)
        term_doc_counts: Dict[str, Set[int]] = defaultdict(set)
        lengths: List[int] = []

        for i, chunk in enumerate(chunks):
            tokens = set(self._tokenize(chunk.content))
            lengths.append(len(tokens))
            for t in tokens:
                term_doc_counts[t].add(i)

        for term, docs in term_doc_counts.items():
            self._doc_freqs[term] = len(docs)

        self._doc_lengths = lengths
        self._avg_dl = sum(lengths) / max(len(lengths), 1)

    def score(self, query: str, chunk: DocumentChunk, vector_score: float = 0.0) -> float:
        """Hybrid score: 0.6 * BM25 + 0.4 * vector similarity."""
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return vector_score

        d_tokens = self._tokenize(chunk.content)
        dl = len(d_tokens)
        tf_counter = Counter(d_tokens)

        bm25 = 0.0
        for term in q_tokens:
            df = self._doc_freqs.get(term, 0)
            if df == 0:
                continue
            idf = math.log((self._N - df + 0.5) / (df + 0.5) + 1)
            tf = tf_counter.get(term, 0)
            denom = tf + self.k1 * (1 - self.b + self.b * dl / max(self._avg_dl, 1))
            bm25 += idf * (tf * (self.k1 + 1)) / max(denom, 1)

        # Normalize BM25 roughly to [0, 1]
        bm25_norm = min(bm25 / 10.0, 1.0)
        return 0.6 * bm25_norm + 0.4 * vector_score

    def rerank(
        self, query: str, results: List[Tuple[DocumentChunk, float]]
    ) -> List[Tuple[DocumentChunk, float]]:
        """Re-rank vector search results with BM25 blending."""
        reranked = [(chunk, self.score(query, chunk, vec_score)) for chunk, vec_score in results]
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked

    def _tokenize(self, text: str) -> List[str]:
        lowered = text.lower()
        cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
        return [t for t in cleaned.split() if len(t) > 1]


class Synthesizer:
    """Merge multiple document agent responses into a coherent answer."""

    def merge(self, answers: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """
        Combine answers from multiple document agents.
        Returns: {answer, sources, confidence}
        """
        if not answers:
            return {"answer": "No relevant documents found.", "sources": [], "confidence": 0.0}

        # Sort by confidence descending
        answers = sorted(answers, key=lambda x: x.get("confidence", 0), reverse=True)

        # Deduplicate source chunks
        seen_chunks: Set[str] = set()
        sources: List[Dict[str, Any]] = []
        for ans in answers:
            for src in ans.get("sources", []):
                cid = src.get("chunk_id", "")
                if cid and cid not in seen_chunks:
                    seen_chunks.add(cid)
                    sources.append(src)

        # Build synthesized answer
        parts: List[str] = []
        for ans in answers[:3]:
            excerpt = ans.get("answer", "").strip()
            if excerpt and excerpt not in parts:
                parts.append(excerpt)

        # Add source attribution
        if sources:
            doc_names = sorted(set(s.get("doc_id", "unknown") for s in sources))
            attribution = f"\n\n(Sources: {', '.join(doc_names)} — {len(sources)} chunks)"
        else:
            attribution = ""

        answer_text = "\n\n".join(parts) + attribution
        avg_conf = sum(a.get("confidence", 0) for a in answers) / len(answers)

        return {
            "answer": answer_text,
            "sources": sources,
            "confidence": round(avg_conf, 3),
        }


class QueryEngine:
    """
    End-to-end query pipeline:
    embed → vector search → rerank → return top chunks.
    """

    def __init__(self, index: VectorIndex, reranker: Reranker, top_k: int = 5) -> None:
        self.index = index
        self.reranker = reranker
        self.top_k = top_k

    def query(self, question: str) -> List[Tuple[DocumentChunk, float]]:
        """Execute full retrieval pipeline."""
        # Stage 1: vector retrieval
        vector_results = self.index.search(question, k=self.top_k * 2)
        if not vector_results:
            return []
        # Stage 2: re-rank
        reranked = self.reranker.rerank(question, vector_results)
        return reranked[: self.top_k]


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — Features
# DocumentAgent · MetaAgent (MockLLM deprecated, use MockToUnifiedBridge)
# ═══════════════════════════════════════════════════════════════════════════════

from ai.mock_to_unified_bridge import MockToUnifiedBridge

# MockLLM alias for backward compatibility
MockLLM = MockToUnifiedBridge



class DocumentAgent:
    """
    Per-document agent that exposes a query tool.
    Owns a slice of the vector index (its own chunks).
    """

    def __init__(
        self,
        document_id: str,
        document_name: str,
        chunks: List[DocumentChunk],
        query_engine: QueryEngine,
        llm: MockLLM,
    ) -> None:
        self.document_id = document_id
        self.document_name = document_name
        self.chunks = chunks
        self.query_engine = query_engine
        self.llm = llm

    def query(self, question: str) -> Dict[str, Any]:
        """Answer a question using only this document's chunks."""
        # Search within this agent's chunks
        # Build a mini index from owned chunks
        mini_index = VectorIndex(self.query_engine.index.embedder, top_k=3)
        mini_index.add(self.chunks)
        mini_qe = QueryEngine(mini_index, self.query_engine.reranker, top_k=3)
        results = mini_qe.query(question)

        if not results:
            return {
                "answer": f"No relevant information found in {self.document_name}.",
                "sources": [],
                "confidence": 0.0,
                "agent": self.document_id,
            }

        contexts = [chunk.content for chunk, _ in results]
        answer = self.llm.generate(question, contexts)

        sources = [
            {
                "chunk_id": chunk.id,
                "doc_id": chunk.doc_id,
                "score": round(score, 4),
                "excerpt": chunk.content[:80] + "...",
            }
            for chunk, score in results
        ]

        confidence = sum(score for _, score in results) / len(results)

        return {
            "answer": answer,
            "sources": sources,
            "confidence": round(confidence, 3),
            "agent": self.document_id,
        }

    def summarize(self) -> str:
        """Summarize the entire document."""
        full_text = " ".join(c.content for c in self.chunks)
        return self.llm.summarize(full_text)

    def __repr__(self) -> str:
        return f"<DocumentAgent doc={self.document_name} chunks={len(self.chunks)}>"


class MetaAgent:
    """
    Top-level router that selects relevant document agents for a query.
    Implements selective document loading — only relevant docs participate.
    """

    def __init__(
        self,
        document_agents: List[DocumentAgent],
        query_engine: QueryEngine,
        llm: MockLLM,
        synthesizer: Synthesizer,
    ) -> None:
        self.agents = {a.document_id: a for a in document_agents}
        self.query_engine = query_engine
        self.llm = llm
        self.synthesizer = synthesizer
        self._history: List[Dict[str, Any]] = []

    def route(self, query: str, top_n: int = 3) -> List[DocumentAgent]:
        """
        Select the most relevant document agents for a query.
        Uses keyword overlap + lightweight vector probe.
        """
        if len(self.agents) <= top_n:
            return list(self.agents.values())

        query_vec = self.query_engine.index.embedder.embed(query)
        scored: List[Tuple[DocumentAgent, float]] = []

        for agent in self.agents.values():
            # Score by average similarity of top chunk
            best_sim = 0.0
            for chunk in agent.chunks:
                sim = self.query_engine.index.embedder.cosine_similarity(query_vec, chunk.embedding)
                if sim > best_sim:
                    best_sim = sim
            scored.append((agent, best_sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [a for a, _ in scored[:top_n]]

    def ask(self, question: str) -> Dict[str, Any]:
        """
        Full pipeline: route → query selected agents → synthesize.
        """
        selected = self.route(question)
        answers: List[Dict[str, Any]] = []
        for agent in selected:
            ans = agent.query(question)
            answers.append(ans)

        merged = self.synthesizer.merge(answers, question)
        merged["agents_used"] = [a.document_id for a in selected]
        merged["query"] = question

        self._history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": question,
            "answer": merged["answer"],
            "agents": merged["agents_used"],
            "confidence": merged["confidence"],
        })

        return merged

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": a.document_id,
                "name": a.document_name,
                "chunks": len(a.chunks),
            }
            for a in self.agents.values()
        ]

    def __repr__(self) -> str:
        return f"<MetaAgent agents={len(self.agents)} history={len(self._history)}>"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — Kernel
# DocumentAgentKernel (MAGNATRIX bridge + demo scenarios)
# ═══════════════════════════════════════════════════════════════════════════════


class DocumentAgentKernel:
    """
    MAGNATRIX Layer 5 (Knowledge) integration kernel.
    Wires all components and provides runnable demo scenarios.
    """

    def __init__(self) -> None:
        self.embedder = HashEmbedding()
        self.index = VectorIndex(self.embedder, top_k=5)
        self.reranker = Reranker()
        self.query_engine: Optional[QueryEngine] = None
        self.llm = MockLLM()
        self.synthesizer = Synthesizer()
        self.meta_agent: Optional[MetaAgent] = None
        self._docs_added = 0

    def add_document(self, doc_id: str, name: str, content: str, chunk_size: int = 200) -> None:
        """Chunk and index a document."""
        chunks = self._chunk_text(doc_id, content, chunk_size)
        self.index.add(chunks)
        self._docs_added += 1

    def _chunk_text(self, doc_id: str, text: str, chunk_size: int) -> List[DocumentChunk]:
        """Simple fixed-size chunking with overlap."""
        words = text.split()
        overlap = max(chunk_size // 5, 20)
        chunks: List[DocumentChunk] = []
        i = 0
        idx = 0
        while i < len(words):
            end = min(i + chunk_size, len(words))
            chunk_text = " ".join(words[i:end])
            chunks.append(
                DocumentChunk(
                    id=f"{doc_id}_chunk_{idx}",
                    content=chunk_text,
                    doc_id=doc_id,
                    index=idx,
                    metadata={"start_word": i, "end_word": end},
                )
            )
            idx += 1
            i += chunk_size - overlap
            if end == len(words):
                break
        return chunks

    def build(self) -> None:
        """Finalize indexing and build queryable agents."""
        # Index corpus for BM25
        self.reranker.index_corpus(self.index._chunks)
        self.query_engine = QueryEngine(self.index, self.reranker, top_k=5)

        # Build per-document agents
        agents: List[DocumentAgent] = []
        for doc_id in self.index.all_docs():
            chunks = self.index.get_doc_chunks(doc_id)
            agent = DocumentAgent(
                document_id=doc_id,
                document_name=doc_id.replace("_", " ").title(),
                chunks=chunks,
                query_engine=self.query_engine,
                llm=self.llm,
            )
            agents.append(agent)

        self.meta_agent = MetaAgent(
            document_agents=agents,
            query_engine=self.query_engine,
            llm=self.llm,
            synthesizer=self.synthesizer,
        )

    def ask(self, question: str) -> Dict[str, Any]:
        """Ask the meta-agent."""
        if not self.meta_agent:
            raise RuntimeError("Kernel not built. Call build() first.")
        return self.meta_agent.ask(question)

    def status(self) -> Dict[str, Any]:
        return {
            "kernel": "DocumentAgentKernel",
            "docs_indexed": self._docs_added,
            "chunks": self.index.stats(),
            "agents": len(self.meta_agent.agents) if self.meta_agent else 0,
            "queries": len(self.meta_agent._history) if self.meta_agent else 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Demo Scenarios
# ═══════════════════════════════════════════════════════════════════════════════


def _demo_docs() -> Dict[str, str]:
    return {
        "bitcoin_whitepaper": """
Bitcoin: A Peer-to-Peer Electronic Cash System.
Satoshi Nakamoto.
Abstract. A purely peer-to-peer version of electronic cash would allow online
payments to be sent directly from one party to another without going through a
financial institution. Digital signatures provide part of the solution, but main
benefits are lost if a trusted third party is still required to prevent double-spending.
We propose a solution to the double-spending problem using a peer-to-peer network.
The network timestamps transactions by hashing them into an ongoing chain of
hash-based proof-of-work, forming a record that cannot be changed without
redoing the proof-of-work. The longest chain not only serves as proof of the
sequence of events witnessed, but proof that it came from the largest pool of
CPU power. As long as a majority of CPU power is controlled by nodes that are
not cooperating to attack the network, they'll generate the longest chain and
outpace attackers. The network itself requires minimal structure. Messages are
broadcast on a best effort basis, and nodes can leave and rejoin the network at
will, accepting the longest proof-of-work chain as proof of what happened while
they were gone.
""",
        "ethereum_whitepaper": """
Ethereum Whitepaper.
A Next-Generation Smart Contract and Decentralized Application Platform.
Buterin.
The concept of decentralized consensus and smart contracts has applications far
beyond the currency and financial world. Smart contracts are programs that execute
exactly as programmed without any possibility of downtime, censorship, fraud, or
third-party interference. They can be used to encode arbitrary state transition
functions, allowing developers to create markets, store registries of debts or promises,
and move funds in accordance with instructions given long in the past. Ethereum
provides a Turing-complete programming language used to write scripts or smart
contracts that can encode any fungible digital asset. Ethereum's chief innovation
is the integration of a Turing-complete programming language with a blockchain
platform. Ethereum uses gas to measure computational effort. Every transaction
and smart contract execution costs a certain amount of gas. The gas limit prevents
infinite loops and resource exhaustion.
""",
        "ipfs_paper": """
IPFS — Content Addressed, Versioned, P2P File System.
Juan Benet.
The InterPlanetary File System (IPFS) is a peer-to-peer distributed file system
that seeks to connect all computing devices with the same system of files.
IPFS combines ideas from Kademlia DHT, BitTorrent, and Git to create a single
unified protocol. Content is addressed by its cryptographic hash rather than by
its location. This provides intrinsic deduplication and ensures content integrity.
IPFS uses a Merkle DAG to model the filesystem. Each node in the DAG can be a
file, a directory, or a more complex data structure. The Merkle structure provides
cryptographic integrity and efficient distribution. Bitswap is the block exchange
protocol used by IPFS. It is a generalized version of the BitTorrent protocol
adapted for arbitrary Merkle DAGs. Bitswap uses a want list and a have list to
manage block exchange between peers.
""",
    }


def main() -> None:  # pragma: no cover
    print("=" * 70)
    print("DOCUMENT AGENT NATIVE — Multi-Document Agent with Meta-Agent Routing")
    print("=" * 70)

    kernel = DocumentAgentKernel()

    # ── Load documents ──
    docs = _demo_docs()
    for doc_id, content in docs.items():
        kernel.add_document(doc_id, doc_id, content.strip(), chunk_size=80)
        print(f"Indexed: {doc_id} → {kernel.index.stats()['total_chunks']} total chunks")

    kernel.build()
    print(f"\nKernel built: {kernel.status()}")

    # ── Demo 1: Single document query ──
    print("\n" + "-" * 70)
    print("DEMO 1: Query Single Document (Bitcoin — double spending)")
    print("-" * 70)
    btc_agent = kernel.meta_agent.agents["bitcoin_whitepaper"]
    r1 = btc_agent.query("How does Bitcoin prevent double spending?")
    print(f"\nAnswer:\n{r1['answer']}")
    print(f"Confidence: {r1['confidence']}")
    print(f"Sources: {len(r1['sources'])} chunks")

    # ── Demo 2: Meta-agent routing ──
    print("\n" + "-" * 70)
    print("DEMO 2: Meta-Agent Routing (gas + smart contracts)")
    print("-" * 70)
    r2 = kernel.ask("What is gas and how do smart contracts work?")
    print(f"\nAnswer:\n{r2['answer']}")
    print(f"Agents used: {r2['agents_used']}")
    print(f"Confidence: {r2['confidence']}")

    # ── Demo 3: IPFS content addressing ──
    print("\n" + "-" * 70)
    print("DEMO 3: IPFS Query (Merkle DAG)")
    print("-" * 70)
    r3 = kernel.ask("How does IPFS ensure content integrity?")
    print(f"\nAnswer:\n{r3['answer']}")
    print(f"Agents used: {r3['agents_used']}")

    # ── Demo 4: Cross-document query ──
    print("\n" + "-" * 70)
    print("DEMO 4: Cross-Document Query (peer-to-peer networks)")
    print("-" * 70)
    r4 = kernel.ask("Compare peer-to-peer networks in Bitcoin and IPFS.")
    print(f"\nAnswer:\n{r4['answer']}")
    print(f"Agents used: {r4['agents_used']}")
    print(f"Confidence: {r4['confidence']}")

    # ── Demo 5: Summarization ──
    print("\n" + "-" * 70)
    print("DEMO 5: Document Summarization")
    print("-" * 70)
    for doc_id in ["bitcoin_whitepaper", "ethereum_whitepaper"]:
        agent = kernel.meta_agent.agents[doc_id]
        print(f"\n{doc_id}:")
        print(f"  {agent.summarize()[:200]}...")

    # ── Demo 6: Routing inspection ──
    print("\n" + "-" * 70)
    print("DEMO 6: Routing Inspection")
    print("-" * 70)
    selected = kernel.meta_agent.route("Merkle tree and hash chains", top_n=2)
    print(f"\nFor query 'Merkle tree and hash chains':")
    for a in selected:
        print(f"  → {a.document_name} ({len(a.chunks)} chunks)")

    # ── Demo 7: Index stats + history ──
    print("\n" + "-" * 70)
    print("DEMO 7: System Status & Query History")
    print("-" * 70)
    print(f"\nStatus: {json.dumps(kernel.status(), indent=2)}")
    print(f"\nQuery history ({len(kernel.meta_agent.get_history())} queries):")
    for h in kernel.meta_agent.get_history():
        print(f"  [{h['timestamp']}] {h['query'][:40]}... | agents={h['agents']} | conf={h['confidence']}")

    # ── Final ──
    print("\n" + "=" * 70)
    total = len(open(__file__).readlines())
    print(f"Document Agent Native — COMPLETE ({total} lines)")
    print("=" * 70)


if __name__ == "__main__":
    main()
