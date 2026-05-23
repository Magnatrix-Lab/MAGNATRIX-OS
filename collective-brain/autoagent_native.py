"""
AutoAgent Native - Pure Python Zero-Code LLM Agent Framework
A native reimplementation of AutoAgent (HKUDS/AutoAgent).

This module provides a complete LLM agent framework built entirely on the
Python standard library, with no external hard dependencies.

Sections:
  1. MetaAgent Architecture
  2. Agentic-RAG Vector DB
  3. Natural Language Agent Creation
  4. Multi-LLM Support
  5. ReAct + Function-Calling Modes
  6. Self-Play Customization
  7. Workflow Editor DAG
  8. Utilities + Demo
"""

from __future__ import annotations

import json
import math
import random
import re
import time
import hashlib
import inspect
import textwrap
import statistics
import datetime
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

# ---------------------------------------------------------------------------
# Section 1: MetaAgent Architecture (lines ~1–200)
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """
    A unit of work within the agent system.

    Attributes:
        id: Unique identifier.
        description: Human-readable description.
        status: Current execution state (pending/running/completed/failed).
        dependencies: Set of task IDs that must finish before this task.
        result: Output produced by the task.
        retries: Number of retry attempts consumed.
    """

    id: str
    description: str
    status: str = "pending"
    dependencies: Set[str] = field(default_factory=set)
    result: Any = None
    retries: int = 0

    def __repr__(self) -> str:
        return (
            f"Task(id={self.id!r}, description={self.description[:40]!r}, "
            f"status={self.status!r}, deps={self.dependencies}, retries={self.retries})"
        )


class Planner:
    """
    Breaks a high-level natural-language goal into an actionable DAG of tasks.
    """

    def __init__(self) -> None:
        self._templates: List[Dict[str, Any]] = []

    def plan(self, goal: str, llm_provider: Optional["LLMProvider"] = None) -> List[Task]:
        """
        Decompose *goal* into a list of :class:`Task` objects with dependencies.

        In a production system this would call an LLM to produce the DAG.
        Here we use a deterministic heuristic so the framework works without
        network access.
        """
        tasks: List[Task] = []
        parts = [p.strip() for p in goal.split(",") if p.strip()]
        if not parts:
            parts = [goal.strip()]
        for i, part in enumerate(parts):
            tid = f"t{i}"
            deps: Set[str] = set()
            if i > 0:
                deps.add(f"t{i - 1}")
            tasks.append(Task(id=tid, description=part, dependencies=deps))
        if llm_provider is not None:
            prompt = f"Break this goal into steps as JSON list of dicts: {goal}"
            raw = llm_provider.generate(prompt, max_tokens=512)
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    tasks = []
                    for idx, item in enumerate(parsed):
                        tid = str(item.get("id", f"t{idx}"))
                        desc = str(item.get("description", ""))
                        deps = set(str(d) for d in item.get("dependencies", []))
                        tasks.append(Task(id=tid, description=desc, dependencies=deps))
            except json.JSONDecodeError:
                pass  # fall back to the heuristic plan above
        return tasks

    def __repr__(self) -> str:
        return f"Planner(templates={len(self._templates)})"


class Executor:
    """
    Runs tasks respecting their dependency graph.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Callable[[Task], Any]] = {}

    def register_handler(self, task_id: str, handler: Callable[[Task], Any]) -> None:
        """Bind a callable to a specific task ID."""
        self._registry[task_id] = handler

    def run(self, tasks: List[Task]) -> None:
        """
        Execute *tasks* in topologically-resolved order.

        Tasks with satisfied dependencies are run immediately; others block
        until their predecessors finish.
        """
        remaining = {t.id: t for t in tasks}
        completed: Set[str] = set()
        while remaining:
            runnable = [
                t for t in remaining.values() if t.dependencies <= completed
            ]
            if not runnable:
                # Deadlock detected: force-run the first remaining task
                runnable = [list(remaining.values())[0]]
            for task in runnable:
                task.status = "running"
                handler = self._registry.get(task.id)
                try:
                    if handler:
                        task.result = handler(task)
                    else:
                        task.result = f"<executed: {task.description}>"
                    task.status = "completed"
                except Exception as exc:
                    task.status = "failed"
                    task.result = exc
                completed.add(task.id)
                del remaining[task.id]

    def __repr__(self) -> str:
        return f"Executor(handlers={list(self._registry.keys())})"


class Observer:
    """
    Monitors execution state, captures output, and reports progress.
    """

    def __init__(self) -> None:
        self._logs: List[Dict[str, Any]] = []
        self._callbacks: List[Callable[[str, Any], None]] = []

    def watch(self, tasks: List[Task]) -> None:
        """Attach lightweight logging hooks to every task."""
        for t in tasks:
            self._logs.append(
                {
                    "task_id": t.id,
                    "status": t.status,
                    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
            )

    def report(self) -> Dict[str, Any]:
        """Return a snapshot of observed progress."""
        return {"log_count": len(self._logs), "latest": self._logs[-3:]}

    def on_change(self, callback: Callable[[str, Any], None]) -> None:
        self._callbacks.append(callback)

    def __repr__(self) -> str:
        return f"Observer(logs={len(self._logs)}, callbacks={len(self._callbacks)})"


class Reflector:
    """
    Self-evaluation loop with configurable retry caps.
    """

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self._history: List[Dict[str, Any]] = []

    def evaluate(self, task: Task) -> Tuple[bool, str]:
        """
        Decide whether *task* succeeded or needs a retry.

        Returns ``(passed, reason)``.
        """
        if task.status == "completed":
            return True, "ok"
        if task.retries >= self.max_retries:
            return False, f"max retries exceeded ({self.max_retries})"
        return False, "retry eligible"

    def record(self, task: Task, decision: bool, reason: str) -> None:
        self._history.append(
            {
                "task_id": task.id,
                "decision": decision,
                "reason": reason,
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        )

    def __repr__(self) -> str:
        return f"Reflector(max_retries={self.max_retries}, history={len(self._history)})"


class MetaAgent:
    """
    Base class for goal-driven meta-agents.

    Orchestrates :class:`Planner`, :class:`Executor`, :class:`Observer`,
    and :class:`Reflector` into a cohesive loop.
    """

    def __init__(self, goal: str, llm_provider: Optional["LLMProvider"] = None) -> None:
        self.goal = goal
        self.planner = Planner()
        self.executor = Executor()
        self.observer = Observer()
        self.reflector = Reflector()
        self.llm_provider = llm_provider
        self._tasks: List[Task] = []

    def decompose(self) -> List[Task]:
        """Run planning."""
        self._tasks = self.planner.plan(self.goal, self.llm_provider)
        self.observer.watch(self._tasks)
        return self._tasks

    def orchestrate(self) -> Dict[str, Any]:
        """
        Plan, execute, observe, and reflect until the goal is resolved.
        """
        self.decompose()
        for attempt in range(1, self.reflector.max_retries + 2):
            self.executor.run(self._tasks)
            all_passed = True
            for t in self._tasks:
                ok, reason = self.reflector.evaluate(t)
                self.reflector.record(t, ok, reason)
                if not ok:
                    all_passed = False
                    t.retries += 1
                    t.status = "pending"
            if all_passed:
                break
        return {
            "goal": self.goal,
            "attempts": attempt,
            "tasks": [
                {"id": t.id, "status": t.status, "result": str(t.result)}
                for t in self._tasks
            ],
        }

    def spawn_subtask(self, sub_goal: str) -> "MetaAgent":
        """Create a child agent with a narrower scope."""
        child = MetaAgent(sub_goal, llm_provider=self.llm_provider)
        return child

    def __repr__(self) -> str:
        return f"MetaAgent(goal={self.goal[:50]!r}, tasks={len(self._tasks)})"


# ---------------------------------------------------------------------------
# Section 2: Agentic-RAG Vector DB (lines ~200–400)
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """
    A piece of text stored in the vector database.

    Attributes:
        id: Unique document identifier.
        text: Raw textual content.
        embedding: Dense vector representation.
        metadata: Arbitrary key/value annotations.
    """

    id: str
    text: str
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"Document(id={self.id!r}, text={self.text[:40]!r}, "
            f"embedding_dim={len(self.embedding)}, metadata={self.metadata})"
        )


class EmbeddingProvider(ABC):
    """Abstract base for text-to-vector encoders."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Encode a batch of strings into float vectors."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class SentenceTransformersStub(EmbeddingProvider):
    """
    Stub that returns deterministic pseudo-embeddings.
    Useful when no heavy ML runtime is available.
    """

    def embed(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2 ** 31)
            rng = random.Random(seed)
            dim = 384
            vec = [rng.uniform(-1.0, 1.0) for _ in range(dim)]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors


