# agentic_rag_native.py
# AMATI-PELAJARI-TIRU: LangGraph + FAISS + MCP Pattern (from AgenticRAG)
# Pure Python, zero external dependencies. Mock LLM swappable.

from __future__ import annotations
import re, json, math, random, hashlib, dataclasses, typing
from collections import deque
from typing import List, Dict, Optional, Tuple, Any, Callable

# ---------------------------------------------------------------------------
# Deterministic Embedding (hash-based random projection)
# ---------------------------------------------------------------------------

class HashEmbedding:
    """Deterministic embedding via hash-based random projection. No numpy."""

    def __init__(self, dim: int = 128, seed: int = 42):
        self.dim = dim
        self.seed = seed

    def _hash_vector(self, text: str, component: int) -> float:
        h = hashlib.blake2b(key=component.to_bytes(4, "big", signed=True), digest_size=32)
        h.update(text.encode("utf-8"))
        val = int.from_bytes(h.digest(), "big")
        return (val / (2 ** 256)) * 2 - 1  # scale to [-1, 1]

    def embed(self, text: str) -> List[float]:
        vec = [self._hash_vector(text, i) for i in range(self.dim)]
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        return dot  # already normalized

# ---------------------------------------------------------------------------
# Document & Chunking
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class DocumentChunk:
    id: str
    content: str
    embedding: List[float]
    doc_id: str
    metadata: Dict[str, Any]

class Chunker:
    """Sentence-boundary chunking."""

    def __init__(self, max_chunk_size: int = 512, overlap: int = 64):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk(self, text: str, doc_id: str) -> List[DocumentChunk]:
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        buffer = ""
        chunk_idx = 0
        embedder = HashEmbedding()
        for sent in sentences:
            if len(buffer) + len(sent) + 1 > self.max_chunk_size and buffer:
                chunks.append(DocumentChunk(
                    id=f"{doc_id}_chunk_{chunk_idx}",
                    content=buffer.strip(),
                    embedding=embedder.embed(buffer.strip()),
                    doc_id=doc_id,
                    metadata={"index": chunk_idx}
                ))
                buffer = buffer[-self.overlap:] if self.overlap < len(buffer) else ""
                chunk_idx += 1
            buffer += (" " if buffer else "") + sent
        if buffer.strip():
            chunks.append(DocumentChunk(
                id=f"{doc_id}_chunk_{chunk_idx}",
                content=buffer.strip(),
                embedding=embedder.embed(buffer.strip()),
                doc_id=doc_id,
                metadata={"index": chunk_idx}
            ))
        return chunks

# ---------------------------------------------------------------------------
# In-Memory Vector Store (FAISS replacement)
# ---------------------------------------------------------------------------

class VectorStore:
    def __init__(self, dim: int = 128):
        self.dim = dim
        self.embedder = HashEmbedding(dim=dim)
        self.chunks: List[DocumentChunk] = []

    def add_documents(self, chunks: List[DocumentChunk]):
        self.chunks.extend(chunks)

    def search(self, query: str, k: int = 5) -> List[DocumentChunk]:
        qvec = self.embedder.embed(query)
        scored = []
        for chunk in self.chunks:
            sim = self.embedder.cosine_similarity(qvec, chunk.embedding)
            scored.append((sim, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:k]]

    def clear(self):
        self.chunks.clear()

# ---------------------------------------------------------------------------
# Mock MCP Client
# ---------------------------------------------------------------------------

class MCPClient:
    """Mock Model Context Protocol client simulating external tool calls."""

    def __init__(self, tools: Optional[Dict[str, Callable]] = None):
        self.tools = tools or {}

    def register_tool(self, name: str, fn: Callable):
        self.tools[name] = fn

    def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self.tools:
            return {"error": f"Tool {tool_name} not found"}
        try:
            result = self.tools[tool_name](**params)
            return {"tool": tool_name, "result": result}
        except Exception as e:
            return {"tool": tool_name, "error": str(e)}

# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------

class MockLLM:
    """Deterministic mock LLM for generation and routing."""

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        if "decide" in prompt.lower() or "needs retrieval" in prompt.lower():
            if "who" in prompt.lower() or "what is" in prompt.lower() or "how" in prompt.lower():
                return "needs_retrieval: true"
            return "needs_retrieval: false"
        if "answer" in prompt.lower() or "generate" in prompt.lower():
            # Return a simple answer based on prompt context
            if "document" in prompt.lower():
                return "Based on the provided documents, the answer is concise and relevant."
            return "This is a generated answer."
        if "web search" in prompt.lower() or "ddg" in prompt.lower():
            return "Web search results: [Simulated result from DuckDuckGo]"
        return "Unknown prompt type."

    def classify(self, prompt: str) -> bool:
        return "true" in self.generate(prompt).lower()

# ---------------------------------------------------------------------------
# Agent State
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class AgentState:
    question: str = ""
    documents: List[str] = dataclasses.field(default_factory=list)
    answer: str = ""
    needs_retrieval: bool = True
    use_ddg: bool = False
    web_results: List[str] = dataclasses.field(default_factory=list)
    steps: List[str] = dataclasses.field(default_factory=list)

# ---------------------------------------------------------------------------
# Graph Nodes
# ---------------------------------------------------------------------------

