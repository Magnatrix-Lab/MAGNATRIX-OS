"""
native_agentic_rag.py — LangGraph-inspired RAG state machine.

Architectural patterns extracted from cesarhgd85/LangGraph-AgenticRAG:
- State machine with typed nodes and conditional edges.
- retrieve → grade (relevance check) → generate → fallback loop.
- Self-correction via web_search fallback when retrieval is poor.
- Iterative improvement with max-iteration guard.
- LLM provided via callback so file stays stdlib-only.

Pure Python ≥3.9, stdlib only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# In-memory vector store (fallback)
# ---------------------------------------------------------------------------

@dataclass
class MemoryDocument:
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)

class NativeMemoryVectorStore:
    """Cosine-similarity in-memory vector store."""

    def __init__(self) -> None:
        self.docs: List[MemoryDocument] = []

    def add(self, doc: MemoryDocument) -> None:
        self.docs.append(doc)

    def search(self, query_embedding: List[float], k: int = 4) -> List[MemoryDocument]:
        scored = []
        for d in self.docs:
            sim = self._cosine(query_embedding, d.embedding)
            scored.append((sim, d))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [d for _, d in scored[:k]]

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-9)

# ---------------------------------------------------------------------------
# State & Workflow
# ---------------------------------------------------------------------------

class RAGPhase(Enum):
    START = auto(); RETRIEVE = auto(); GRADE = auto(); GENERATE = auto()
    WEB_SEARCH = auto(); FINAL = auto()

@dataclass
class RAGState:
    question: str
    context: List[str] = field(default_factory=list)
    answer: str = ""
    phase: RAGPhase = RAGPhase.START
    iteration: int = 0
    history: List[str] = field(default_factory=list)
    done: bool = False

# ---------------------------------------------------------------------------
# Native Agentic RAG
# ---------------------------------------------------------------------------

class NativeAgenticRAG:
    """
    LangGraph-inspired RAG with self-correction.

    Pipeline:
        START → RETRIEVE → GRADE ──► GENERATE → FINAL
                        └─bad──► WEB_SEARCH → GRADE (loop)
    """

    def __init__(
        self,
        store: NativeMemoryVectorStore,
        embed_fn: Callable[[str], List[float]],
        llm_fn: Callable[[str, Optional[List[str]]], str],
        web_search_fn: Optional[Callable[[str], List[str]]] = None,
        max_iterations: int = 3,
        grade_threshold: float = 0.6,
    ) -> None:
        self.store = store
        self.embed_fn = embed_fn
        self.llm_fn = llm_fn
        self.web_search_fn = web_search_fn
        self.max_iterations = max_iterations
        self.grade_threshold = grade_threshold

    def run(self, question: str) -> RAGState:
        """Execute full state machine."""
        state = RAGState(question=question)
        while not state.done:
            state = self._step(state)
        return state

    def execute(self, question: str) -> str:
        """Run and return the final answer."""
        return self.run(question).answer

    def _step(self, state: RAGState) -> RAGState:
        if state.phase == RAGPhase.START:
            state.phase = RAGPhase.RETRIEVE
            state.history.append("start")
            return state

        if state.phase == RAGPhase.RETRIEVE:
            q_emb = self.embed_fn(state.question)
            docs = self.store.search(q_emb, k=4)
            state.context = [d.text for d in docs]
            state.phase = RAGPhase.GRADE
            state.history.append(f"retrieved:{len(docs)}")
            return state

        if state.phase == RAGPhase.GRADE:
            score = self._grade(state.question, state.context)
            state.history.append(f"grade:{score:.2f}")
            if score >= self.grade_threshold:
                state.phase = RAGPhase.GENERATE
            else:
                if state.iteration >= self.max_iterations:
                    state.phase = RAGPhase.GENERATE  # force generate with what we have
                    state.history.append("grade:max_iter_reached")
                else:
                    state.phase = RAGPhase.WEB_SEARCH
                    state.iteration += 1
            return state

        if state.phase == RAGPhase.WEB_SEARCH:
            if self.web_search_fn:
                results = self.web_search_fn(state.question)
                state.context.extend(results)
                state.history.append(f"web_search:{len(results)}")
            else:
                state.history.append("web_search:none")
            state.phase = RAGPhase.GRADE
            return state

        if state.phase == RAGPhase.GENERATE:
            prompt = self._build_generate_prompt(state.question, state.context)
            state.answer = self.llm_fn(prompt, state.context)
            state.phase = RAGPhase.FINAL
            state.history.append("generated")
            return state

        if state.phase == RAGPhase.FINAL:
            state.done = True
            state.history.append("final")
            return state

        raise RuntimeError(f"Unhandled phase {state.phase}")

    # ------------------------------------------------------------------
    # Grading
    # ------------------------------------------------------------------

    def _grade(self, question: str, context: List[str]) -> float:
        """Relevance score 0..1 based on token overlap heuristic."""
        if not context:
            return 0.0
        q_tokens = set(question.lower().split())
        best = 0.0
        for c in context:
            c_tokens = set(c.lower().split())
            if not c_tokens:
                continue
            overlap = len(q_tokens & c_tokens) / len(q_tokens)
            best = max(best, overlap)
        return best

    def _build_generate_prompt(self, question: str, context: List[str]) -> str:
        ctx = "\n\n".join(f"Context {i+1}:\n{c}" for i, c in enumerate(context))
        return f"Answer the question using only the provided context.\n\n{ctx}\n\nQuestion: {question}\nAnswer:"

# ---------------------------------------------------------------------------
# Native orchestrator with conditional-edge visualization support
# ---------------------------------------------------------------------------

class NativeRAGOrchestrator:
    """Higher-level wrapper exposing graph-like node wiring."""

    def __init__(self, rag: NativeAgenticRAG) -> None:
        self.rag = rag
        self.nodes: Dict[str, Callable[[RAGState], RAGState]] = {
            "retrieve": self._node_retrieve,
            "grade": self._node_grade,
            "generate": self._node_generate,
            "web_search": self._node_web_search,
        }
        self.edges: Dict[str, List[Tuple[str, Callable[[RAGState], bool]]]] = {
            "retrieve": [("grade", lambda s: True)],
            "grade": [
                ("generate", lambda s: s.phase == RAGPhase.GENERATE),
                ("web_search", lambda s: s.phase == RAGPhase.WEB_SEARCH),
            ],
            "web_search": [("grade", lambda s: True)],
            "generate": [],
        }

    def run(self, question: str) -> RAGState:
        state = RAGState(question=question, phase=RAGPhase.RETRIEVE)
        current = "retrieve"
        while current != "generate":
            state = self.nodes[current](state)
            transitions = self.edges.get(current, [])
            next_node = None
            for target, guard in transitions:
                if guard(state):
                    next_node = target
                    break
            if next_node is None:
                break
            current = next_node
        state = self.nodes["generate"](state)
        state.done = True
        return state

    def _node_retrieve(self, state: RAGState) -> RAGState:
        return self.rag._step(state)

    def _node_grade(self, state: RAGState) -> RAGState:
        return self.rag._step(state)

    def _node_web_search(self, state: RAGState) -> RAGState:
        return self.rag._step(state)

    def _node_generate(self, state: RAGState) -> RAGState:
        return self.rag._step(state)

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Mock embedding: simple bag-of-characters float vector
    def mock_embed(text: str) -> List[float]:
        vec = [0.0] * 64
        for ch in text.lower():
            idx = ord(ch) % 64
            vec[idx] += 1.0
        return vec

    # Mock LLM: echo-style
    def mock_llm(prompt: str, _ctx: Optional[List[str]] = None) -> str:
        # Simple keyword-based mock answer
        if "capital" in prompt.lower():
            return "Paris is the capital of France."
        if "python" in prompt.lower():
            return "Python is a programming language created by Guido van Rossum."
        return "I don't know based on the provided context."

    # Mock web search
    def mock_web_search(q: str) -> List[str]:
        return [f"Web result for {q}: additional info from the internet."]

    store = NativeMemoryVectorStore()
    store.add(MemoryDocument("1", "Paris is the capital of France.", mock_embed("Paris France capital")))
    store.add(MemoryDocument("2", "Python is a programming language.", mock_embed("Python language")))
    store.add(MemoryDocument("3", "Berlin is the capital of Germany.", mock_embed("Berlin Germany capital")))

    rag = NativeAgenticRAG(store, mock_embed, mock_llm, mock_web_search, max_iterations=2)

    print("=== Demo 1: Good retrieval ===")
    r1 = rag.run("What is the capital of France?")
    print(f"Answer: {r1.answer}")
    print(f"History: {r1.history}")
    print()

    print("=== Demo 2: Needs web search fallback ===")
    # Question with no good overlap in store
    r2 = rag.run("What is the speed of light?")
    print(f"Answer: {r2.answer}")
    print(f"History: {r2.history}")
    print()

    print("=== Demo 3: Orchestrator wiring ===")
    orch = NativeRAGOrchestrator(rag)
    r3 = orch.run("Who created Python?")
    print(f"Answer: {r3.answer}")
    print(f"History: {r3.history}")
    print()

    print("All demos completed.")