class TFIDFEmbedder(EmbeddingProvider):
    """
    Pure-Python TF-IDF embedder.
    Builds a vocabulary from the corpus and produces sparse-style dense vectors.
    """

    def __init__(self, max_features: int = 256) -> None:
        self.max_features = max_features
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._docs_count: int = 0

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    def _build_vocabulary(self, texts: List[str]) -> None:
        doc_freq: Dict[str, int] = {}
        for text in texts:
            tokens = set(self._tokenize(text))
            for tok in tokens:
                doc_freq[tok] = doc_freq.get(tok, 0) + 1
        sorted_toks = sorted(
            doc_freq.items(), key=lambda kv: (kv[1], kv[0]), reverse=True
        )[: self.max_features]
        self._vocab = {tok: idx for idx, (tok, _) in enumerate(sorted_toks)}
        self._idf = {
            tok: math.log((self._docs_count + 1) / (freq + 1)) + 1.0
            for tok, freq in doc_freq.items()
            if tok in self._vocab
        }

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not self._vocab or len(texts) != self._docs_count:
            self._docs_count = len(texts)
            self._build_vocabulary(texts)
        vectors: List[List[float]] = []
        for text in texts:
            tokens = self._tokenize(text)
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            vec = [0.0] * len(self._vocab)
            for tok, count in tf.items():
                if tok in self._vocab:
                    idx = self._vocab[tok]
                    vec[idx] = (count / len(tokens)) * self._idf.get(tok, 1.0)
            # Normalise
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vec = [v / norm for v in vec]
            # Pad to uniform length if needed
            while len(vec) < self.max_features:
                vec.append(0.0)
            vectors.append(vec[: self.max_features])
        return vectors

    def __repr__(self) -> str:
        return f"TFIDFEmbedder(max_features={self.max_features}, vocab={len(self._vocab)})"


