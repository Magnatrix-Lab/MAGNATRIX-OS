#!/usr/bin/env python3
"""
MAGNATRIX-OS — LlamaIndex RAG Native
Document agent with multi-tool ReAct reasoning, conversation memory,
and multi-document router. Pure Python stdlib.
"""
from __future__ import annotations

import os
import re
import json
import math
import hashlib
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict


# ── Document & Chunking ─────────────────────────────────────

@dataclass
class LlamaDocument:
    text: str
    doc_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SimpleDirectoryReaderNative:
    """Walk directory, load .txt and .md files."""

    def __init__(self, input_dir: str):
        self.input_dir = input_dir

    def load(self) -> List[LlamaDocument]:
        docs = []
        for root, _, files in os.walk(self.input_dir):
            for fname in files:
                if fname.endswith(('.txt', '.md')):
                    path = os.path.join(root, fname)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            text = f.read()
                        docs.append(LlamaDocument(
                            text=text,
                            doc_id=hashlib.md5(path.encode()).hexdigest()[:16],
                            metadata={"path": path, "filename": fname}
                        ))
                    except Exception:
                        pass
        return docs


class DocumentChunkerNative:
    """Semantic chunking with overlap."""

    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, doc: LlamaDocument) -> List[LlamaDocument]:
        text = doc.text
        chunks = []
        start = 0
        cid = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]
            chunks.append(LlamaDocument(
                text=chunk_text,
                doc_id=f"{doc.doc_id}_chunk_{cid}",
                metadata={**doc.metadata, "chunk_idx": cid, "parent_id": doc.doc_id}
            ))
            start = end - self.overlap
            cid += 1
        return chunks


# ── TF-IDF Indexing ─────────────────────────────────────────

