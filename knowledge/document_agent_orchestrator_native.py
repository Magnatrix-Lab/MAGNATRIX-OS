"""
native_document_agent.py — Multi-document routing agent.

Architectural patterns extracted from AyushParikh/LlamaIndex-Agent:
- Document classification to determine which handler should process a query.
- Specialized handlers (finance, legal, tech, general) with distinct retrieval strategies.
- Orchestrator pattern routing queries to the right handler and aggregating results.
- Fallback cascading when primary handler returns low-confidence.
- In-memory vector store per document domain.

Pure Python ≥3.9, stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Shared vector store (same pattern as other knowledge modules)
# ---------------------------------------------------------------------------

@dataclass
class DocumentChunk:
    id: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class NativeChunkStore:
    """Domain-scoped in-memory vector store."""

    def __init__(self) -> None:
        self.chunks: Dict[str, DocumentChunk] = {}

    def add(self, chunk: DocumentChunk) -> None:
        self.chunks[chunk.id] = chunk

    def search(self, query_emb: List[float], k: int = 4) -> List[DocumentChunk]:
        scored: List[Tuple[float, DocumentChunk]] = []
        for c in self.chunks.values():
            if c.embedding is None:
                continue
            sim = self._cosine(query_emb, c.embedding)
            scored.append((sim, c))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [c for _, c in scored[:k]]

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb + 1e-9)

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

class DocDomain(Enum):
    FINANCE = auto(); LEGAL = auto(); TECH = auto(); GENERAL = auto()

class NativeDocumentClassifier:
    """Keyword-based classifier for routing."""

    KEYWORDS: Dict[DocDomain, List[str]] = {
        DocDomain.FINANCE: ["revenue", "profit", "stock", "investment", "market", "price", "financial", "earnings"],
        DocDomain.LEGAL: ["contract", "clause", "liability", "regulation", "compliance", "court", "law"],
        DocDomain.TECH: ["software", "api", "database", "cloud", "algorithm", "python", "code", "server"],
    }

    def classify(self, query: str) -> DocDomain:
        lowered = query.lower()
        scores: Dict[DocDomain, int] = {d: 0 for d in DocDomain}
        for domain, words in self.KEYWORDS.items():
            scores[domain] = sum(1 for w in words if w in lowered)
        best = max(scores, key=lambda d: scores[d])
        return best if scores[best] > 0 else DocDomain.GENERAL

# ---------------------------------------------------------------------------
# Specialized Handlers
# ---------------------------------------------------------------------------

class NativeDomainHandler:
    """Base handler interface."""

    def __init__(
        self,
        domain: DocDomain,
        store: NativeChunkStore,
        embed_fn: Callable[[str], List[float]],
        llm_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.domain = domain
        self.store = store
        self.embed_fn = embed_fn
        self.llm_fn = llm_fn

    def handle(self, query: str) -> Tuple[str, float]:
        """Return (answer, confidence)."""
        q_emb = self.embed_fn(query)
        chunks = self.store.search(q_emb, k=4)
        if not chunks:
            return (f"No relevant {self.domain.name} information found.", 0.0)
        context = "\n".join(c.text for c in chunks)
        confidence = self._score_confidence(query, chunks)
        if self.llm_fn:
            prompt = f"You are a {self.domain.name} specialist. Answer using only the context.\n\nContext:\n{context}\n\nQuestion: {query}\nAnswer:"
            return (self.llm_fn(prompt), confidence)
        return (chunks[0].text, confidence)

    def _score_confidence(self, query: str, chunks: List[DocumentChunk]) -> float:
        q_tokens = set(query.lower().split())
        best = 0.0
        for c in chunks:
            c_tokens = set(c.text.lower().split())
            overlap = len(q_tokens & c_tokens) / (len(q_tokens) + 1e-9)
            best = max(best, overlap)
        return min(best, 1.0)

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class NativeDocumentOrchestrator:
    """
    Routes queries to domain-specific handlers.
    Falls back to next-best domain if confidence is low.
    """

    CONFIDENCE_THRESHOLD = 0.3

    def __init__(
        self,
        embed_fn: Callable[[str], List[float]],
        llm_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.classifier = NativeDocumentClassifier()
        self.embed_fn = embed_fn
        self.llm_fn = llm_fn
        self.handlers: Dict[DocDomain, NativeDomainHandler] = {}
        self.fallback_order = [DocDomain.TECH, DocDomain.FINANCE, DocDomain.LEGAL, DocDomain.GENERAL]

    def register(self, domain: DocDomain, chunks: List[DocumentChunk]) -> None:
        store = NativeChunkStore()
        for c in chunks:
            if c.embedding is None:
                c.embedding = self.embed_fn(c.text)
            store.add(c)
        self.handlers[domain] = NativeDomainHandler(domain, store, self.embed_fn, self.llm_fn)

    def run(self, query: str) -> Tuple[str, DocDomain, float]:
        """Route and return (answer, domain_used, confidence)."""
        primary = self.classifier.classify(query)
        answer, conf = self._try_handle(query, primary)
        if conf >= self.CONFIDENCE_THRESHOLD:
            return (answer, primary, conf)
        # Fallback cascade
        for domain in self.fallback_order:
            if domain == primary or domain not in self.handlers:
                continue
            answer, conf = self._try_handle(query, domain)
            if conf >= self.CONFIDENCE_THRESHOLD:
                return (answer, domain, conf)
        # Last resort: general or primary whatever it is
        return (answer, primary, conf)

    def execute(self, query: str) -> str:
        """Run and return answer string only."""
        answer, _domain, _conf = self.run(query)
        return answer

    def _try_handle(self, query: str, domain: DocDomain) -> Tuple[str, float]:
        if domain in self.handlers:
            return self.handlers[domain].handle(query)
        return ("No handler registered for this domain.", 0.0)

# ---------------------------------------------------------------------------
# Multi-document routing agent (higher-level facade)
# ---------------------------------------------------------------------------

class NativeDocumentAgent:
    """
    Multi-document routing agent.

    Usage:
        agent = NativeDocumentAgent(embed_fn, llm_fn)
        agent.add_document("10-K report", finance_chunks)
        agent.add_document("API docs", tech_chunks)
        answer = agent.query("What was the revenue?")
    """

    def __init__(
        self,
        embed_fn: Callable[[str], List[float]],
        llm_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.orchestrator = NativeDocumentOrchestrator(embed_fn, llm_fn)
        self.documents: Dict[str, Tuple[DocDomain, List[DocumentChunk]]] = {}

    def add_document(self, name: str, domain: DocDomain, chunks: List[DocumentChunk]) -> None:
        """Add a named document under a domain."""
        self.documents[name] = (domain, chunks)
        self.orchestrator.register(domain, chunks)

    def query(self, question: str) -> Dict[str, Any]:
        """Query and return structured result."""
        answer, domain, confidence = self.orchestrator.run(question)
        return {
            "answer": answer,
            "domain": domain.name,
            "confidence": round(confidence, 3),
            "documents_considered": list(self.documents.keys()),
        }

    def run(self, question: str) -> Dict[str, Any]:
        """Alias for query."""
        return self.query(question)

    def execute(self, question: str) -> str:
        """Return plain answer string."""
        return self.query(question)["answer"]

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    def mock_embed(text: str) -> List[float]:
        vec = [0.0] * 24
        for ch in text.lower():
            vec[ord(ch) % 24] += 1.0
        return vec

    def mock_llm(prompt: str) -> str:
        if "FINANCE" in prompt:
            return "The revenue increased by 15% year-over-year."
        if "TECH" in prompt:
            return "The API supports REST and GraphQL endpoints."
        if "LEGAL" in prompt:
            return "Clause 3.2 governs liability limitations."
        return "Here is the information you requested."

    agent = NativeDocumentAgent(mock_embed, mock_llm)

    finance_chunks = [
        DocumentChunk("f1", "Q3 revenue was 120 million, up 15% YoY."),
        DocumentChunk("f2", "Operating margin expanded to 22%."),
        DocumentChunk("f3", "Stock repurchase program authorized for 500 million."),
    ]

    tech_chunks = [
        DocumentChunk("t1", "The API uses OAuth 2.0 authentication."),
        DocumentChunk("t2", "GraphQL queries are supported alongside REST."),
        DocumentChunk("t3", "Rate limit: 1000 requests per minute."),
    ]

    legal_chunks = [
        DocumentChunk("l1", "Clause 3.2 limits liability to direct damages only."),
        DocumentChunk("l2", "Arbitration shall be held in Delaware."),
    ]

    agent.add_document("Q3 Earnings", DocDomain.FINANCE, finance_chunks)
    agent.add_document("API Documentation", DocDomain.TECH, tech_chunks)
    agent.add_document("Service Agreement", DocDomain.LEGAL, legal_chunks)

    print("=== Demo 1: Finance query ===")
    r1 = agent.query("Q3 revenue was how much?")
    print(f"Answer: {r1['answer']}")
    print(f"Domain: {r1['domain']} | Confidence: {r1['confidence']}")
    print()

    print("=== Demo 2: Tech query ===")
    r2 = agent.query("API uses what authentication?")
    print(f"Answer: {r2['answer']}")
    print(f"Domain: {r2['domain']} | Confidence: {r2['confidence']}")
    print()

    print("=== Demo 3: Legal query ===")
    r3 = agent.query("Arbitration shall be held where?")
    print(f"Answer: {r3['answer']}")
    print(f"Domain: {r3['domain']} | Confidence: {r3['confidence']}")
    print()

    print("=== Demo 4: Fallback query ===")
    r4 = agent.query("Explain machine learning")
    print(f"Answer: {r4['answer']}")
    print(f"Domain: {r4['domain']} | Confidence: {r4['confidence']}")
    print()

    print("All demos completed.")