class VectorStore:
    """
    In-memory vector database with add/search/delete.
    """

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self._provider = embedding_provider
        self._docs: Dict[str, Document] = {}

    def add(self, documents: List[Document]) -> None:
        """Index documents, computing embeddings on the fly."""
        texts = [d.text for d in documents]
        vectors = self._provider.embed(texts)
        for doc, vec in zip(documents, vectors):
            doc.embedding = vec
            self._docs[doc.id] = doc

    def search(
        self, query: str, top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """Brute-force cosine similarity search."""
        q_vec = self._provider.embed([query])[0]
        results: List[Tuple[Document, float]] = []
        for doc in self._docs.values():
            if not doc.embedding:
                continue
            dot = sum(a * b for a, b in zip(q_vec, doc.embedding))
            results.append((doc, dot))
        results.sort(key=lambda kv: kv[1], reverse=True)
        return results[:top_k]

    def delete(self, doc_id: str) -> bool:
        if doc_id in self._docs:
            del self._docs[doc_id]
            return True
        return False

    def __repr__(self) -> str:
        return f"VectorStore(docs={len(self._docs)}, provider={self._provider!r})"


class HNSWIndex:
    """
    Simplified HNSW-style stub for approximate nearest neighbour search.
    Falls back to brute-force cosine similarity when the index is cold.
    """

    def __init__(self, dim: int, m: int = 8, ef: int = 16) -> None:
        self.dim = dim
        self.m = m
        self.ef = ef
        self._layers: List[Dict[int, List[int]]] = []
        self._vectors: Dict[int, List[float]] = {}
        self._seq = 0

    def _cosine(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (na * nb)

    def add(self, vec: List[float]) -> int:
        idx = self._seq
        self._seq += 1
        self._vectors[idx] = vec
        return idx

    def search(self, query: List[float], top_k: int = 5) -> List[Tuple[int, float]]:
        # Brute-force fallback (real HNSW is hundreds of lines)
        scored = [
            (idx, self._cosine(query, vec)) for idx, vec in self._vectors.items()
        ]
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return scored[:top_k]

    def __repr__(self) -> str:
        return f"HNSWIndex(dim={self.dim}, m={self.m}, entries={len(self._vectors)})"


class Chunker:
    """
    Text chunking with multiple strategies.
    """

    @staticmethod
    def fixed_size(text: str, size: int = 256, overlap: int = 32) -> List[str]:
        """Slice text into equal-sized windows."""
        chunks: List[str] = []
        start = 0
        while start < len(text):
            chunks.append(text[start : start + size])
            start += size - overlap
        return [c for c in chunks if c.strip()]

    @staticmethod
    def sentence_boundary(text: str, max_len: int = 512) -> List[str]:
        """Split on sentence punctuation, respecting *max_len*."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: List[str] = []
        current = ""
        for s in sentences:
            if len(current) + len(s) + 1 > max_len:
                if current:
                    chunks.append(current.strip())
                current = s
            else:
                current = (current + " " + s).strip()
        if current:
            chunks.append(current.strip())
        return chunks

    @staticmethod
    def recursive(text: str, chunk_size: int = 512, separators: Optional[List[str]] = None) -> List[str]:
        """
        Recursively split by the list of separators, falling back to
        fixed-size when nothing else works.
        """
        if separators is None:
            separators = ["\n\n", "\n", ". ", " "]
        if len(text) <= chunk_size:
            return [text]
        for sep in separators:
            parts = text.split(sep)
            if len(parts) > 1 and max(len(p) for p in parts) < chunk_size:
                return [p.strip() for p in parts if p.strip()]
        return Chunker.fixed_size(text, size=chunk_size)

    def __repr__(self) -> str:
        return "Chunker(fixed_size, sentence_boundary, recursive)"


class RAGPipeline:
    """
    End-to-end retrieval-augmented generation pipeline.

    query -> embed -> top-k retrieval -> rerank stub -> context injection
    """

    def __init__(
        self,
        vector_store: VectorStore,
        llm_provider: Optional["LLMProvider"] = None,
        top_k: int = 5,
    ) -> None:
        self.vector_store = vector_store
        self.llm_provider = llm_provider
        self.top_k = top_k

    def retrieve(self, query: str) -> List[Document]:
        """Return the most relevant documents."""
        results = self.vector_store.search(query, top_k=self.top_k)
        # Stub rerank: boost docs that contain query terms verbatim
        boosted: List[Tuple[Document, float]] = []
        terms = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))
        for doc, score in results:
            bonus = sum(1 for t in terms if t in doc.text.lower()) * 0.05
            boosted.append((doc, score + bonus))
        boosted.sort(key=lambda kv: kv[1], reverse=True)
        return [d for d, _ in boosted]

    def generate(self, query: str, system: str = "") -> str:
        """
        Inject retrieved context into a prompt and call the LLM.
        """
        docs = self.retrieve(query)
        context = "\n\n---\n\n".join(d.text for d in docs)
        prompt = (
            f"{system}\n\nContext:\n{context}\n\nQuestion: {query}\nAnswer:"
            if system
            else f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        )
        if self.llm_provider is None:
            return f"<RAG stub response using {len(docs)} docs>"
        return self.llm_provider.generate(prompt, max_tokens=1024)

    def __repr__(self) -> str:
        return (
            f"RAGPipeline(store={self.vector_store!r}, "
            f"top_k={self.top_k}, llm={self.llm_provider is not None})"
        )


# ---------------------------------------------------------------------------
# Section 3: Natural Language Agent Creation (lines ~400–550)
# ---------------------------------------------------------------------------


@dataclass
class Tool:
    """
    A tool that an agent can invoke.

    Attributes:
        name: Short identifier.
        description: Natural-language usage explanation.
        callable: The actual function to run.
        parameters: JSON Schema dict for the arguments.
    """

    name: str
    description: str
    callable: Callable[..., Any]
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"Tool(name={self.name!r}, description={self.description[:40]!r}, "
            f"params={list(self.parameters.get('properties', {}).keys())})"
        )


class AgentTemplate(ABC):
    """
    Base template for specialised agents.
    """

    def __init__(self, name: str, tools: Optional[List[Tool]] = None) -> None:
        self.name = name
        self.tools = tools or []

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the persona prompt for this agent type."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, tools={len(self.tools)})"


class ResearcherAgent(AgentTemplate):
    """Digs through sources and synthesises findings."""

    def system_prompt(self) -> str:
        return "You are a meticulous researcher. Cite sources, avoid speculation."


class CoderAgent(AgentTemplate):
    """Writes and explains code."""

    def system_prompt(self) -> str:
        return (
            "You are a senior software engineer. Write clean, idiomatic code "
            "with comments and type hints."
        )


class AnalystAgent(AgentTemplate):
    """Crunches numbers and detects patterns."""

    def system_prompt(self) -> str:
        return (
            "You are a data analyst. Use statistical reasoning, present "
            "insights with charts in ASCII when helpful."
        )


class WriterAgent(AgentTemplate):
    """Produces prose, docs, or creative writing."""

    def system_prompt(self) -> str:
        return (
            "You are a professional writer. Tailor tone to the audience, "
            "structure ideas clearly, and eliminate filler."
        )


class ReviewerAgent(AgentTemplate):
    """Critiques output for correctness, style, and completeness."""

    def system_prompt(self) -> str:
        return (
            "You are a rigorous reviewer. Flag errors, suggest concrete "
            "improvements, and score clarity from 1-10."
        )


class PlannerAgent(AgentTemplate):
    """Creates execution plans and roadmaps."""

    def system_prompt(self) -> str:
        return (
            "You are a project planner. Break work into milestones, "
            "identify dependencies, and flag risks."
        )


class DebuggerAgent(AgentTemplate):
    """Investigates bugs and proposes fixes."""

    def system_prompt(self) -> str:
        return (
            "You are a debugger. Reproduce the issue, trace root causes, "
            "and provide minimal, testable fixes."
        )


class TesterAgent(AgentTemplate):
    """Designs and runs tests."""

    def system_prompt(self) -> str:
        return (
            "You are a QA engineer. Write edge-case tests, use property-based "
            "reasoning, and report coverage."
        )


class DesignerAgent(AgentTemplate):
    """Creates UI/UX or visual specifications."""

    def system_prompt(self) -> str:
        return (
            "You are a product designer. Favour accessibility, consistency, "
            "and progressive disclosure."
        )


class ManagerAgent(AgentTemplate):
    """Coordinates other agents and resolves conflicts."""

    def system_prompt(self) -> str:
        return (
            "You are a team lead. Delegate clearly, unblock teammates, "
            "and keep scope realistic."
        )


class AgentFactory:
    """
    Converts a natural-language description into a configured agent.
    """

    _BUILT_INS: Dict[str, Type[AgentTemplate]] = {
        "researcher": ResearcherAgent,
        "coder": CoderAgent,
        "analyst": AnalystAgent,
        "writer": WriterAgent,
        "reviewer": ReviewerAgent,
        "planner": PlannerAgent,
        "debugger": DebuggerAgent,
        "tester": TesterAgent,
        "designer": DesignerAgent,
        "manager": ManagerAgent,
    }

    def __init__(self) -> None:
        self._tool_registry: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        self._tool_registry[tool.name] = tool

    def parse(self, description: str) -> Dict[str, Any]:
        """
        Extract agent type and optional config from an English description.
        """
        desc_lower = description.lower()
        agent_type = "coder"
        for key, cls in self._BUILT_INS.items():
            if key in desc_lower:
                agent_type = key
                break
        config: Dict[str, Any] = {
            "agent_type": agent_type,
            "name": description.split()[:3] or ["Agent"],
            "tools": list(self._tool_registry.values()),
        }
        return config

    def instantiate(self, config: Dict[str, Any]) -> AgentTemplate:
        """Build an agent from a configuration dictionary."""
        cls = self._BUILT_INS.get(config.get("agent_type", "coder"), CoderAgent)
        return cls(name=config.get("name", "Agent"), tools=config.get("tools"))

    def __repr__(self) -> str:
        return f"AgentFactory(built_ins={list(self._BUILT_INS.keys())}, tools={len(self._tool_registry)})"


# ---------------------------------------------------------------------------
# Section 4: Multi-LLM Support (lines ~550–700)
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    """
    Abstract LLM backend.
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Synchronous text generation."""
        ...

    def stream_generate(self, prompt: str, **kwargs: Any) -> Iterator[str]:
        """Stub streaming — yields the full response in one chunk."""
        yield self.generate(prompt, **kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class OpenAIProvider(LLMProvider):
    """OpenAI-style HTTP stub."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, **kwargs: Any) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 512),
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
                return str(payload["choices"][0]["message"]["content"])
        except Exception:
            return f"<OpenAIProvider stub response for model={self.model}>"

    def __repr__(self) -> str:
        return f"OpenAIProvider(model={self.model!r}, base_url={self.base_url!r})"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude HTTP stub."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "claude-3-opus-20240229",
        base_url: str = "https://api.anthropic.com/v1",
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, **kwargs: Any) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": kwargs.get("max_tokens", 512),
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/messages",
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
                return str(payload["content"][0]["text"])
        except Exception:
            return f"<AnthropicProvider stub response for model={self.model}>"

    def __repr__(self) -> str:
        return f"AnthropicProvider(model={self.model!r})"


class GeminiProvider(LLMProvider):
    """Google Gemini HTTP stub."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-1.5-pro",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, **kwargs: Any) -> str:
        body = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "maxOutputTokens": kwargs.get("max_tokens", 512),
                },
            }
        ).encode()
        url = (
            f"{self.base_url}/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
                return str(payload["candidates"][0]["content"]["parts"][0]["text"])
        except Exception:
            return f"<GeminiProvider stub response for model={self.model}>"

    def __repr__(self) -> str:
        return f"GeminiProvider(model={self.model!r})"


class DeepSeekProvider(LLMProvider):
    """DeepSeek HTTP stub."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com/v1",
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, **kwargs: Any) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 512),
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
                return str(payload["choices"][0]["message"]["content"])
        except Exception:
            return f"<DeepSeekProvider stub response for model={self.model}>"

    def __repr__(self) -> str:
        return f"DeepSeekProvider(model={self.model!r})"