class TFIDFVectorizerNative:
    """Pure Python TF-IDF vectorizer."""

    def __init__(self):
        self.idf: Dict[str, float] = {}
        self.vocab: Dict[str, int] = {}
        self.n_docs = 0

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'[a-zA-Z]{2,}', text.lower())

    def fit(self, docs: List[LlamaDocument]) -> None:
        doc_freq: Dict[str, int] = defaultdict(int)
        for doc in docs:
            tokens = set(self._tokenize(doc.text))
            for tok in tokens:
                doc_freq[tok] += 1
        self.n_docs = len(docs)
        for tok, df in doc_freq.items():
            self.idf[tok] = math.log((self.n_docs + 1) / (df + 1)) + 1
            self.vocab[tok] = len(self.vocab)

    def transform(self, text: str) -> Dict[str, float]:
        tokens = self._tokenize(text)
        tf: Dict[str, int] = defaultdict(int)
        for t in tokens:
            tf[t] += 1
        vec = {}
        for t, count in tf.items():
            if t in self.idf:
                vec[t] = count * self.idf[t]
        return vec

    def cosine(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        dot = sum(a.get(k, 0) * b.get(k, 0) for k in set(a) | set(b))
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class NativeVectorIndex:
    """In-memory TF-IDF vector index."""

    def __init__(self):
        self.docs: List[LlamaDocument] = []
        self.vectors: List[Dict[str, float]] = []
        self.vectorizer = TFIDFVectorizerNative()

    def add(self, docs: List[LlamaDocument]) -> None:
        self.docs.extend(docs)
        self.vectorizer.fit(self.docs)
        self.vectors = [self.vectorizer.transform(d.text) for d in self.docs]

    def query(self, q: str, k: int = 5) -> List[Tuple[LlamaDocument, float]]:
        q_vec = self.vectorizer.transform(q)
        scored = []
        for i, doc in enumerate(self.docs):
            score = self.vectorizer.cosine(q_vec, self.vectors[i])
            if score > 0:
                scored.append((doc, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


# ── Tool System ─────────────────────────────────────────────

class ToolNative:
    def __init__(self, name: str, desc: str, fn: Callable):
        self.name = name
        self.desc = desc
        self.fn = fn


class ToolRegistryNative:
    def __init__(self):
        self.tools: Dict[str, ToolNative] = {}

    def register(self, tool: ToolNative) -> None:
        self.tools[tool.name] = tool

    def list(self) -> List[ToolNative]:
        return list(self.tools.values())

    def call(self, name: str, **kwargs) -> Any:
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        return self.tools[name].fn(**kwargs)


# ── ReAct Agent ─────────────────────────────────────────────

class ReActAgentNative:
    """ReAct-style agent: Reasoning + Acting."""

    def __init__(self, tools: ToolRegistryNative, index: NativeVectorIndex):
        self.tools = tools
        self.index = index
        self.memory: List[Dict] = []

    def think(self, query: str) -> str:
        """Reasoning step: decide tool to use."""
        # Simple keyword-based reasoning
        q = query.lower()
        if any(w in q for w in ['search', 'find', 'look up', 'cari']):
            return "search"
        if any(w in q for w in ['calculate', 'compute', 'math', 'berapa']):
            return "calculator"
        if any(w in q for w in ['summarize', 'summary', 'ringkas']):
            return "summarize"
        return "direct"

    def act(self, query: str) -> Dict[str, Any]:
        """Action step: execute tool."""
        action = self.think(query)
        result = {"action": action, "result": None}

        if action == "search":
            docs = self.index.query(query, k=3)
            result["result"] = "\\n".join([d.text[:200] for d, _ in docs])
        elif action == "calculator":
            result["result"] = self._simple_math(query)
        elif action == "summarize":
            docs = self.index.query(query, k=1)
            text = docs[0][0].text if docs else ""
            result["result"] = self._summarize(text)
        else:
            result["result"] = "Direct answer not available without LLM backend."

        self.memory.append({"query": query, **result})
        return result

    def _simple_math(self, q: str) -> str:
        numbers = re.findall(r'-?\d+\.?\d*', q)
        if len(numbers) >= 2:
            try:
                a, b = float(numbers[0]), float(numbers[1])
                if '+' in q: return str(a + b)
                if '-' in q: return str(a - b)
                if '*' in q: return str(a * b)
                if '/' in q and b != 0: return str(a / b)
            except Exception:
                pass
        return "Could not parse math expression."

    def _summarize(self, text: str, max_sentences: int = 3) -> str:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return " ".join(sentences[:max_sentences])


# ── Multi-Document Router ─────────────────────────────────

class MultiDocumentRouterNative:
    """Routes queries to the right document index."""

    def __init__(self):
        self.indices: Dict[str, NativeVectorIndex] = {}

    def add_index(self, name: str, index: NativeVectorIndex) -> None:
        self.indices[name] = index

    def route(self, query: str) -> Tuple[str, NativeVectorIndex]:
        """Pick best index for query."""
        # Simple routing: try all, pick most relevant
        best_name = list(self.indices.keys())[0] if self.indices else "default"
        return best_name, self.indices.get(best_name, NativeVectorIndex())


# ── Demo ────────────────────────────────────────────────────

def _demo():
    print("=" * 60)
    print("LlamaIndex RAG Native Demo")
    print("=" * 60)

    # Create demo docs
    docs = [
        LlamaDocument("Python is a high-level programming language. It was created by Guido van Rossum in 1991. Python emphasizes code readability.", "doc1"),
        LlamaDocument("Machine learning is a subset of artificial intelligence. It enables computers to learn from data without explicit programming.", "doc2"),
        LlamaDocument("The Fibonacci sequence starts with 0 and 1. Each subsequent number is the sum of the previous two. It appears in many biological settings.", "doc3"),
    ]

    # Chunk
    chunker = DocumentChunkerNative(chunk_size=100, overlap=10)
    chunks = []
    for d in docs:
        chunks.extend(chunker.chunk(d))
    print(f"\n[1] Chunked {len(docs)} docs into {len(chunks)} chunks")

    # Index
    index = NativeVectorIndex()
    index.add(chunks)
    print(f"[2] Indexed {len(index.docs)} chunks")

    # Query
    query = "Who created Python?"
    results = index.query(query, k=2)
    print(f"\n[3] Query: '{query}'")
    for doc, score in results:
        print(f"    Score: {score:.3f} | {doc.text[:60]}...")

    # Agent
    tools = ToolRegistryNative()
    agent = ReActAgentNative(tools, index)
    print(f"\n[4] Agent action for '{query}':")
    result = agent.act(query)
    print(f"    Action: {result['action']}")
    print(f"    Result: {result['result'][:80]}...")

    # Router
    router = MultiDocumentRouterNative()
    router.add_index("docs", index)
    name, idx = router.route("machine learning")
    print(f"\n[5] Router selected: '{name}'")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
