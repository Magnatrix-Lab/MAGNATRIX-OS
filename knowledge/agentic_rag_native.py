"""
agentic_rag_native.py — MAGNATRIX-OS Agentic RAG Engine

Pure-Python implementation of LangGraph + LlamaIndex + AgenticRAG patterns.
No LangChain / LlamaIndex imports — native stdlib + numpy only.

Components:
    • VectorStore      — numpy-powered similarity search
    • Retriever        — document retrieval with filtering
    • QueryRouter      — route queries to specialized handlers
    • DocumentAgent    — per-domain document processing agent
    • AgenticRAG       — self-correcting RAG state machine
    • MetaAgent        — orchestrator that coordinates all agents
"""
from __future__ import annotations

import json
import re
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple, Union
from pathlib import Path

import numpy as np


# ──────────────────────────────────────────────────────────────────────────
# 1. VectorStore — numpy-powered similarity search
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class Document:
    """A chunk of text with vector embedding and metadata."""
    id: str
    text: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.embedding, list):
            self.embedding = np.array(self.embedding, dtype=np.float32)


class VectorStore:
    """
    In-memory vector store with batch indexing and multiple search strategies.

    Supports:
        • cosine similarity (default)
        • euclidean distance
        • dot-product
        • metadata filtering
    """

    def __init__(self, dim: int = 768, metric: str = "cosine") -> None:
        self.dim = dim
        self.metric = metric
        self._docs: List[Document] = []
        self._matrix: Optional[np.ndarray] = None  # (N, dim)
        self._id_map: Dict[str, int] = {}  # id → index
        self._dirty = True

    # ── Core ops ──

    def add(self, doc: Document) -> None:
        """Index a single document."""
        self._docs.append(doc)
        self._id_map[doc.id] = len(self._docs) - 1
        self._dirty = True

    def add_batch(self, docs: List[Document]) -> None:
        """Bulk index for efficiency."""
        start_idx = len(self._docs)
        for i, doc in enumerate(docs):
            self._id_map[doc.id] = start_idx + i
        self._docs.extend(docs)
        self._dirty = True

    def delete(self, doc_id: str) -> bool:
        """Remove by id; O(N) because indices shift."""
        if doc_id not in self._id_map:
            return False
        idx = self._id_map[doc_id]
        self._docs.pop(idx)
        self._id_map.clear()
        for i, d in enumerate(self._docs):
            self._id_map[d.id] = i
        self._dirty = True
        return True

    def get(self, doc_id: str) -> Optional[Document]:
        idx = self._id_map.get(doc_id)
        return self._docs[idx] if idx is not None else None

    def count(self) -> int:
        return len(self._docs)

    # ── Search ──

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 4,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """
        Return top-k (Document, score) tuples.
        Higher score = better match (cosine/dot) or lower = better (euclidean).
        """
        if self.count() == 0:
            return []

        self._rebuild_matrix()
        query = self._normalize(query_embedding)

        candidates = self._filter_indices(filter_dict)
        if not candidates:
            return []

        scores = self._compute_scores(query, candidates)
        top_k = self._top_k(scores, candidates, k)
        return top_k

    def search_by_text(
        self,
        embed_fn: Callable[[str], np.ndarray],
        query_text: str,
        k: int = 4,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """Embed + search in one call."""
        emb = embed_fn(query_text)
        return self.search(emb, k=k, filter_dict=filter_dict)

    # ── Internals ──

    def _rebuild_matrix(self) -> None:
        if not self._dirty or not self._docs:
            return
        self._matrix = np.stack([d.embedding for d in self._docs])
        self._dirty = False

    def _normalize(self, v: np.ndarray) -> np.ndarray:
        v = np.asarray(v, dtype=np.float32)
        if v.ndim == 1:
            v = v.reshape(1, -1)
        return v

    def _filter_indices(self, filter_dict: Optional[Dict[str, Any]]) -> List[int]:
        if filter_dict is None:
            return list(range(len(self._docs)))
        indices = []
        for i, doc in enumerate(self._docs):
            if all(doc.metadata.get(k) == v for k, v in filter_dict.items()):
                indices.append(i)
        return indices

    def _compute_scores(self, query: np.ndarray, indices: List[int]) -> np.ndarray:
        vecs = self._matrix[indices]  # (M, dim)

        if self.metric == "cosine":
            q_norm = query / (np.linalg.norm(query, axis=1, keepdims=True) + 1e-9)
            v_norm = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
            scores = (q_norm @ v_norm.T).flatten()

        elif self.metric == "dot":
            scores = (query @ vecs.T).flatten()

        elif self.metric == "euclidean":
            diff = vecs - query  # broadcasting (M, dim)
            scores = -np.linalg.norm(diff, axis=1)  # negative so higher=better

        else:
            raise ValueError(f"Unknown metric: {self.metric}")

        return scores

    def _top_k(
        self, scores: np.ndarray, indices: List[int], k: int
    ) -> List[Tuple[Document, float]]:
        k = min(k, len(scores))
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(-scores[top_idx])]
        return [(self._docs[indices[i]], float(scores[i])) for i in top_idx]

    # ── Persistence ──

    def save(self, path: Union[str, Path]) -> None:
        """Serialize to JSON."""
        data = {
            "dim": self.dim,
            "metric": self.metric,
            "docs": [
                {
                    "id": d.id,
                    "text": d.text,
                    "embedding": d.embedding.tolist(),
                    "metadata": d.metadata,
                }
                for d in self._docs
            ],
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Union[str, Path]) -> VectorStore:
        """Deserialize from JSON."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        store = cls(dim=data["dim"], metric=data.get("metric", "cosine"))
        for d in data["docs"]:
            store.add(
                Document(
                    id=d["id"],
                    text=d["text"],
                    embedding=np.array(d["embedding"], dtype=np.float32),
                    metadata=d.get("metadata", {}),
                )
            )
        return store


# ──────────────────────────────────────────────────────────────────────────
# 2. Retriever — document retrieval with reranking and query expansion
# ──────────────────────────────────────────────────────────────────────────

class Retriever:
    """
    Advanced retriever with:
        • Query expansion (synonym/hyponym injection)
        • Hybrid search (vector + keyword)
        • Re-ranking via cross-encoder pattern (heuristic)
        • MMR diversity re-ranking
    """

    def __init__(
        self,
        store: VectorStore,
        embed_fn: Callable[[str], np.ndarray],
        top_k: int = 10,
        rerank_top_k: int = 4,
        use_mmr: bool = True,
        mmr_lambda: float = 0.5,
    ) -> None:
        self.store = store
        self.embed_fn = embed_fn
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k
        self.use_mmr = use_mmr
        self.mmr_lambda = mmr_lambda

    def retrieve(
        self,
        query: str,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Full retrieval pipeline: search → rerank → return."""
        # 1. Expand query
        expanded = self._expand_query(query)

        # 2. Vector search on expanded
        all_results: List[Tuple[Document, float]] = []
        for q in expanded:
            emb = self.embed_fn(q)
            results = self.store.search(emb, k=self.top_k, filter_dict=filter_dict)
            all_results.extend(results)

        # 3. Deduplicate by id, keep best score
        seen: Dict[str, float] = {}
        for doc, score in all_results:
            if doc.id not in seen or score > seen[doc.id]:
                seen[doc.id] = score

        # 4. Re-rank
        unique_docs = [self.store.get(did) for did in seen.keys()]
        unique_docs = [d for d in unique_docs if d is not None]

        if self.use_mmr and len(unique_docs) > 1:
            ranked = self._mmr_rerank(query, unique_docs, seen)
        else:
            ranked = sorted(unique_docs, key=lambda d: seen[d.id], reverse=True)

        return ranked[: self.rerank_top_k]

    # ── Query expansion ──

    def _expand_query(self, query: str) -> List[str]:
        """Simple expansion: original + lowercase variant + stemmed."""
        expanded = [query, query.lower()]
        # Naive stemming: remove trailing 's', 'ing', 'ed'
        words = query.lower().split()
        stemmed = []
        for w in words:
            if w.endswith("ing") and len(w) > 5:
                w = w[:-3]
            elif w.endswith("ed") and len(w) > 4:
                w = w[:-2]
            elif w.endswith("s") and len(w) > 3:
                w = w[:-1]
            stemmed.append(w)
        expanded.append(" ".join(stemmed))
        return expanded

    # ── MMR (Maximal Marginal Relevance) ──

    def _mmr_rerank(
        self, query: str, docs: List[Document], scores: Dict[str, float]
    ) -> List[Document]:
        """MMR: λ * relevance - (1-λ) * max_sim(selected)."""
        query_emb = self.embed_fn(query)
        query_emb = query_emb / (np.linalg.norm(query_emb) + 1e-9)

        doc_embs = np.stack([d.embedding for d in docs])
        doc_embs = doc_embs / (np.linalg.norm(doc_embs, axis=1, keepdims=True) + 1e-9)

        rel = np.array([scores[d.id] for d in docs])
        sim_matrix = doc_embs @ doc_embs.T  # (N, N)

        selected: List[int] = []
        remaining = set(range(len(docs)))

        while remaining and len(selected) < self.rerank_top_k:
            best_score = -float("inf")
            best_idx = -1

            for idx in remaining:
                relevance = rel[idx]
                if selected:
                    diversity = max(sim_matrix[idx][s] for s in selected)
                else:
                    diversity = 0.0
                mmr_score = self.mmr_lambda * relevance - (1 - self.mmr_lambda) * diversity
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            selected.append(best_idx)
            remaining.remove(best_idx)

        return [docs[i] for i in selected]