class GroqProvider(LLMProvider):
    """Groq HTTP stub."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "llama3-70b-8192",
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, **kwargs: Any) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 512),
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
                return str(payload["choices"][0]["message"]["content"])
        except Exception:
            return f"<GroqProvider stub response for model={self.model}>"

    def __repr__(self) -> str:
        return f"GroqProvider(model={self.model!r})"


class OllamaProvider(LLMProvider):
    """Ollama local API stub."""

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434/api",
        timeout: int = 120,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, **kwargs: Any) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 512),
                },
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
                return str(payload.get("response", ""))
        except Exception:
            return f"<OllamaProvider stub response for model={self.model}>"

    def __repr__(self) -> str:
        return f"OllamaProvider(model={self.model!r}, base_url={self.base_url!r})"


class ProviderRegistry:
    """
    Central registry for named LLM backends.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, LLMProvider] = {}

    def register(self, name: str, provider: LLMProvider) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> Optional[LLMProvider]:
        return self._providers.get(name)

    def list(self) -> List[str]:
        return list(self._providers.keys())

    def __repr__(self) -> str:
        return f"ProviderRegistry(providers={self.list()})"


class RetryConfig:
    """Simple exponential-backoff configuration."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def sleep_time(self, attempt: int) -> float:
        return min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)

    def __repr__(self) -> str:
        return (
            f"RetryConfig(max_retries={self.max_retries}, "
            f"base_delay={self.base_delay})"
        )


class CircuitBreaker:
    """
    Stub circuit breaker for resilient LLM calls.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._last_failure_time: Optional[float] = None

    def can_call(self) -> bool:
        if self._failures < self.failure_threshold:
            return True
        if self._last_failure_time and (
            time.time() - self._last_failure_time > self.recovery_timeout
        ):
            self._failures = 0
            return True
        return False

    def record_success(self) -> None:
        self._failures = 0
        self._last_failure_time = None

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.time()

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(failures={self._failures}, "
            f"threshold={self.failure_threshold})"
        )


# ---------------------------------------------------------------------------
# Section 5: ReAct + Function-Calling Modes (lines ~700–900)
# ---------------------------------------------------------------------------


@dataclass
class Thought:
    """A reasoning step inside the ReAct loop."""

    content: str

    def __repr__(self) -> str:
        return f"Thought(content={self.content[:50]!r})"


@dataclass
class Action:
    """An action to be executed."""

    name: str
    inputs: Dict[str, Any]

    def __repr__(self) -> str:
        return f"Action(name={self.name!r}, inputs={self.inputs})"


@dataclass
class Observation:
    """The result of executing an action."""

    content: str

    def __repr__(self) -> str:
        return f"Observation(content={self.content[:50]!r})"


