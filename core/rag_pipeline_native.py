#!/usr/bin/env python3
"""
RAG Pipeline for MAGNATRIX-OS
Retrieval-Augmented Generation pipeline combining Knowledge Base,
LLM adapter, context management, and prompt injection guard.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import time
from typing import Any, Dict, List, Optional, Tuple


@dataclasses.dataclass
class RAGResult:
    query: str
    retrieved_chunks: List[str]
    context: str
    response: str
    sources: List[str]
    latency_ms: float
    tokens_used: int
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "retrieved_chunks": len(self.retrieved_chunks),
            "context_length": len(self.context),
            "response": self.response[:200] + "..." if len(self.response) > 200 else self.response,
            "sources": self.sources,
            "latency_ms": round(self.latency_ms, 2),
            "tokens_used": self.tokens_used,
        }


class RAGPipeline:
    """End-to-end RAG pipeline: retrieve -> contextualize -> generate."""

    def __init__(self, knowledge_base: Any, llm_adapter: Any, context_manager: Optional[Any] = None, prompt_guard: Optional[Any] = None) -> None:
        self.kb = knowledge_base
        self.llm = llm_adapter
        self.ctx = context_manager
        self.guard = prompt_guard
        self._history: List[Dict[str, Any]] = []
        self.max_context_tokens = 4000
        self.top_k = 5

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def query(self, question: str, system_prompt: Optional[str] = None) -> RAGResult:
        start = time.perf_counter()
        # Step 1: Guard check
        if self.guard:
            try:
                result = self.guard.scan_and_sanitize(question)
                if result.threat_level.value in ("dangerous", "critical"):
                    return RAGResult(
                        query=question, retrieved_chunks=[], context="",
                        response="[BLOCKED] Input flagged by safety guard.",
                        sources=[], latency_ms=0, tokens_used=0,
                        metadata={"blocked": True, "reason": result.reason}
                    )
            except Exception:
                pass

        # Step 2: Retrieve relevant chunks
        retrieved = []
        sources = []
        if self.kb:
            try:
                results = self.kb.search(question, top_k=self.top_k)
                for chunk, score in results:
                    retrieved.append(f"[{chunk.doc_id}] {chunk.content}")
                    sources.append(chunk.doc_id)
            except Exception:
                pass

        # Step 3: Build context
        context_parts = []
        token_count = 0
        for chunk_text in retrieved:
            chunk_tokens = len(chunk_text) // 4
            if token_count + chunk_tokens > self.max_context_tokens:
                break
            context_parts.append(chunk_text)
            token_count += chunk_tokens
        context = "\n\n".join(context_parts)

        # Step 4: Build prompt
        base_prompt = system_prompt or "You are a helpful assistant. Use the provided context to answer the question."
        full_prompt = f"{base_prompt}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"

        # Step 5: Generate response
        response = ""
        if self.llm:
            try:
                # Try chat method
                if hasattr(self.llm, 'chat'):
                    llm_result = self.llm.chat(question, system=full_prompt)
                    response = llm_result.text if hasattr(llm_result, 'text') else str(llm_result)
                elif hasattr(self.llm, 'chat_mock'):
                    llm_result = self.llm.chat_mock(question)
                    response = llm_result.text if hasattr(llm_result, 'text') else str(llm_result)
                else:
                    response = self._fallback_response(question, context)
            except Exception:
                response = self._fallback_response(question, context)
        else:
            response = self._fallback_response(question, context)

        latency = (time.perf_counter() - start) * 1000

        # Step 6: Store in context
        if self.ctx:
            try:
                self.ctx.store(question, memory_type_str="conversation", source="user")
                self.ctx.store(response, memory_type_str="conversation", source="assistant")
            except Exception:
                pass

        result = RAGResult(
            query=question,
            retrieved_chunks=retrieved,
            context=context,
            response=response,
            sources=list(set(sources)),
            latency_ms=latency,
            tokens_used=token_count + len(response) // 4,
            metadata={"chunks_retrieved": len(retrieved)}
        )
        self._history.append(result.to_dict())
        return result

    def _fallback_response(self, question: str, context: str) -> str:
        if context:
            return f"[RAG] Based on retrieved context, here's what I found about '{question[:50]}':\n\n{context[:500]}"
        return f"[RAG] No relevant documents found for '{question[:50]}'. Please ingest relevant documents first."

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    def ingest(self, doc_id: str, title: str, content: str, source: str = "user") -> bool:
        if not self.kb:
            return False
        try:
            self.kb.ingest(doc_id, title, content, source)
            return True
        except Exception:
            return False

    def ingest_file(self, file_path: str) -> bool:
        if not self.kb:
            return False
        try:
            self.kb.ingest_file(file_path)
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        kb_stats = self.kb.stats() if self.kb else {}
        return {
            "knowledge_base": kb_stats,
            "queries_served": len(self._history),
            "avg_latency_ms": round(sum(h.get("latency_ms", 0) for h in self._history) / max(1, len(self._history)), 2),
            "max_context_tokens": self.max_context_tokens,
            "top_k": self.top_k,
        }

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._history[-limit:]

    def clear_history(self) -> None:
        self._history.clear()


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile, shutil, sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.knowledge_base_native import KnowledgeBase
    from core.multi_model_llm_adapter_native import MultiModelLLMAdapter
    from core.prompt_injection_guard_native import PromptInjectionGuard
    from core.context_manager_native import ContextManager

    tmp = tempfile.mkdtemp(prefix="magnatrix_rag_")
    kb = KnowledgeBase(tmp, chunk_size=200, chunk_overlap=30)
    llm = MultiModelLLMAdapter()
    guard = PromptInjectionGuard()
    ctx = ContextManager(tmp)

    # Ingest knowledge
    kb.ingest("py_intro", "Python Introduction", "Python is a high-level programming language. It was created by Guido van Rossum. Python emphasizes code readability.", source="docs")
    kb.ingest("py_libs", "Python Libraries", "Python has a vast ecosystem of libraries. NumPy is for numerical computing. Pandas is for data analysis. Flask is for web development.", source="docs")
    kb.ingest("js_intro", "JavaScript Introduction", "JavaScript is a scripting language for web pages. It enables interactive web experiences.", source="docs")

    pipeline = RAGPipeline(kb, llm, ctx, guard)
    print("=== RAG Pipeline Demo ===\n")
    print(f"KB Stats: {pipeline.get_stats()}")
    # Query
    print("\nQuery: 'What is Python?'")
    result = pipeline.query("What is Python?")
    print(f"Response: {result.response}")
    print(f"Sources: {result.sources}")
    print(f"Latency: {result.latency_ms:.2f}ms")
    # Query 2
    print("\nQuery: 'Which libraries for data analysis?'")
    result2 = pipeline.query("Which libraries for data analysis?")
    print(f"Response: {result2.response}")
    print(f"Sources: {result2.sources}")
    # Stats
    print(f"\nPipeline Stats: {pipeline.get_stats()}")
    # Cleanup
    shutil.rmtree(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