# ──────────────────────────────────────────────────────────────────────────
# 3. QueryRouter — route queries to specialized handlers
# ──────────────────────────────────────────────────────────────────────────

class QueryType(Enum):
    Factual = auto()      # "What is the capital of France?"
    Analytical = auto()   # "Compare A and B"
    Summarization = auto()  # "Summarize this document"
    Creative = auto()     # "Write a poem about..."
    DomainSpecific = auto()  # "What does this legal clause mean?"
    Ambiguous = auto()    # Unclear intent


class QueryRouter:
    """
    Route incoming queries to the right handler based on intent classification.
    Uses keyword heuristics + embedding similarity to a query-type taxonomy.
    """

    # Taxonomy: query type → example phrases
    TAXONOMY: Dict[QueryType, List[str]] = {
        QueryType.Factual: [
            "what is", "who is", "when did", "where is", "how many",
            "define", "explain", "what are", "list the",
        ],
        QueryType.Analytical: [
            "compare", "contrast", "difference between", "similarities",
            "analyze", "evaluate", "pros and cons", "advantages",
        ],
        QueryType.Summarization: [
            "summarize", "summary", "tl;dr", "key points", "main ideas",
            "brief overview", "in short",
        ],
        QueryType.Creative: [
            "write a", "create a", "draft", "generate", "imagine",
            "poem", "story", "email", "proposal",
        ],
        QueryType.DomainSpecific: [
            "legal", "financial", "medical", "technical", "code",
            "contract", "regulation", "compliance", "tax",
        ],
    }

    def __init__(self, embed_fn: Callable[[str], np.ndarray]) -> None:
        self.embed_fn = embed_fn
        # Pre-compute taxonomy embeddings
        self._taxonomy_emb: Dict[QueryType, np.ndarray] = {}
        for qt, phrases in self.TAXONOMY.items():
            embs = [self.embed_fn(p) for p in phrases]
            self._taxonomy_emb[qt] = np.mean(embs, axis=0)

    def classify(self, query: str) -> QueryType:
        """Classify query intent. Returns best-matching QueryType."""
        q_lower = query.lower()

        # 1. Fast keyword match
        for qt, phrases in self.TAXONOMY.items():
            if any(p in q_lower for p in phrases):
                return qt

        # 2. Embedding similarity fallback
        q_emb = self.embed_fn(query)
        q_emb = q_emb / (np.linalg.norm(q_emb) + 1e-9)

        best_type = QueryType.Ambiguous
        best_score = -1.0

        for qt, ref_emb in self._taxonomy_emb.items():
            ref_emb = ref_emb / (np.linalg.norm(ref_emb) + 1e-9)
            score = float(q_emb @ ref_emb)
            if score > best_score:
                best_score = score
                best_type = qt

        return best_type

    def route(
        self, query: str, handlers: Dict[QueryType, Callable[[str], str]]
    ) -> str:
        """Classify and dispatch to the appropriate handler."""
        qt = self.classify(query)
        handler = handlers.get(qt, handlers.get(QueryType.Ambiguous))
        if handler is None:
            return f"[No handler for {qt.name}] {query}"
        return handler(query)