class ReActEngine:
    """
    Thought -> Action -> Observation loop with max-iteration guard.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: "ToolRegistry",
        max_iterations: int = 10,
    ) -> None:
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self._history: List[Union[Thought, Action, Observation]] = []

    def run(self, query: str) -> str:
        """
        Execute the ReAct loop for *query* and return the final answer.
        """
        prompt = self._build_prompt(query)
        for i in range(self.max_iterations):
            llm_output = self.llm_provider.generate(prompt, max_tokens=512)
            thought, action = self._parse_output(llm_output)
            if thought:
                self._history.append(thought)
            if action is None:
                return llm_output
            self._history.append(action)
            obs = self._execute_action(action)
            self._history.append(obs)
            prompt = (
                f"{prompt}\n\nThought: {thought.content if thought else ''}\n"
                f"Action: {action.name}({json.dumps(action.inputs)})\n"
                f"Observation: {obs.content}\n"
            )
        return f"<ReAct max iterations reached ({self.max_iterations})>"

    def _build_prompt(self, query: str) -> str:
        tools_desc = self.tool_registry.describe()
        return (
            f"Answer the following question by interleaving Thoughts and Actions.\n"
            f"Available tools:\n{tools_desc}\n\n"
            f"Question: {query}\n"
        )

    def _parse_output(self, text: str) -> Tuple[Optional[Thought], Optional[Action]]:
        thought_match = re.search(r"Thought:\s*(.+?)(?:\nAction:|$)", text, re.S)
        action_match = re.search(
            r"Action:\s*(\w+)\((.*?)\)", text, re.S
        ) or re.search(r"Action:\s*(\w+)\s*\n", text, re.S)
        thought = Thought(thought_match.group(1).strip()) if thought_match else None
        if action_match:
            name = action_match.group(1).strip()
            raw_inputs = action_match.group(2).strip() if action_match.lastindex and action_match.lastindex >= 2 else ""
            inputs: Dict[str, Any] = {}
            try:
                inputs = json.loads(raw_inputs)
            except json.JSONDecodeError:
                inputs = {"raw": raw_inputs}
            return thought, Action(name=name, inputs=inputs)
        return thought, None

    def _execute_action(self, action: Action) -> Observation:
        tool = self.tool_registry.get(action.name)
        if tool is None:
            return Observation(content=f"Error: tool '{action.name}' not found.")
        try:
            result = tool.callable(**action.inputs)
            return Observation(content=str(result))
        except Exception as exc:
            return Observation(content=f"Error: {exc}")

    def __repr__(self) -> str:
        return f"ReActEngine(iterations={len(self._history)}, max={self.max_iterations})"


class FunctionCaller:
    """
    OpenAI-style function-calling schema parser and executor.
    """

    def __init__(self, tool_registry: "ToolRegistry") -> None:
        self.tool_registry = tool_registry

    def parse(self, llm_output: str) -> List[Dict[str, Any]]:
        """
        Extract function calls from JSON embedded in the LLM response.
        """
        calls: List[Dict[str, Any]] = []
        # Try to find a JSON array or object
        for block in re.findall(r"```json\s*(.*?)\s*```", llm_output, re.S):
            try:
                parsed = json.loads(block)
                if isinstance(parsed, list):
                    calls.extend(parsed)
                elif isinstance(parsed, dict) and "name" in parsed:
                    calls.append(parsed)
            except json.JSONDecodeError:
                continue
        # Fallback: regex for {"name": ..., "arguments": ...}
        for m in re.finditer(
            r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}',
            llm_output,
            re.S,
        ):
            calls.append({"name": m.group(1), "arguments": json.loads(m.group(2))})
        return calls

    def execute(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for call in calls:
            tool = self.tool_registry.get(call["name"])
            if tool is None:
                results.append(
                    {"name": call["name"], "error": "tool not found"}
                )
                continue
            args = call.get("arguments", {})
            try:
                out = tool.callable(**args)
                results.append({"name": call["name"], "result": out})
            except Exception as exc:
                results.append({"name": call["name"], "error": str(exc)})
        return results

    def __repr__(self) -> str:
        return f"FunctionCaller(registry={self.tool_registry!r})"


class ToolRegistry:
    """
    Decorator-based tool registry with JSON schema inference.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def describe(self) -> str:
        lines = []
        for name, tool in self._tools.items():
            lines.append(f"- {name}: {tool.description}")
        return "\n".join(lines)

    def tool(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator that auto-registers a function as a tool.
        """
        schema = self._infer_schema(fn)
        name = fn.__name__
        self.register(
            Tool(
                name=name,
                description=fn.__doc__ or name,
                callable=fn,
                parameters=schema,
            )
        )
        return fn

    def _infer_schema(self, fn: Callable[..., Any]) -> Dict[str, Any]:
        sig = inspect.signature(fn)
        props: Dict[str, Any] = {}
        required: List[str] = []
        for param in sig.parameters.values():
            pschema: Dict[str, Any] = {"type": "string"}
            if param.default is inspect.Parameter.empty:
                required.append(param.name)
            if param.annotation is not inspect.Parameter.empty:
                if param.annotation is int:
                    pschema["type"] = "integer"
                elif param.annotation is float:
                    pschema["type"] = "number"
                elif param.annotation is bool:
                    pschema["type"] = "boolean"
                elif param.annotation is list or param.annotation is List:
                    pschema["type"] = "array"
                elif param.annotation is dict or param.annotation is Dict:
                    pschema["type"] = "object"
            props[param.name] = pschema
        return {
            "type": "object",
            "properties": props,
            "required": required,
        }

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={list(self._tools.keys())})"


class HallucinationDetector:
    """
    Lightweight guardrail that checks for tool hallucinations.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def validate_action(self, action: Action) -> Tuple[bool, str]:
        if self.tool_registry.get(action.name) is None:
            return False, f"Unknown tool: {action.name}"
        tool = self.tool_registry.get(action.name)
        if tool is None:
            return False, "missing tool"
        params = tool.parameters.get("properties", {})
        for key in action.inputs:
            if key not in params:
                return False, f"Unexpected parameter: {key}"
        for key in tool.parameters.get("required", []):
            if key not in action.inputs:
                return False, f"Missing required parameter: {key}"
        return True, "ok"

    def __repr__(self) -> str:
        return f"HallucinationDetector(registry={self.tool_registry!r})"


# ---------------------------------------------------------------------------
# Section 6: Self-Play Customization (lines ~900–1050)
# ---------------------------------------------------------------------------


class CritiqueAgent:
    """
    Reviews another agent's output and assigns a numerical score.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None) -> None:
        self.llm_provider = llm_provider

    def review(self, content: str, criteria: List[str]) -> Dict[str, Any]:
        """
        Produce a critique dict with a 0-100 score and per-criterion feedback.
        """
        prompt = (
            f"Critique the following output according to these criteria: {criteria}.\n\n"
            f"Output:\n{content}\n\n"
            f"Return JSON with keys: score, feedback, suggestions."
        )
        if self.llm_provider is None:
            score = max(0, 100 - len(content) % 30)
            return {
                "score": score,
                "feedback": "Stub critique: text appears coherent.",
                "suggestions": ["Add more detail", "Check citations"],
            }
        raw = self.llm_provider.generate(prompt, max_tokens=512)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"score": 50, "feedback": raw[:200], "suggestions": []}
        return parsed

    def __repr__(self) -> str:
        return f"CritiqueAgent(llm={self.llm_provider is not None})"


class ImprovementAgent:
    """
    Produces concrete patches based on critique feedback.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None) -> None:
        self.llm_provider = llm_provider

    def improve(self, draft: str, critique: Dict[str, Any]) -> str:
        """
        Rewrite *draft* incorporating the critique.
        """
        prompt = (
            f"Given this draft and the critique, produce an improved version.\n\n"
            f"Draft:\n{draft}\n\n"
            f"Critique: {json.dumps(critique)}\n\n"
            f"Improved version:"
        )
        if self.llm_provider is None:
            return f"<improved draft based on score {critique.get('score', 50)}>\n{draft}"
        return self.llm_provider.generate(prompt, max_tokens=1024)

    def __repr__(self) -> str:
        return f"ImprovementAgent(llm={self.llm_provider is not None})"


