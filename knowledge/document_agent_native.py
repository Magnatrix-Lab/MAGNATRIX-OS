# document_agent_native.py
# AMATI-PELAJARI-TIRU: LlamaIndex Multi-Document Agent Pattern
# Meta-agent routes queries to per-document agents. Pure Python, zero deps.

from __future__ import annotations
import re, json, math, hashlib, dataclasses, typing, os
from typing import List, Dict, Optional, Tuple, Any

# ---------------------------------------------------------------------------
# Reusable HashEmbedding (same as agentic_rag_native)
# ---------------------------------------------------------------------------

class HashEmbedding:
    def __init__(self, dim: int = 128, seed: int = 42):
        self.dim = dim
        self.seed = seed

    def _hash_vector(self, text: str, component: int) -> float:
        h = hashlib.blake2b(key=component.to_bytes(4, "big", signed=True), digest_size=32)
        h.update(text.encode("utf-8"))
        val = int.from_bytes(h.digest(), "big")
        return (val / (2 ** 256)) * 2 - 1

    def embed(self, text: str) -> List[float]:
        vec = [self._hash_vector(text, i) for i in range(self.dim)]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

# ---------------------------------------------------------------------------
# Document Chunk & Document Loading
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class DocumentChunk:
    id: str
    content: str
    embedding: List[float]
    doc_id: str
    metadata: Dict[str, Any]

class Chunker:
    def __init__(self, max_chunk_size: int = 512, overlap: int = 64):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk(self, text: str, doc_id: str, embedder: HashEmbedding) -> List[DocumentChunk]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        buffer = ""
        chunk_idx = 0
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

class DocumentLoader:
    """Load .txt and .md files."""

    def load(self, path: str) -> Tuple[str, Dict[str, Any]]:
        if not os.path.exists(path):
            return "", {"error": f"File not found: {path}"}
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        meta = {"path": path, "size": len(text), "ext": os.path.splitext(path)[1]}
        return text, meta

    def load_directory(self, dir_path: str) -> List[Tuple[str, Dict[str, Any]]]:
        results = []
        if not os.path.isdir(dir_path):
            return results
        for fname in os.listdir(dir_path):
            if fname.endswith(".txt") or fname.endswith(".md"):
                p = os.path.join(dir_path, fname)
                text, meta = self.load(p)
                meta["filename"] = fname
                results.append((text, meta))
        return results

# ---------------------------------------------------------------------------
# Vector Index (per-document and global)
# ---------------------------------------------------------------------------

class VectorIndex:
    def __init__(self, dim: int = 128):
        self.dim = dim
        self.embedder = HashEmbedding(dim=dim)
        self.chunks: List[DocumentChunk] = []

    def add(self, chunks: List[DocumentChunk]):
        self.chunks.extend(chunks)

    def search(self, query: str, k: int = 5) -> List[DocumentChunk]:
        qvec = self.embedder.embed(query)
        scored = [(self.embedder.cosine_similarity(qvec, c.embedding), c) for c in self.chunks]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:k]]

    def clear(self):
        self.chunks.clear()

# ---------------------------------------------------------------------------
# BM25-style Reranker
# ---------------------------------------------------------------------------