class AgenticRAGGraph:
    """LangGraph-style workflow: decide -> retrieve -> generate -> web_search -> regenerate."""

    def __init__(self, vector_store: VectorStore, mcp: MCPClient, llm: Optional[MockLLM] = None):
        self.vector_store = vector_store
        self.mcp = mcp
        self.llm = llm or MockLLM()
        self.chunker = Chunker()

    def build_graph(self) -> Callable[[AgentState], AgentState]:
        def run(state: AgentState) -> AgentState:
            state = self.decide_node(state)
            if state.needs_retrieval:
                state = self.retrieve_node(state)
            if state.use_ddg:
                state = self.web_search_node(state)
            state = self.generate_node(state)
            return state
        return run

    def decide_node(self, state: AgentState) -> AgentState:
        prompt = (
            f"Question: {state.question}\n"
            "Decide whether this question needs document retrieval. "
            "Respond with 'needs_retrieval: true' or 'needs_retrieval: false'."
        )
        raw = self.llm.generate(prompt, max_tokens=32)
        state.needs_retrieval = "true" in raw.lower()
        state.steps.append(f"decide: needs_retrieval={state.needs_retrieval}")
        return state

    def retrieve_node(self, state: AgentState) -> AgentState:
        chunks = self.vector_store.search(state.question, k=5)
        state.documents = [c.content for c in chunks]
        state.steps.append(f"retrieve: found {len(chunks)} chunks")
        # If few documents, trigger web search
        if len(chunks) < 2:
            state.use_ddg = True
        return state

    def web_search_node(self, state: AgentState) -> AgentState:
        result = self.mcp.call_tool("web_search", {"query": state.question})
        state.web_results = [str(result.get("result", "No result"))]
        state.steps.append("web_search: executed via MCP")
        return state

    def generate_node(self, state: AgentState) -> AgentState:
        context = "\n".join(state.documents + state.web_results)
        prompt = (
            f"Question: {state.question}\n"
            f"Context: {context}\n"
            "Generate a concise answer based on the context."
        )
        state.answer = self.llm.generate(prompt, max_tokens=256)
        state.steps.append("generate: produced answer")
        return state

    def run(self, question: str, use_ddg: bool = False) -> AgentState:
        state = AgentState(question=question, use_ddg=use_ddg)
        graph = self.build_graph()
        return graph(state)

# ---------------------------------------------------------------------------
# Hybrid Retriever
# ---------------------------------------------------------------------------

class HybridRetriever:
    """Combines vector + web results."""

    def __init__(self, vector_store: VectorStore, mcp: MCPClient):
        self.vector_store = vector_store
        self.mcp = mcp

    def retrieve(self, query: str, k: int = 5, use_web: bool = False) -> List[str]:
        chunks = self.vector_store.search(query, k=k)
        results = [c.content for c in chunks]
        if use_web:
            web = self.mcp.call_tool("web_search", {"query": query})
            results.append(str(web.get("result", "")))
        return results

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

def _test_embedding():
    emb = HashEmbedding(dim=64)
    v1 = emb.embed("hello world")
    v2 = emb.embed("hello world")
    assert abs(sum(v1) - sum(v2)) < 1e-9
    assert len(v1) == 64
    print("[PASS] hash embedding")

def _test_chunking():
    chunker = Chunker(max_chunk_size=100, overlap=10)
    text = "This is sentence one. This is sentence two. This is sentence three. This is sentence four."
    chunks = chunker.chunk(text, "doc1")
    assert len(chunks) > 0
    assert all(len(c.content) <= 120 for c in chunks)
    print("[PASS] chunking")

def _test_vector_store():
    store = VectorStore(dim=64)
    chunker = Chunker()
    chunks = chunker.chunk("The sky is blue. The sun is bright.", "doc1")
    store.add_documents(chunks)
    results = store.search("sky color", k=2)
    assert len(results) > 0
    print("[PASS] vector store")

def _test_mcp():
    mcp = MCPClient()
    mcp.register_tool("calculator", lambda a, b: a + b)
    r = mcp.call_tool("calculator", {"a": 2, "b": 3})
    assert r["result"] == 5
    print("[PASS] mcp client")

def _test_graph():
    store = VectorStore(dim=64)
    chunker = Chunker()
    store.add_documents(chunker.chunk("Python is a programming language. It is used for AI.", "doc1"))
    store.add_documents(chunker.chunk("The capital of France is Paris. It is known for the Eiffel Tower.", "doc2"))
    mcp = MCPClient()
    mcp.register_tool("web_search", lambda query: f"Web result for {query}")
    graph = AgenticRAGGraph(store, mcp)
    state = graph.run("What is Python?", use_ddg=False)
    assert state.answer
    assert state.steps
    print("[PASS] agentic rag graph")

def _test_hybrid_retriever():
    store = VectorStore(dim=64)
    chunker = Chunker()
    store.add_documents(chunker.chunk("Document about machine learning.", "doc1"))
    mcp = MCPClient()
    mcp.register_tool("web_search", lambda query: f"Web: {query}")
    ret = HybridRetriever(store, mcp)
    results = ret.retrieve("machine learning", k=3, use_web=True)
    assert len(results) >= 2
    print("[PASS] hybrid retriever")

if __name__ == "__main__":
    _test_embedding()
    _test_chunking()
    _test_vector_store()
    _test_mcp()
    _test_graph()
    _test_hybrid_retriever()
    print("\n[OK] agentic_rag_native.py — all 6 tests passed")