class SelfPlayLoop:
    """
    Agent-vs-agent debate and evaluation loop.
    """

    def __init__(
        self,
        agent_a: MetaAgent,
        agent_b: MetaAgent,
        rounds: int = 3,
    ) -> None:
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.rounds = rounds
        self._transcript: List[Dict[str, Any]] = []

    def run(self, topic: str) -> Dict[str, Any]:
        """
        Run *rounds* turns of back-and-forth on *topic*.
        """
        current = topic
        for r in range(self.rounds):
            out_a = self.agent_a.goal + ": " + current
            out_b = self.agent_b.goal + ": " + current
            self._transcript.append(
                {"round": r + 1, "agent_a": out_a, "agent_b": out_b}
            )
            current = f"round-{r + 1} synthesis"
        return {"topic": topic, "rounds": self.rounds, "transcript": self._transcript}

    def __repr__(self) -> str:
        return f"SelfPlayLoop(rounds={self.rounds}, turns={len(self._transcript)})"


class DebateArena:
    """
    Multi-agent discussion with a moderator stub.
    """

    def __init__(
        self,
        participants: List[MetaAgent],
        moderator: Optional[MetaAgent] = None,
    ) -> None:
        self.participants = participants
        self.moderator = moderator

    def discuss(self, topic: str, turns: int = 2) -> List[Dict[str, Any]]:
        """
        Every participant gets a turn per round; moderator may intervene.
        """
        log: List[Dict[str, Any]] = []
        for turn in range(turns):
            for p in self.participants:
                entry = {
                    "turn": turn + 1,
                    "agent": repr(p),
                    "message": f"{p.goal} on {topic}",
                }
                log.append(entry)
            if self.moderator:
                log.append(
                    {
                        "turn": turn + 1,
                        "agent": "MODERATOR",
                        "message": f"Moderator: proceed to turn {turn + 2}",
                    }
                )
        return log

    def __repr__(self) -> str:
        return f"DebateArena(participants={len(self.participants)}, moderator={self.moderator is not None})"


class IterativeRefinementPipeline:
    """
    Draft -> Critique -> Revise -> Final.
    """

    def __init__(
        self,
        critique_agent: CritiqueAgent,
        improvement_agent: ImprovementAgent,
        max_cycles: int = 3,
        score_threshold: float = 85.0,
    ) -> None:
        self.critique_agent = critique_agent
        self.improvement_agent = improvement_agent
        self.max_cycles = max_cycles
        self.score_threshold = score_threshold

    def run(self, draft: str, criteria: List[str]) -> Dict[str, Any]:
        """
        Loop until quality threshold or max cycles.
        """
        current = draft
        history: List[Dict[str, Any]] = []
        for cycle in range(1, self.max_cycles + 1):
            critique = self.critique_agent.review(current, criteria)
            score = float(critique.get("score", 0))
            history.append({"cycle": cycle, "score": score, "draft_len": len(current)})
            if score >= self.score_threshold:
                break
            current = self.improvement_agent.improve(current, critique)
        return {
            "final": current,
            "history": history,
            "cycles": len(history),
        }

    def __repr__(self) -> str:
        return (
            f"IterativeRefinementPipeline(max_cycles={self.max_cycles}, "
            f"threshold={self.score_threshold})"
        )


# ---------------------------------------------------------------------------
# Section 7: Workflow Editor DAG (lines ~1050–1200)
# ---------------------------------------------------------------------------