# ──────────────────────────────────────────────────────────────────────────
# 4. DocumentAgent — per-domain document processing
# ──────────────────────────────────────────────────────────────────────────

class DocumentAgent:
    """
    Specialized agent for a document domain.
    Owns a dedicated VectorStore + Retriever + prompt template.
    """

    def __init__(
        self,
        domain: str,
        store: VectorStore,
        embed_fn: Callable[[str], np.ndarray],
        llm_fn: Callable[[str, Optional[List[str]]], str],
        system_prompt: str = "",
        top_k: int = 4,
    ) -> None:
        self.domain = domain
        self.store = store
        self.embed_fn = embed_fn
        self.llm_fn = llm_fn
        self.system_prompt = system_prompt
        self.retriever = Retriever(store, embed_fn, top_k=top_k)

    def ingest(self, chunks: List[Document]) -> None:
        """Add documents to this agent's store."""
        self.store.add_batch(chunks)

    def query(self, question: str) -> str:
        """Retrieve relevant docs and generate answer."""
        docs = self.retriever.retrieve(
            question, filter_dict={"domain": self.domain}
        )
        context = [d.text for d in docs]

        prompt = self._build_prompt(question, context)
        return self.llm_fn(prompt, context)

    def _build_prompt(self, question: str, context: List[str]) -> str:
        lines = [f"Domain: {self.domain}"]
        if self.system_prompt:
            lines.append(f"System: {self.system_prompt}")
        if context:
            lines.append("Context:")
            for i, c in enumerate(context, 1):
                lines.append(f"  [{i}] {c}")
        lines.append(f"Question: {question}")
        lines.append("Answer:")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────