class BM25Reranker:
    """Simple BM25-inspired scoring for re-ranking."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'[a-zA-Z]+', text.lower())

    def score(self, query: str, chunk: DocumentChunk) -> float:
        q_tokens = self._tokenize(query)
        c_tokens = self._tokenize(chunk.content)
        if not q_tokens or not c_tokens:
            return 0.0
        # Simple term frequency scoring
        score = 0.0
        avg_len = 200.0  # assumed average chunk length
        for tok in q_tokens:
            tf = c_tokens.count(tok)
            if tf == 0:
                continue
            idf = 1.0  # simplified idf
            denom = tf + self.k1 * (1 - self.b + self.b * (len(c_tokens) / avg_len))
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    def rerank(self, query: str, chunks: List[DocumentChunk]) -> List[Tuple[float, DocumentChunk]]:
        scored = [(self.score(query, c), c) for c in chunks]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------

class MockLLM:
    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        if "summarize" in prompt.lower():
            return "Summary: The document discusses key topics concisely."
        if "answer" in prompt.lower():
            return "Answer: Based on the document content, the answer is straightforward."
        return "Generated response."

# ---------------------------------------------------------------------------
# Document Agent (one per document)
# ---------------------------------------------------------------------------

class DocumentAgent:
    """Per-document agent with embedded query capability."""

    def __init__(self, doc_id: str, chunks: List[DocumentChunk], llm: Optional[MockLLM] = None):
        self.doc_id = doc_id
        self.chunks = chunks
        self.llm = llm or MockLLM()
        self.index = VectorIndex(dim=128)
        self.index.add(chunks)

    def query(self, question: str) -> str:
        results = self.index.search(question, k=3)
        context = "\n".join(c.content for c in results)
        prompt = (
            f"Document: {self.doc_id}\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer concisely based on the document."
        )
        return self.llm.generate(prompt, max_tokens=256)

    def summarize(self) -> str:
        all_text = "\n".join(c.content for c in self.chunks)[:2000]
        prompt = f"Summarize the following document:\n{all_text}\n"
        return self.llm.generate(prompt, max_tokens=256)

    def get_tool_description(self) -> Dict[str, Any]:
        return {
            "name": f"query_{self.doc_id}",
            "description": f"Query document {self.doc_id}",
            "parameters": {"question": "string"}
        }

# ---------------------------------------------------------------------------
# Meta Agent (top-level router)
# ---------------------------------------------------------------------------

class MetaAgent:
    """Routes queries to relevant document agents."""

    def __init__(self, llm: Optional[MockLLM] = None):
        self.llm = llm or MockLLM()
        self.agents: Dict[str, DocumentAgent] = {}
        self.global_index = VectorIndex(dim=128)
        self.reranker = BM25Reranker()

    def register_agent(self, agent: DocumentAgent):
        self.agents[agent.doc_id] = agent
        self.global_index.add(agent.chunks)

    def route(self, query: str) -> List[str]:
        """Select relevant document agents using global index + heuristics."""
        global_results = self.global_index.search(query, k=10)
        # Aggregate by doc_id
        doc_scores: Dict[str, float] = {}
        for chunk in global_results:
            doc_scores[chunk.doc_id] = doc_scores.get(chunk.doc_id, 0.0) + 1.0
        # Rerank with BM25 on top chunks per doc
        for doc_id, agent in self.agents.items():
            chunks = agent.index.search(query, k=5)
            scored = self.reranker.rerank(query, chunks)
            if scored:
                doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + scored[0][0]
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        # Return top 3 or all if few
        return [doc_id for doc_id, _ in sorted_docs[:3]]

    def query(self, question: str) -> str:
        relevant = self.route(question)
        answers = []
        for doc_id in relevant:
            agent = self.agents[doc_id]
            answer = agent.query(question)
            answers.append((doc_id, answer))
        return self.synthesize(question, answers)

    def synthesize(self, question: str, answers: List[Tuple[str, str]]) -> str:
        context = "\n\n".join(f"[{doc_id}] {ans}" for doc_id, ans in answers)
        prompt = (
            f"Question: {question}\n"
            f"Answers from documents:\n{context}\n\n"
            "Synthesize a single coherent answer."
        )
        return self.llm.generate(prompt, max_tokens=256)

# ---------------------------------------------------------------------------
# Query Engine
# ---------------------------------------------------------------------------

class QueryEngine:
    """High-level query interface combining index + reranker + synthesis."""

    def __init__(self, meta_agent: MetaAgent):
        self.meta = meta_agent

    def query(self, question: str) -> Dict[str, Any]:
        answer = self.meta.query(question)
        relevant_docs = self.meta.route(question)
        return {
            "question": question,
            "answer": answer,
            "relevant_documents": relevant_docs,
        }

# ---------------------------------------------------------------------------
# Synthesizer (standalone)
# ---------------------------------------------------------------------------

class Synthesizer:
    """Merges multiple document agent responses into a coherent answer."""

    def __init__(self, llm: Optional[MockLLM] = None):
        self.llm = llm or MockLLM()

    def merge(self, question: str, answers: List[Tuple[str, str]]) -> str:
        context = "\n\n".join(f"Doc {doc_id}: {ans}" for doc_id, ans in answers)
        prompt = (
            f"Question: {question}\n"
            f"Document answers:\n{context}\n\n"
            "Provide a unified, coherent answer. Remove contradictions."
        )
        return self.llm.generate(prompt, max_tokens=256)

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

def _test_chunk_and_index():
    embedder = HashEmbedding(dim=64)
    chunker = Chunker(max_chunk_size=200, overlap=20)
    text = "Alpha is a company. It builds software. Beta is a rival. It builds hardware."
    chunks = chunker.chunk(text, "doc1", embedder)
    assert len(chunks) > 0
    idx = VectorIndex(dim=64)
    idx.add(chunks)
    res = idx.search("software", k=2)
    assert len(res) > 0
    print("[PASS] chunk and index")

def _test_document_agent():
    chunker = Chunker(max_chunk_size=200, overlap=20)
    embedder = HashEmbedding(dim=64)
    chunks = chunker.chunk("Paris is the capital of France. The Eiffel Tower is in Paris.", "france", embedder)
    agent = DocumentAgent("france", chunks)
    ans = agent.query("capital of France")
    assert "France" in ans or "Paris" in ans or "Answer" in ans
    print("[PASS] document agent")

def _test_meta_agent():
    chunker = Chunker(max_chunk_size=200, overlap=20)
    embedder = HashEmbedding(dim=64)
    a1 = DocumentAgent("doc1", chunker.chunk("Python is great for AI. It has many libraries.", "doc1", embedder))
    a2 = DocumentAgent("doc2", chunker.chunk("Rust is fast and safe. It uses ownership.", "doc2", embedder))
    meta = MetaAgent()
    meta.register_agent(a1)
    meta.register_agent(a2)
    routed = meta.route("Python libraries")
    assert "doc1" in routed
    print("[PASS] meta agent routing")

def _test_reranker():
    chunker = Chunker(max_chunk_size=200, overlap=20)
    embedder = HashEmbedding(dim=64)
    chunks = chunker.chunk("Machine learning is a subset of AI. Deep learning is part of ML.", "ml", embedder)
    reranker = BM25Reranker()
    scored = reranker.rerank("deep learning", chunks)
    assert len(scored) > 0
    print("[PASS] bm25 reranker")

def _test_query_engine():
    chunker = Chunker(max_chunk_size=200, overlap=20)
    embedder = HashEmbedding(dim=64)
    a1 = DocumentAgent("doc1", chunker.chunk("Python is a programming language. It is used for web development.", "doc1", embedder))
    a2 = DocumentAgent("doc2", chunker.chunk("JavaScript runs in browsers. It is used for frontend.", "doc2", embedder))
    meta = MetaAgent()
    meta.register_agent(a1)
    meta.register_agent(a2)
    engine = QueryEngine(meta)
    result = engine.query("web development language")
    assert "answer" in result
    assert result["relevant_documents"]
    print("[PASS] query engine")

def _test_synthesizer():
    synth = Synthesizer()
    merged = synth.merge("What is AI?", [("doc1", "AI is intelligence in machines."), ("doc2", "AI solves complex problems.")])
    assert merged
    print("[PASS] synthesizer")

if __name__ == "__main__":
    _test_chunk_and_index()
    _test_document_agent()
    _test_meta_agent()
    _test_reranker()
    _test_query_engine()
    _test_synthesizer()
    print("\n[OK] document_agent_native.py — all 6 tests passed")