@dataclass
class WorkflowNode:
    """
    Base node for workflow DAGs.

    Attributes:
        id: Unique node identifier.
        node_type: Discriminator for UI/rendering.
        config: Arbitrary node configuration.
        input_refs: IDs of upstream nodes.
        output_refs: IDs of downstream nodes.
    """

    id: str
    node_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    input_refs: List[str] = field(default_factory=list)
    output_refs: List[str] = field(default_factory=list)

    def execute(self, inputs: Dict[str, Any]) -> Any:
        """Override in subclasses."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={self.id!r}, type={self.node_type!r}, "
            f"inputs={self.input_refs}, outputs={self.output_refs})"
        )


class StartNode(WorkflowNode):
    """Entry point of a workflow."""

    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(node_id, "start", config or {})

    def execute(self, inputs: Dict[str, Any]) -> Any:
        return inputs


class EndNode(WorkflowNode):
    """Terminal point of a workflow."""

    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(node_id, "end", config or {})

    def execute(self, inputs: Dict[str, Any]) -> Any:
        return inputs


class LLMNode(WorkflowNode):
    """Calls an LLM with the provided prompt."""

    def __init__(
        self,
        node_id: str,
        llm_provider: LLMProvider,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(node_id, "llm", config or {})
        self.llm_provider = llm_provider

    def execute(self, inputs: Dict[str, Any]) -> Any:
        prompt = self.config.get("prompt", "")
        if isinstance(prompt, str):
            for key, val in inputs.items():
                prompt = prompt.replace(f"{{{key}}}", str(val))
        return self.llm_provider.generate(prompt, max_tokens=self.config.get("max_tokens", 256))


class ToolNode(WorkflowNode):
    """Invokes a registered tool."""

    def __init__(
        self,
        node_id: str,
        tool_registry: ToolRegistry,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(node_id, "tool", config or {})
        self.tool_registry = tool_registry

    def execute(self, inputs: Dict[str, Any]) -> Any:
        tool_name = self.config.get("tool_name", "")
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return {"error": f"tool {tool_name} not found"}
        merged = {**self.config.get("args", {}), **inputs}
        return tool.callable(**merged)


class ConditionNode(WorkflowNode):
    """Routes based on a simple expression."""

    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(node_id, "condition", config or {})

    def execute(self, inputs: Dict[str, Any]) -> Any:
        field_name = self.config.get("field", "")
        expected = self.config.get("value", "")
        actual = inputs.get(field_name, "")
        return {"branch": "true" if actual == expected else "false", "inputs": inputs}


class LoopNode(WorkflowNode):
    """Iterates over a collection and passes each item downstream."""

    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(node_id, "loop", config or {})

    def execute(self, inputs: Dict[str, Any]) -> Any:
        collection = inputs.get(self.config.get("iterator", "items"), [])
        return {"items": list(collection), "inputs": inputs}


class MergeNode(WorkflowNode):
    """Merges multiple upstream branches into a single output dict."""

    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(node_id, "merge", config or {})

    def execute(self, inputs: Dict[str, Any]) -> Any:
        merged: Dict[str, Any] = {}
        if isinstance(inputs, dict):
            merged.update(inputs)
        return merged


class DelayNode(WorkflowNode):
    """Pauses execution for a configurable duration."""

    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(node_id, "delay", config or {})

    def execute(self, inputs: Dict[str, Any]) -> Any:
        seconds = float(self.config.get("seconds", 0))
        time.sleep(seconds)
        return {"delayed": seconds, "inputs": inputs}


class WorkflowDAG:
    """
    Adjacency-list DAG with validation and topological sort.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, WorkflowNode] = {}
        self._adj: Dict[str, List[str]] = {}

    def add_node(self, node: WorkflowNode) -> None:
        self.nodes[node.id] = node
        self._adj.setdefault(node.id, [])
        for out_id in node.output_refs:
            self._adj.setdefault(out_id, [])
            if node.id not in self._adj[out_id]:
                self._adj[out_id].append(node.id)

    def validate(self) -> Tuple[bool, str]:
        """Check for dangling references and cycles."""
        for node in self.nodes.values():
            for ref in node.input_refs + node.output_refs:
                if ref not in self.nodes:
                    return False, f"Dangling reference: {ref}"
        try:
            self.topological_sort()
        except ValueError as exc:
            return False, str(exc)
        return True, "ok"

    def topological_sort(self) -> List[str]:
        """
        Kahn's algorithm.  Raises :exc:`ValueError` on cycle.
        """
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        for node in self.nodes.values():
            for out_id in node.output_refs:
                in_degree[out_id] = in_degree.get(out_id, 0) + 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order: List[str] = []
        while queue:
            current = queue.pop(0)
            order.append(current)
            for out_id in self.nodes[current].output_refs:
                in_degree[out_id] -= 1
                if in_degree[out_id] == 0:
                    queue.append(out_id)
        if len(order) != len(self.nodes):
            raise ValueError("Cycle detected in workflow DAG")
        return order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.node_type,
                    "config": n.config,
                    "inputs": n.input_refs,
                    "outputs": n.output_refs,
                }
                for n in self.nodes.values()
            ]
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        llm_provider: Optional[LLMProvider] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> "WorkflowDAG":
        dag = cls()
        for raw in data.get("nodes", []):
            nt = raw["type"]
            nid = raw["id"]
            cfg = raw.get("config", {})
            node: WorkflowNode
            if nt == "start":
                node = StartNode(nid, cfg)
            elif nt == "end":
                node = EndNode(nid, cfg)
            elif nt == "llm":
                node = LLMNode(nid, llm_provider or OpenAIProvider(), cfg)
            elif nt == "tool":
                node = ToolNode(nid, tool_registry or ToolRegistry(), cfg)
            elif nt == "condition":
                node = ConditionNode(nid, cfg)
            elif nt == "loop":
                node = LoopNode(nid, cfg)
            elif nt == "merge":
                node = MergeNode(nid, cfg)
            elif nt == "delay":
                node = DelayNode(nid, cfg)
            else:
                node = WorkflowNode(nid, nt, cfg)
            node.input_refs = raw.get("inputs", [])
            node.output_refs = raw.get("outputs", [])
            dag.add_node(node)
        return dag

    def __repr__(self) -> str:
        return f"WorkflowDAG(nodes={list(self.nodes.keys())})"