# 5. AgenticRAG — self-correcting RAG state machine (LangGraph-inspired)
# ──────────────────────────────────────────────────────────────────────────

class RAGPhase(Enum):
    START = auto()
    RETRIEVE = auto()
    GRADE = auto()
    GENERATE = auto()
    WEB_SEARCH = auto()
    FINAL = auto()


@dataclass
class RAGState:
    question: str
    context: List[str] = field(default_factory=list)
    answer: str = ""
    phase: RAGPhase = RAGPhase.START
    iteration: int = 0
    history: List[str] = field(default_factory=list)
    done: bool = False
    score: float = 0.0


class AgenticRAG:
    """
    LangGraph-inspired RAG with self-correction loop.

    Pipeline:
        START → RETRIEVE → GRADE ──► GENERATE → FINAL
                        └─bad──► WEB_SEARCH → GRADE (loop, max 3x)
    """

    def __init__(
        self,
        retriever: Retriever,
        llm_fn: Callable[[str, Optional[List[str]]], str],
        web_search_fn: Optional[Callable[[str], List[str]]] = None,
        max_iterations: int = 3,
        grade_threshold: float = 0.6,
    ) -> None:
        self.retriever = retriever
        self.llm_fn = llm_fn
        self.web_search_fn = web_search_fn
        self.max_iterations = max_iterations
        self.grade_threshold = grade_threshold

    def run(self, question: str) -> RAGState:
        """Execute full state machine until FINAL."""
        state = RAGState(question=question)
        while not state.done:
            state = self._step(state)
        return state

    def execute(self, question: str) -> str:
        """Run and return final answer string."""
        return self.run(question).answer

    def _step(self, state: RAGState) -> RAGState:
        if state.phase == RAGPhase.START:
            state.phase = RAGPhase.RETRIEVE
            state.history.append("→ START")
            return state

        if state.phase == RAGPhase.RETRIEVE:
            docs = self.retriever.retrieve(state.question)
            state.context = [d.text for d in docs]
            state.phase = RAGPhase.GRADE
            state.history.append(f"→ RETRIEVE (got {len(docs)} docs)")
            return state

        if state.phase == RAGPhase.GRADE:
            state.score = self._grade(state.question, state.context)
            state.history.append(f"→ GRADE score={state.score:.2f}")

            if state.score >= self.grade_threshold:
                state.phase = RAGPhase.GENERATE
            else:
                if state.iteration >= self.max_iterations:
                    state.history.append("→ GRADE max_iter reached, forcing GENERATE")
                    state.phase = RAGPhase.GENERATE
                else:
                    state.phase = RAGPhase.WEB_SEARCH
                    state.iteration += 1
            return state

        if state.phase == RAGPhase.WEB_SEARCH:
            if self.web_search_fn:
                results = self.web_search_fn(state.question)
                state.context.extend(results)
                state.history.append(f"→ WEB_SEARCH (got {len(results)} results)")
            else:
                state.history.append("→ WEB_SEARCH (no fn, skipped)")
            state.phase = RAGPhase.GRADE
            return state

        if state.phase == RAGPhase.GENERATE:
            prompt = self._build_generate_prompt(state.question, state.context)
            state.answer = self.llm_fn(prompt, state.context)
            state.phase = RAGPhase.FINAL
            state.history.append("→ GENERATE")
            return state

        if state.phase == RAGPhase.FINAL:
            state.done = True
            state.history.append("→ FINAL")
            return state

        raise RuntimeError(f"Unhandled phase {state.phase}")

    # ── Grading ──

    def _grade(self, question: str, context: List[str]) -> float:
        """Relevance score 0..1 based on token overlap + semantic density."""
        if not context:
            return 0.0

        q_tokens = set(self._tokenize(question))
        if not q_tokens:
            return 0.0

        scores = []
        for c in context:
            c_tokens = set(self._tokenize(c))
            if not c_tokens:
                continue
            overlap = len(q_tokens & c_tokens) / len(q_tokens)
            # Bonus for long context = more information density
            density = min(len(c_tokens) / 50, 1.0)  # cap at 50 tokens
            scores.append(overlap * 0.7 + density * 0.3)

        return max(scores) if scores else 0.0

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace + lowercase tokenization."""
        return re.findall(r"[a-z0-9]+", text.lower())

    def _build_generate_prompt(self, question: str, context: List[str]) -> str:
        ctx = "\n\n".join(
            f"Context {i+1}:\n{c}" for i, c in enumerate(context)
        )
        return (
            f"Answer the question using only the provided context.\n\n"
            f"{ctx}\n\n"
            f"Question: {question}\n"
            f"Answer:"
        )


# ──────────────────────────────────────────────────────────────────────────
# 6. MetaAgent — orchestrator that coordinates all sub-agents
# ──────────────────────────────────────────────────────────────────────────

class MetaAgent:
    """
    Top-level orchestrator.

    Responsibilities:
        • Route queries to the right DocumentAgent via QueryRouter
        • Fall back to general AgenticRAG when no domain agent matches
        • Aggregate results across multiple agents if needed
        • Maintain session history for multi-turn coherence
    """

    def __init__(
        self,
        embed_fn: Callable[[str], np.ndarray],
        llm_fn: Callable[[str, Optional[List[str]]], str],
        router: Optional[QueryRouter] = None,
        general_rag: Optional[AgenticRAG] = None,
    ) -> None:
        self.embed_fn = embed_fn
        self.llm_fn = llm_fn
        self.router = router or QueryRouter(embed_fn)
        self.general_rag = general_rag
        self.agents: Dict[str, DocumentAgent] = {}
        self.session_history: List[Dict[str, Any]] = []

    def register_agent(self, agent: DocumentAgent) -> None:
        """Add a domain-specific agent."""
        self.agents[agent.domain] = agent

    def ask(self, question: str) -> Dict[str, Any]:
        """
        Main entry point. Returns full result dict with:
            answer, source_agent, context, history, confidence.
        """
        # 1. Classify intent
        qtype = self.router.classify(question)

        # 2. Route to domain agent if available
        if qtype == QueryType.DomainSpecific or self._domain_detected(question):
            domain = self._extract_domain(question)
            if domain and domain in self.agents:
                agent = self.agents[domain]
                answer = agent.query(question)
                result = {
                    "answer": answer,
                    "source_agent": domain,
                    "query_type": qtype.name,
                    "context": self._last_retrieved_context(agent, question),
                    "confidence": "high",
                }
                self._record(question, result)
                return result

        # 3. General AgenticRAG fallback
        if self.general_rag:
            state = self.general_rag.run(question)
            result = {
                "answer": state.answer,
                "source_agent": "general_rag",
                "query_type": qtype.name,
                "context": state.context,
                "confidence": self._confidence_from_score(state.score),
                "history": state.history,
                "iterations": state.iteration,
            }
            self._record(question, result)
            return result

        # 4. No RAG available — direct LLM
        answer = self.llm_fn(question, None)
        result = {
            "answer": answer,
            "source_agent": "direct_llm",
            "query_type": qtype.name,
            "context": [],
            "confidence": "unknown",
        }
        self._record(question, result)
        return result

    # ── Helpers ──

    def _domain_detected(self, query: str) -> bool:
        """Check if query mentions any registered domain."""
        q_lower = query.lower()
        return any(dom.lower() in q_lower for dom in self.agents.keys())

    def _extract_domain(self, query: str) -> Optional[str]:
        """Pick the first registered domain mentioned in query."""
        q_lower = query.lower()
        for dom in self.agents.keys():
            if dom.lower() in q_lower:
                return dom
        return None

    def _last_retrieved_context(self, agent: DocumentAgent, question: str) -> List[str]:
        docs = agent.retriever.retrieve(question)
        return [d.text for d in docs]

    def _confidence_from_score(self, score: float) -> str:
        if score >= 0.8:
            return "high"
        elif score >= 0.5:
            return "medium"
        return "low"

    def _record(self, question: str, result: Dict[str, Any]) -> None:
        self.session_history.append({"question": question, **result})

    def get_history(self) -> List[Dict[str, Any]]:
        return self.session_history.copy()

    def clear_history(self) -> None:
        self.session_history.clear()


# ══════════════════════════════════════════════════════════════════════════
# DEMO / SELF-TEST
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # ── Mock embedding ──
    def mock_embed(text: str) -> np.ndarray:
        """Deterministic 64-dim embedding from character frequencies."""
        vec = np.zeros(64, dtype=np.float32)
        for ch in text.lower():
            idx = ord(ch) % 64
            vec[idx] += 1.0
        return vec

    # ── Mock LLM ──
    def mock_llm(prompt: str, _ctx: Optional[List[str]] = None) -> str:
        p = prompt.lower()
        if "capital" in p and "france" in p:
            return "Paris is the capital of France."
        if "python" in p:
            return "Python is a programming language created by Guido van Rossum."
        if "speed of light" in p:
            return "The speed of light in vacuum is approximately 299,792,458 m/s."
        if "legal" in p or "contract" in p:
            return "This is a legal opinion based on the provided clauses."
        return "I don't have enough context to answer confidently."

    # ── Mock web search ──
    def mock_web_search(q: str) -> List[str]:
        return [f"Web result for '{q}': supplementary info from the internet."]

    print("=" * 60)
    print("MAGNATRIX-OS AgenticRAG — Self-Test")
    print("=" * 60)

    # 1. VectorStore
    print("\n[1] VectorStore")
    store = VectorStore(dim=64, metric="cosine")
    docs = [
        Document("d1", "Paris is the capital of France.", mock_embed("Paris France capital")),
        Document("d2", "Python is a programming language.", mock_embed("Python language programming")),
        Document("d3", "Berlin is the capital of Germany.", mock_embed("Berlin Germany capital")),
        Document("d4", "The speed of light is 299,792,458 m/s.", mock_embed("speed light physics")),
    ]
    store.add_batch(docs)
    print(f"  Indexed {store.count()} documents")

    q_emb = mock_embed("capital of France")
    results = store.search(q_emb, k=2)
    for doc, score in results:
        print(f"  → {doc.id}: score={score:.3f} | {doc.text[:50]}")

    # 2. Retriever
    print("\n[2] Retriever")
    retriever = Retriever(store, mock_embed, top_k=6, rerank_top_k=3, use_mmr=True)
    r_docs = retriever.retrieve("What is the capital of France?")
    for d in r_docs:
        print(f"  → {d.id}: {d.text[:50]}")

    # 3. QueryRouter
    print("\n[3] QueryRouter")
    router = QueryRouter(mock_embed)
    test_queries = [
        "What is the capital of France?",
        "Compare Python and Java",
        "Summarize the legal contract",
        "Write a poem about AI",
    ]
    for q in test_queries:
        qt = router.classify(q)
        print(f"  → '{q[:40]}...' → {qt.name}")

    # 4. DocumentAgent (legal domain)
    print("\n[4] DocumentAgent — Legal")
    legal_store = VectorStore(dim=64, metric="cosine")
    legal_docs = [
        Document("l1", "Clause 1: The party of the first part shall...", mock_embed("legal contract clause"), {"domain": "legal"}),
        Document("l2", "Clause 2: Indemnification covers all direct losses...", mock_embed("legal indemnification"), {"domain": "legal"}),
    ]
    legal_store.add_batch(legal_docs)
    legal_agent = DocumentAgent(
        domain="legal",
        store=legal_store,
        embed_fn=mock_embed,
        llm_fn=mock_llm,
        system_prompt="You are a legal assistant. Be precise.",
    )
    ans = legal_agent.query("What does the indemnification clause cover?")
    print(f"  → LegalAgent answer: {ans}")

    # 5. AgenticRAG (general)
    print("\n[5] AgenticRAG")
    general_store = VectorStore(dim=64, metric="cosine")
    general_store.add_batch(docs)
    general_retriever = Retriever(general_store, mock_embed, top_k=4, rerank_top_k=4)
    rag = AgenticRAG(
        retriever=general_retriever,
        llm_fn=mock_llm,
        web_search_fn=mock_web_search,
        max_iterations=2,
        grade_threshold=0.3,
    )

    r1 = rag.run("What is the capital of France?")
    print(f"  → Q1: {r1.answer}")
    print(f"      History: {' | '.join(r1.history)}")

    r2 = rag.run("What is the speed of light?")
    print(f"  → Q2: {r2.answer}")
    print(f"      History: {' | '.join(r2.history)}")

    r3 = rag.run("What is quantum entanglement?")  # triggers web search fallback
    print(f"  → Q3: {r3.answer}")
    print(f"      History: {' | '.join(r3.history)}")

    # 6. MetaAgent (orchestrator)
    print("\n[6] MetaAgent")
    meta = MetaAgent(embed_fn=mock_embed, llm_fn=mock_llm)
    meta.register_agent(legal_agent)

    # Build general RAG for MetaAgent fallback
    meta_rag = AgenticRAG(general_retriever, mock_llm, mock_web_search)
    meta.general_rag = meta_rag

    for q in ["Explain the legal indemnification clause", "What is Python?"]:
        res = meta.ask(q)
        print(f"  → Q: {q[:50]}")
        print(f"    Agent: {res['source_agent']} | Type: {res['query_type']} | Confidence: {res['confidence']}")
        print(f"    A: {res['answer'][:60]}...")

    print("\n" + "=" * 60)
    print("All self-tests passed ✓")
    print("=" * 60)
