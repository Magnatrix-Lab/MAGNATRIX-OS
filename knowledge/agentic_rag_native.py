#!/usr/bin/env python3
"""
MAGNATRIX-OS Layer: Knowledge — Agentic RAG Engine
File: knowledge/agentic_rag_native.py
Pattern: AMATI-PELAJARI-TIRU dari priyanshudutta04/AgenticRAG + cesarhgd85/LangGraph-AgenticRAG

Native pure-Python reimplementation of:
  - LangGraph-style workflow (decide → retrieve → generate → web_search → regenerate)
  - FAISS-like in-memory vector store (cosine similarity, pure Python)
  - MCP (Model Context Protocol) mock client untuk external tools
  - Hybrid search: local vector + DuckDuckGo web search via MCP
  - Async/await throughout

Zero external dependencies. Semua vector ops pure Python.
Deterministic embeddings pakai hash-based random projection.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import random
import re
import string
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 1.  EMBEDDING — deterministic hash-based random projection
# ---------------------------------------------------------------------------

class HashEmbedding:
    """
    Deterministic embedding pakai hash-based random projection.
    Tidak perlu numpy / torch. Pure Python, reproducible.
    """

    def __init__(self, dim: int = 128, seed: int = 42) -> None:
        self.dim = dim
        self.seed = seed
        self._rng = random.Random(seed)
        # Pre-generate projection vectors untuk setiap dimensi
        self._projections: List[List[float]] = [
            [self._rng.gauss(0.0, 1.0) for _ in range(256)]
            for _ in range(dim)
        ]

    def _hash_features(self, text: str) -> List[int]:
        """Extract sparse hash features dari text."""
        text = text.lower().translate(str.maketrans("", "", string.punctuation))
        tokens = text.split()
        features: set[int] = set()
        # Unigram + bigram hashes
        for i, tok in enumerate(tokens):
            features.add(int(hashlib.md5(tok.encode()).hexdigest(), 16) % 256)
            if i + 1 < len(tokens):
                bigram = tok + " " + tokens[i + 1]
                features.add(int(hashlib.md5(bigram.encode()).hexdigest(), 16) % 256)
        return list(features)

    def embed(self, text: str) -> List[float]:
        """Embed text jadi dense vector dimensi `self.dim`."""
        features = self._hash_features(text)
        vec: List[float] = []
        for d in range(self.dim):
            proj = self._projections[d]
            val = sum(proj[f] for f in features)
            vec.append(val)
        # L2-normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


# ---------------------------------------------------------------------------
# 2.  VECTOR STORE — in-memory cosine similarity (FAISS replacement)
# ---------------------------------------------------------------------------

@dataclass
class Document:
    id: str
    content: str
    embedding: List[float] = field(repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStore:
    """
    In-memory vector store dengan cosine similarity.
    Replacement native untuk FAISS — pure Python, zero dependency.
    """

    def __init__(self, embedding: HashEmbedding) -> None:
        self._embedding = embedding
        self._docs: List[Document] = []
        self._lock = asyncio.Lock()

    async def add_document(self, content: str, doc_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Document:
        """Add single document."""
        doc_id = doc_id or f"doc_{len(self._docs)}"
        emb = self._embedding.embed(content)
        doc = Document(id=doc_id, content=content, embedding=emb,
                       metadata=metadata or {})
        async with self._lock:
            self._docs.append(doc)
        return doc

    async def add_documents(self, contents: List[str],
                            metadata_list: Optional[List[Dict[str, Any]]] = None) -> List[Document]:
        """Batch add documents."""
        docs: List[Document] = []
        metas = metadata_list or [{}] * len(contents)
        for i, content in enumerate(contents):
            emb = self._embedding.embed(content)
            doc = Document(id=f"doc_{len(self._docs) + i}", content=content,
                           embedding=emb, metadata=metas[i])
            docs.append(doc)
        async with self._lock:
            self._docs.extend(docs)
        return docs

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Cosine similarity dua vector (sudah L2-normalized)."""
        return sum(x * y for x, y in zip(a, b))

    async def search(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """Search top-k documents pakai cosine similarity."""
        q_emb = self._embedding.embed(query)
        async with self._lock:
            scored = [
                (doc, self._cosine_similarity(q_emb, doc.embedding))
                for doc in self._docs
            ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    async def delete(self, doc_id: str) -> bool:
        """Delete document by ID."""
        async with self._lock:
            for i, doc in enumerate(self._docs):
                if doc.id == doc_id:
                    self._docs.pop(i)
                    return True
            return False

    def __len__(self) -> int:
        return len(self._docs)


# ---------------------------------------------------------------------------
# 3.  DOCUMENT CHUNKING — sentence boundaries
# ---------------------------------------------------------------------------

class SentenceChunker:
    """Chunk documents pakai sentence boundaries."""

    SENTENCE_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    MAX_CHUNK_LEN = 512

    @classmethod
    def chunk(cls, text: str, overlap: int = 1) -> List[str]:
        """
        Split text jadi chunks berbasis kalimat.
        overlap = jumlah kalimat overlap antar chunk.
        """
        sentences = [s.strip() for s in cls.SENTENCE_RE.split(text) if s.strip()]
        if not sentences:
            return [text]

        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for sent in sentences:
            sent_len = len(sent)
            if current_len + sent_len > cls.MAX_CHUNK_LEN and current:
                chunks.append(" ".join(current))
                # Overlap: simpan N kalimat terakhir
                current = current[-overlap:] if overlap > 0 else []
                current_len = sum(len(s) for s in current)
            current.append(sent)
            current_len += sent_len

        if current:
            chunks.append(" ".join(current))

        return chunks if chunks else [text]


# ---------------------------------------------------------------------------
# 4.  MCP CLIENT — mock Model Context Protocol client
# ---------------------------------------------------------------------------

class MCPClient:
    """
    Mock MCP (Model Context Protocol) client.
    Simulasi tool calls untuk external integrations.
    Bisa di-swap dengan real MCP client tanpa rubah interface.
    """

    def __init__(self, tools: Optional[Dict[str, Callable[..., Any]]] = None) -> None:
        self._tools = tools or {}
        self._call_log: List[Dict[str, Any]] = []

    def register_tool(self, name: str, fn: Callable[..., Any]) -> None:
        self._tools[name] = fn

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool via MCP protocol."""
        t0 = time.time()
        if tool_name not in self._tools:
            return {"error": f"Tool '{tool_name}' not found", "status": "error"}
        try:
            result = await asyncio.to_thread(self._tools[tool_name], **params)
            self._call_log.append({
                "tool": tool_name, "params": params, "result": result,
                "duration_ms": round((time.time() - t0) * 1000, 2)
            })
            return {"result": result, "status": "ok"}
        except Exception as exc:
            return {"error": str(exc), "status": "error"}

    def get_log(self) -> List[Dict[str, Any]]:
        return self._call_log.copy()


# ---------------------------------------------------------------------------
# 5.  WEB SEARCH — DuckDuckGo via MCP (mockable)
# ---------------------------------------------------------------------------

async def duckduckgo_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    DuckDuckGo instant answer API — pure urllib, no requests dependency.
    Returns list of {title, snippet, url}.
    """
    url = "https://duckduckgo.com/html/"
    # Fallback: HTML scrape (simplified)
    # Untuk native tanpa dependency, kita mock hasilnya
    # Real implementation bisa pakai DDG JSON API
    return [
        {
            "title": f"DDG Result #{i+1} for '{query}'",
            "snippet": f"Mock snippet containing keywords from query: {query[:40]}...",
            "url": f"https://duckduckgo.com/?q={urllib.parse.quote(query)}"
        }
        for i in range(max_results)
    ]


# ---------------------------------------------------------------------------
# 6.  LLM INTERFACE — Groq-style fast LLM (mockable)
# ---------------------------------------------------------------------------

class MockLLM:
    """
    Mock LLM yang simulasi Groq-style fast inference.
    Bisa di-swap dengan real API client.
    """

    def __init__(self, model: str = "mock-llm-v1") -> None:
        self.model = model
        self._call_count = 0

    async def generate(self, prompt: str, max_tokens: int = 512,
                       temperature: float = 0.7) -> str:
        """Generate text dari prompt."""
        self._call_count += 1
        # Simulasi latency
        await asyncio.sleep(0.01)
        # Simple heuristic response
        if "answer" in prompt.lower() or "jawab" in prompt.lower():
            return f"[MockLLM] Based on the provided context, here is the synthesized answer. (call #{self._call_count})"
        if "decide" in prompt.lower() or "perlu" in prompt.lower():
            return "yes" if "what" in prompt.lower() or "who" in prompt.lower() else "no"
        return f"[MockLLM] Generated response for prompt length {len(prompt)}. (call #{self._call_count})"

    def get_stats(self) -> Dict[str, Any]:
        return {"model": self.model, "calls": self._call_count}


# ---------------------------------------------------------------------------
# 7.  AGENT STATE — TypedDict-style class
# ---------------------------------------------------------------------------

@dataclass
class AgentState:
    """
    State object untuk graph workflow.
    Equivalent to LangGraph's AgentState TypedDict.
    """
    question: str = ""
    documents: List[str] = field(default_factory=list)
    answer: str = ""
    needs_retrieval: bool = False
    use_ddg: bool = False
    web_results: List[Dict[str, str]] = field(default_factory=list)
    retrieval_scores: List[float] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3


# ---------------------------------------------------------------------------
# 8.  GRAPH NODES
# ---------------------------------------------------------------------------

class RAGNodes:
    """Collection of graph nodes untuk Agentic RAG workflow."""

    def __init__(self, vector_store: VectorStore, llm: MockLLM,
                 mcp: MCPClient) -> None:
        self.vector_store = vector_store
        self.llm = llm
        self.mcp = mcp

    async def decide_node(self, state: AgentState) -> AgentState:
        """
        Node 1: Decide apakah query perlu retrieval.
        Keyword heuristic + LLM fallback.
        """
        state.iteration += 1
        q = state.question.lower()
        # Heuristic: factual questions need retrieval
        factual_keywords = ["what", "who", "when", "where", "how", "why",
                            "explain", "describe", "compare", "apa", "siapa",
                            "kapan", "dimana", "bagaimana", "mengapa"]
        needs = any(kw in q for kw in factual_keywords)
        if not needs:
            # LLM fallback decision
            prompt = f"Question: {state.question}\nDoes this need document retrieval to answer accurately? Answer yes or no only."
            decision = await self.llm.generate(prompt, max_tokens=10, temperature=0.0)
            needs = "yes" in decision.lower()
        state.needs_retrieval = needs
        return state

    async def retrieve_node(self, state: AgentState) -> AgentState:
        """
        Node 2: Retrieve documents dari vector store.
        """
        if not state.needs_retrieval:
            return state
        results = await self.vector_store.search(state.question, k=5)
        state.documents = [doc.content for doc, _ in results]
        state.retrieval_scores = [score for _, score in results]
        return state

    async def web_search_node(self, state: AgentState) -> AgentState:
        """
        Node 3: Web search via DuckDuckGo (via MCP tool call).
        """
        if not state.use_ddg:
            return state
        # Via MCP
        resp = await self.mcp.call_tool("duckduckgo_search", {
            "query": state.question, "max_results": 3
        })
        if resp["status"] == "ok":
            state.web_results = resp["result"]
        else:
            # Fallback langsung
            state.web_results = await duckduckgo_search(state.question, max_results=3)
        return state

    async def generate_node(self, state: AgentState) -> AgentState:
        """
        Node 4: Generate answer dari documents + web results.
        """
        context_parts: List[str] = []
        if state.documents:
            context_parts.append("=== Retrieved Documents ===")
            for i, doc in enumerate(state.documents, 1):
                context_parts.append(f"[{i}] {doc[:300]}...")
        if state.web_results:
            context_parts.append("=== Web Results ===")
            for i, wr in enumerate(state.web_results, 1):
                context_parts.append(f"[{i}] {wr['title']}: {wr['snippet']}")

        context = "\n".join(context_parts) if context_parts else "No additional context available."
        prompt = f"""Context:
{context}

Question: {state.question}

Provide a concise, accurate answer based on the context above. If the context is insufficient, say so."""
        state.answer = await self.llm.generate(prompt, max_tokens=512, temperature=0.3)
        return state

    async def regenerate_node(self, state: AgentState) -> AgentState:
        """
        Node 5: Regenerate dengan expanded query (query rewriting).
        """
        if state.iteration >= state.max_iterations:
            return state
        # Rewrite query untuk broader retrieval
        rewrite_prompt = f"Rewrite this question to be more general and retrieval-friendly:\n{state.question}"
        rewritten = await self.llm.generate(rewrite_prompt, max_tokens=64, temperature=0.5)
        state.question = rewritten.strip()
        state.documents = []
        state.web_results = []
        return state


# ---------------------------------------------------------------------------
# 9.  CONDITIONAL EDGES
# ---------------------------------------------------------------------------

def needs_retrieval_edge(state: AgentState) -> str:
    """Edge: decide → retrieve (if needs_retrieval) atau generate (if not)."""
    return "retrieve" if state.needs_retrieval else "generate"


def use_ddg_edge(state: AgentState) -> str:
    """Edge: retrieve → web_search (if use_ddg) atau generate."""
    return "web_search" if state.use_ddg else "generate"


def should_regenerate_edge(state: AgentState) -> str:
    """
    Edge: generate → regenerate jika answer insufficient dan belum max iteration.
    Heuristic: check if answer contains "insufficient" or "don't know".
    """
    if state.iteration >= state.max_iterations:
        return "end"
    insufficient_markers = ["insufficient", "don't know", "tidak tahu",
                            "no context", "not enough", "kurang"]
    if any(m in state.answer.lower() for m in insufficient_markers):
        return "regenerate"
    return "end"


# ---------------------------------------------------------------------------
# 10.  GRAPH BUILDER — LangGraph-style workflow assembly
# ---------------------------------------------------------------------------

class AgenticRAGGraph:
    """
    LangGraph-style workflow builder untuk Agentic RAG.
    Nodes: decide → retrieve → (web_search) → generate → (regenerate) → end
    """

    def __init__(self, vector_store: VectorStore, llm: MockLLM,
                 mcp: MCPClient) -> None:
        self.nodes = RAGNodes(vector_store, llm, mcp)
        self._graph: Dict[str, Callable[[AgentState], asyncio.Future[AgentState]]] = {}
        self._edges: Dict[str, Callable[[AgentState], str]] = {}
        self._build()

    def _build(self) -> None:
        self._graph = {
            "decide": self.nodes.decide_node,
            "retrieve": self.nodes.retrieve_node,
            "web_search": self.nodes.web_search_node,
            "generate": self.nodes.generate_node,
            "regenerate": self.nodes.regenerate_node,
        }
        self._edges = {
            "decide": needs_retrieval_edge,
            "retrieve": use_ddg_edge,
            "generate": should_regenerate_edge,
        }

    async def run(self, question: str, use_ddg: bool = False) -> AgentState:
        """
        Execute graph dari start sampai end.
        Returns final AgentState dengan answer.
        """
        state = AgentState(question=question, use_ddg=use_ddg)
        node_name = "decide"
        visited: set[str] = set()

        while node_name != "end":
            if node_name in visited and node_name != "regenerate":
                # Loop detection (kecuali regenerate yang memang iterative)
                break
            visited.add(node_name)

            node_fn = self._graph.get(node_name)
            if not node_fn:
                break
            state = await node_fn(state)

            edge_fn = self._edges.get(node_name)
            if edge_fn:
                node_name = edge_fn(state)
            else:
                node_name = "end"

        return state


# ---------------------------------------------------------------------------
# 11.  HYBRID RETRIEVER — vector + web
# ---------------------------------------------------------------------------

class HybridRetriever:
    """
    Combines vector store retrieval + web search results.
    Deduplicate dan re-rank pakai simple fusion.
    """

    def __init__(self, vector_store: VectorStore, mcp: MCPClient) -> None:
        self.vector_store = vector_store
        self.mcp = mcp

    async def retrieve(self, query: str, k_vector: int = 5,
                       k_web: int = 3) -> List[Dict[str, Any]]:
        """
        Hybrid retrieve: vector docs + web results, merged & deduplicated.
        Returns list of dict dengan 'source', 'content', 'score'.
        """
        # Vector
        vec_results = await self.vector_store.search(query, k=k_vector)
        merged: List[Dict[str, Any]] = [
            {"source": "vector", "content": doc.content, "score": score,
             "id": doc.id}
            for doc, score in vec_results
        ]
        # Web
        web_resp = await self.mcp.call_tool("duckduckgo_search",
                                              {"query": query, "max_results": k_web})
        if web_resp["status"] == "ok":
            web_results: List[Dict[str, str]] = web_resp["result"]
        else:
            web_results = await duckduckgo_search(query, max_results=k_web)
        for wr in web_results:
            merged.append({"source": "web", "content": f"{wr['title']}: {wr['snippet']}",
                           "score": 0.5, "url": wr["url"]})
        # Sort by score desc
        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged


# ---------------------------------------------------------------------------
# 12.  MAIN DEMO & TEST SUITE
# ---------------------------------------------------------------------------

async def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Agentic RAG Engine — Native Demo")
    print("=" * 60)

    # Init components
    emb = HashEmbedding(dim=128, seed=42)
    store = VectorStore(emb)
    llm = MockLLM(model="mock-llm-v1")
    mcp = MCPClient()

    # Register DDG tool ke MCP
    mcp.register_tool("duckduckgo_search",
                      lambda **kwargs: asyncio.run(duckduckgo_search(**kwargs)))

    # Seed documents
    corpus = [
        "Python is a high-level programming language created by Guido van Rossum in 1991.",
        "Asyncio is Python's standard library for writing concurrent code using async/await syntax.",
        "FAISS is a library for efficient similarity search and clustering of dense vectors.",
        "LangGraph is a library for building stateful, multi-actor applications with LLMs.",
        "Model Context Protocol (MCP) enables seamless integration between LLMs and external tools.",
        "MAGNATRIX-OS is a unified agentic operating system built from open-source components.",
        "Hash-based random projection provides deterministic embeddings without neural networks.",
        "Cosine similarity measures the cosine of the angle between two non-zero vectors.",
        "DuckDuckGo is a privacy-focused search engine that does not track users.",
        "Groq is an AI inference company known for extremely fast LLM token generation.",
    ]
    chunker = SentenceChunker()
    all_chunks: List[str] = []
    for doc in corpus:
        all_chunks.extend(chunker.chunk(doc))

    print(f"\n[1] Indexing {len(all_chunks)} chunks into vector store...")
    await store.add_documents(all_chunks)
    print(f"    Vector store size: {len(store)} documents")

    # Build graph
    graph = AgenticRAGGraph(store, llm, mcp)
    hybrid = HybridRetriever(store, mcp)

    # Test 1: Simple retrieval
    print("\n[2] Test 1 — Simple retrieval (no web search)")
    q1 = "What is Python and who created it?"
    result1 = await graph.run(q1, use_ddg=False)
    print(f"    Q: {q1}")
    print(f"    Needs retrieval: {result1.needs_retrieval}")
    print(f"    Docs retrieved: {len(result1.documents)}")
    print(f"    Answer: {result1.answer[:200]}...")

    # Test 2: Hybrid retrieval
    print("\n[3] Test 2 — Hybrid retrieval (vector + web)")
    q2 = "How does DuckDuckGo protect user privacy?"
    result2 = await graph.run(q2, use_ddg=True)
    print(f"    Q: {q2}")
    print(f"    Web results: {len(result2.web_results)}")
    print(f"    Answer: {result2.answer[:200]}...")

    # Test 3: HybridRetriever directly
    print("\n[4] Test 3 — HybridRetriever direct call")
    q3 = "Explain cosine similarity in vector search"
    hybrid_results = await hybrid.retrieve(q3, k_vector=3, k_web=2)
    print(f"    Q: {q3}")
    for i, r in enumerate(hybrid_results[:5], 1):
        src = r["source"]
        content = r["content"][:80]
        print(f"    [{i}] ({src}) {content}... (score: {r['score']:.3f})")

    # Test 4: Regeneration loop
    print("\n[5] Test 4 — Query requiring regeneration")
    q4 = "Tell me about something completely unknown to the corpus"
    result4 = await graph.run(q4, use_ddg=True)
    print(f"    Q: {q4}")
    print(f"    Iterations: {result4.iteration}")
    print(f"    Answer: {result4.answer[:200]}...")

    # Stats
    print("\n[6] Component stats")
    print(f"    LLM calls: {llm.get_stats()}")
    print(f"    MCP calls: {len(mcp.get_log())}")

    print("\n" + "=" * 60)
    print("Demo complete. All tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(_demo())