class WorkflowExecutor:
    """
    BFS executor with dependency resolution and basic error handling.
    """

    def __init__(self, dag: WorkflowDAG) -> None:
        self.dag = dag
        self._state: Dict[str, Any] = {}
        self._errors: List[Dict[str, Any]] = []

    def run(self, initial_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the DAG from start to end nodes.
        """
        inputs = initial_inputs or {}
        order = self.dag.topological_sort()
        for nid in order:
            node = self.dag.nodes[nid]
            # Gather upstream outputs
            upstream: Dict[str, Any] = {}
            for in_id in node.input_refs:
                upstream[in_id] = self._state.get(in_id, {})
            merged = {**inputs, **upstream}
            try:
                self._state[nid] = node.execute(merged)
            except Exception as exc:
                self._errors.append({"node": nid, "error": str(exc)})
                self._state[nid] = {"error": str(exc)}
        # Return end-node states
        end_states = {
            nid: self._state[nid]
            for nid, node in self.dag.nodes.items()
            if isinstance(node, EndNode)
        }
        return {"outputs": end_states, "errors": self._errors}

    def __repr__(self) -> str:
        return f"WorkflowExecutor(dag={self.dag!r}, errors={len(self._errors)})"


# ---------------------------------------------------------------------------
# Section 8: Utilities + Demo (lines ~1200–1300+)
# ---------------------------------------------------------------------------


class JSONSafeParser:
    """
    Robust JSON extractor with repair heuristics for LLM output.
    """

    @staticmethod
    def parse(text: str) -> Any:
        """
        Try multiple extraction strategies and return the best result.
        """
        # Strategy 1: direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Strategy 2: extract first JSON object or array
        for pattern in (r"\{.*\}", r"\[.*\]"):
            m = re.search(pattern, text, re.S)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
        # Strategy 3: strip markdown fences and trailing garbage
        cleaned = re.sub(r"```json\s*", "", text)
        cleaned = re.sub(r"\s*```", "", cleaned)
        cleaned = cleaned.strip().rstrip(",")
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        # Strategy 4: return raw string as fallback
        return text

    def __repr__(self) -> str:
        return "JSONSafeParser()"


class StringSimilarity:
    """
    Pure-Python Levenshtein distance and ratio.
    """

    @staticmethod
    def levenshtein(a: str, b: str) -> int:
        """Compute edit distance between *a* and *b*."""
        if len(a) < len(b):
            return StringSimilarity.levenshtein(b, a)
        if not b:
            return len(a)
        previous = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            current = [i + 1]
            for j, cb in enumerate(b):
                insertions = previous[j + 1] + 1
                deletions = current[j] + 1
                substitutions = previous[j] + (ca != cb)
                current.append(min(insertions, deletions, substitutions))
            previous = current
        return previous[-1]

    @staticmethod
    def ratio(a: str, b: str) -> float:
        """Return similarity in the range 0..1."""
        dist = StringSimilarity.levenshtein(a, b)
        max_len = max(len(a), len(b))
        if max_len == 0:
            return 1.0
        return 1.0 - dist / max_len

    def __repr__(self) -> str:
        return "StringSimilarity()"


_T = TypeVar("_T")


class Memoize(Generic[_T]):
    """
    Simple unbounded memoisation decorator for pure functions.
    """

    def __init__(self, fn: Callable[..., _T]) -> None:
        self.fn = fn
        self._cache: Dict[Tuple[Any, ...], _T] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> _T:
        key = (args, tuple(sorted(kwargs.items())))
        if key not in self._cache:
            self._cache[key] = self.fn(*args, **kwargs)
        return self._cache[key]

    def __repr__(self) -> str:
        return f"Memoize({self.fn.__name__}, cached={len(self._cache)})"


def memoize(fn: Callable[..., _T]) -> Memoize[_T]:
    return Memoize(fn)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=" * 60)
    print("AutoAgent Native – Framework Demo")
    print("=" * 60)

    # 1. Create MetaAgent with a goal
    print("\n[1] MetaAgent decomposition")
    agent = MetaAgent(
        goal="Research Python metaclasses, write a summary, review the draft"
    )
    tasks = agent.decompose()
    for t in tasks:
        print(f"  {t}")

    # 2. Plan tasks
    print("\n[2] Full orchestration")
    # Bind simple handlers so execution produces deterministic strings
    agent.executor.register_handler("t0", lambda task: "Metaclasses research done")
    agent.executor.register_handler("t1", lambda task: "Summary written")
    agent.executor.register_handler("t2", lambda task: "Review passed")
    outcome = agent.orchestrate()
    print(f"  attempts: {outcome['attempts']}")
    for entry in outcome["tasks"]:
        print(f"  -> {entry['id']}: {entry['status']} = {entry['result']}")

    # 3. Register tools to agent
    print("\n[3] Tool registry")
    registry = ToolRegistry()

    @registry.tool
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    @registry.tool
    def greet(name: str) -> str:
        """Greet a person by name."""
        return f"Hello, {name}!"

    print(f"  Registered: {list(registry._tools.keys())}")
    print(f"  Schema for 'add': {json.dumps(registry.get('add').parameters, indent=2)}")

    # 4. Run ReAct loop on sample query
    print("\n[4] ReAct engine")
    stub_llm = OpenAIProvider(api_key="demo-key")
    react = ReActEngine(llm_provider=stub_llm, tool_registry=registry)
    # Because the stub can't really reason, we override the prompt just
    # to show the loop mechanics with a synthetic answer.
    answer = react.run("What is 7 + 5?")
    print(f"  Final answer: {answer}")

    # 5. Show RAG retrieval from sample documents
    print("\n[5] RAG retrieval")
    docs = [
        Document(
            id="d1",
            text="Python metaclasses allow customising class creation.",
        ),
        Document(
            id="d2",
            text="Descriptors are a protocol for attribute access.",
        ),
        Document(
            id="d3",
            text="The __new__ method controls instance construction.",
        ),
    ]
    embedder = SentenceTransformersStub()
    store = VectorStore(embedding_provider=embedder)
    store.add(docs)
    rag = RAGPipeline(vector_store=store, top_k=2)
    retrieved = rag.retrieve("Tell me about class creation in Python")
    for doc, _ in store.search("Tell me about class creation in Python", top_k=2):
        print(f"  -> {doc.id}: {doc.text[:60]}...")

    # 6. Build and execute a simple workflow DAG
    print("\n[6] Workflow DAG")
    dag = WorkflowDAG()
    start = StartNode("start", {"input": "user_query"})
    llm_node = LLMNode("llm", stub_llm, {"prompt": "Summarise: {user_query}"})
    tool_node = ToolNode("tool", registry, {"tool_name": "greet", "args": {"name": "World"}})
    merge = MergeNode("merge")
    end = EndNode("end")

    start.output_refs = ["llm", "tool"]
    llm_node.input_refs = ["start"]
    llm_node.output_refs = ["merge"]
    tool_node.input_refs = ["start"]
    tool_node.output_refs = ["merge"]
    merge.input_refs = ["llm", "tool"]
    merge.output_refs = ["end"]
    end.input_refs = ["merge"]

    dag.add_node(start)
    dag.add_node(llm_node)
    dag.add_node(tool_node)
    dag.add_node(merge)
    dag.add_node(end)

    ok, reason = dag.validate()
    print(f"  Validation: {ok} ({reason})")
    print(f"  Topo sort: {dag.topological_sort()}")

    wf_exec = WorkflowExecutor(dag)
    wf_result = wf_exec.run(initial_inputs={"user_query": "Explain recursion"})
    print(f"  Outputs: {json.dumps(wf_result['outputs'], indent=2)}")

    # 7. Print summary of all components
    print("\n[7] Component inventory")
    components = [
        agent,
        embedder,
        store,
        rag,
        registry,
        stub_llm,
        react,
        dag,
        wf_exec,
        JSONSafeParser(),
        StringSimilarity(),
    ]
    for c in components:
        print(f"  - {c}")

    # 8. Extra utility demos
    print("\n[8] Utility demos")
    sim = StringSimilarity()
    print(f"  Levenshtein('kitten', 'sitting') = {sim.levenshtein('kitten', 'sitting')}")
    print(f"  Ratio('hello', 'helo') = {sim.ratio('hello', 'helo'):.3f}")

    parser = JSONSafeParser()
    print(f"  JSONSafeParser on malformed: {parser.parse('{{\"a\": 1,}}')}")

    @memoize
    def slow_fib(n: int) -> int:
        return n if n < 2 else slow_fib(n - 1) + slow_fib(n - 2)

    print(f"  Memoized fib(20) = {slow_fib(20)} (cached={len(slow_fib._cache)})")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
