"""
native_llamaindex_rag.py — Document agents with ingestion, indexing, query routing.

Architectural patterns extracted from AyushParikh/LlamaIndex-Agent:
- Document ingestion pipeline with transformation hooks.
- In-memory vector index with node-level granularity.
- Query router selecting between vector search, summary, and list-based tools.
- Response synthesizer combining retrieved nodes into coherent answers.
- Native callback `llm_fn` for generation to avoid external dependencies.

Pure Python ≥3.9, stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# In-memory vector store (same pattern as agentic_rag, reusable)
# ---------------------------------------------------------------------------

@dataclass
class TextNode:
    id_: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, List[str]] = field(default_factory=dict)

class NativeVectorIndex:
    """Simple in-memory index with cosine similarity."""

    def __init__(self) -> None:
        self.nodes: Dict[str, TextNode] = {}

    def add(self, node: TextNode) -> None:
        self.nodes[node.id_] = node

    def search(
        self,
        query_embedding: List[float],
        k: int = 4,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[TextNode]:
        scored: List[Tuple[float, TextNode]] = []
        for node in self.nodes.values():
            if node.embedding is None:
                continue
            if filters and not all(node.metadata.get(k) == v for k, v in filters.items()):
                continue
            sim = self._cosine(query_embedding, node.embedding)
            scored.append((sim, node))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [n for _, n in scored[:k]]

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb + 1e-9)

# ---------------------------------------------------------------------------
# Transformations
# ---------------------------------------------------------------------------

class NativeTransform:
    """Base for ingestion transforms."""

    def __call__(self, nodes: List[TextNode]) -> List[TextNode]:
        return nodes

class SentenceSplitter(NativeTransform):
    """Naïve sentence splitting."""

    def __init__(self, chunk_size: int = 3) -> None:
        self.chunk_size = chunk_size

    def __call__(self, nodes: List[TextNode]) -> List[TextNode]:
        out: List[TextNode] = []
        for node in nodes:
            sentences = [s.strip() for s in node.text.split(".") if s.strip()]
            for i in range(0, len(sentences), self.chunk_size):
                chunk_text = ". ".join(sentences[i:i + self.chunk_size]) + "."
                out.append(TextNode(
                    id_=f"{node.id_}_{i}",
                    text=chunk_text,
                    metadata=dict(node.metadata),
                ))
        return out

class EmbedTransform(NativeTransform):
    """Attach embeddings via callback."""

    def __init__(self, embed_fn: Callable[[str], List[float]]) -> None:
        self.embed_fn = embed_fn

    def __call__(self, nodes: List[TextNode]) -> List[TextNode]:
        for n in nodes:
            n.embedding = self.embed_fn(n.text)
        return nodes

# ---------------------------------------------------------------------------
# Ingestion Pipeline
# ---------------------------------------------------------------------------

class NativeIngestionPipeline:
    """Load → Split → Embed → Index."""

    def __init__(
        self,
        index: NativeVectorIndex,
        transforms: List[NativeTransform],
    ) -> None:
        self.index = index
        self.transforms = transforms

    def run(self, raw_nodes: List[TextNode]) -> None:
        nodes = raw_nodes
        for tx in self.transforms:
            nodes = tx(nodes)
        for node in nodes:
            self.index.add(node)

# ---------------------------------------------------------------------------
# Query Router
# ---------------------------------------------------------------------------

class QueryType(Enum):
    VECTOR = auto(); SUMMARY = auto(); LIST = auto()

class NativeQueryRouter:
    """Route queries to appropriate tool based on keyword heuristics."""

    def __init__(self, llm_fn: Optional[Callable[[str], str]] = None) -> None:
        self.llm_fn = llm_fn

    def classify(self, query: str) -> QueryType:
        lowered = query.lower()
        if any(w in lowered for w in ("summarize", "summary", "overview", "tl;dr")):
            return QueryType.SUMMARY
        if any(w in lowered for w in ("list", "enumerate", "all", "every")):
            return QueryType.LIST
        return QueryType.VECTOR

# ---------------------------------------------------------------------------
# Response Synthesizer
# ---------------------------------------------------------------------------

class NativeResponseSynthesizer:
    """Combine nodes into a coherent answer."""

    def __init__(self, llm_fn: Optional[Callable[[str], str]] = None) -> None:
        self.llm_fn = llm_fn

    def synthesize(self, query: str, nodes: List[TextNode]) -> str:
        if not nodes:
            return "No relevant information found."
        context = "\n\n".join(n.text for n in nodes)
        if self.llm_fn:
            prompt = f"Given the context below, answer the question concisely.\n\nContext:\n{context}\n\nQuestion: {query}\nAnswer:"
            return self.llm_fn(prompt)
        return f"Top match: {nodes[0].text}"

# ---------------------------------------------------------------------------
# Document Agent (main facade)
# ---------------------------------------------------------------------------

class NativeLlamaIndexRAG:
    """
    End-to-end document agent.

    Provides:
    - ingest(docs)   → pipeline through transforms into index
    - query(text)    → route → retrieve → synthesize → answer
    """

    def __init__(
        self,
        embed_fn: Callable[[str], List[float]],
        llm_fn: Optional[Callable[[str], str]] = None,
        chunk_size: int = 3,
    ) -> None:
        self.index = NativeVectorIndex()
        self.embed_fn = embed_fn
        self.llm_fn = llm_fn
        self.pipeline = NativeIngestionPipeline(
            self.index,
            [SentenceSplitter(chunk_size), EmbedTransform(embed_fn)],
        )
        self.router = NativeQueryRouter(llm_fn)
        self.synthesizer = NativeResponseSynthesizer(llm_fn)

    def run(self, documents: List[TextNode]) -> None:
        """Ingest documents."""
        self.pipeline.run(documents)

    def execute(self, query: str) -> str:
        """Alias for query."""
        return self.query(query)

    def query(self, query: str) -> str:
        qtype = self.router.classify(query)

        if qtype == QueryType.VECTOR:
            q_emb = self.embed_fn(query)
            nodes = self.index.search(q_emb, k=4)
            return self.synthesizer.synthesize(query, nodes)

        if qtype == QueryType.SUMMARY:
            all_nodes = list(self.index.nodes.values())
            # Return top-k by length as a proxy for importance
            all_nodes.sort(key=lambda n: len(n.text), reverse=True)
            return self.synthesizer.synthesize(query, all_nodes[:4])

        if qtype == QueryType.LIST:
            all_nodes = list(self.index.nodes.values())
            # Enumerate short snippets
            return self.synthesizer.synthesize(query, all_nodes[:8])

        return "Unhandled query type."

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    def mock_embed(text: str) -> List[float]:
        vec = [0.0] * 32
        for ch in text.lower():
            vec[ord(ch) % 32] += 1.0
        return vec

    def mock_llm(prompt: str) -> str:
        if "python" in prompt.lower():
            return "Python is a high-level programming language."
        if "openai" in prompt.lower():
            return "OpenAI is an AI research company."
        return "Based on the context, here is the answer."

    rag = NativeLlamaIndexRAG(mock_embed, mock_llm, chunk_size=2)

    docs = [
        TextNode("doc1", "Python is a high-level programming language. It supports multiple paradigms. Python was created by Guido van Rossum."),
        TextNode("doc2", "OpenAI is an artificial intelligence research laboratory. It was founded in 2015. OpenAI created GPT models."),
        TextNode("doc3", "Machine learning is a subset of artificial intelligence. Deep learning is a subset of machine learning."),
    ]

    print("=== Ingesting ===")
    rag.run(docs)
    print(f"Indexed {len(rag.index.nodes)} nodes")
    print()

    print("=== Demo 1: Vector query ===")
    a1 = rag.query("Who created Python?")
    print(f"Answer: {a1}")
    print()

    print("=== Demo 2: Summary query ===")
    a2 = rag.query("Summarize what OpenAI does.")
    print(f"Answer: {a2}")
    print()

    print("=== Demo 3: List query ===")
    a3 = rag.query("List all topics mentioned.")
    print(f"Answer: {a3}")
    print()

    print("All demos completed.")
