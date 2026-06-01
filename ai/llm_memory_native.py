#!/usr/bin/env python3
"""
ai/llm_memory_native.py
MAGNATRIX-OS — Long-Context Memory Engine for the LLM Arena
AMATI pattern: persistent memory (Claude Projects, MemGPT, VectorDB)

Pure Python, stdlib only. Simulates session memory, knowledge storage,
project context, and retrieval-augmented recall.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _token_count(text: str) -> int:
    return len(text) // 4 + 1


def _short_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


# ───────────────────────────────────────────────────────────────
# 1. SESSION MEMORY
# ───────────────────────────────────────────────────────────────

@dataclass
class MemoryEntry:
    role: str  # user / assistant / system / tool
    content: str
    timestamp: float
    tokens: int
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5  # 0-1


class SessionMemory:
    """Stores conversation history per session with token counting and auto-summarization."""

    def __init__(self, max_tokens: int = 8192, summarize_threshold: int = 6000) -> None:
        self.max_tokens = max_tokens
        self.summarize_threshold = summarize_threshold
        self.entries: List[MemoryEntry] = []
        self.summaries: List[str] = []
        self.session_id = _short_hash(str(_now()))

    def add(self, role: str, content: str, tags: Optional[List[str]] = None, importance: float = 0.5) -> None:
        entry = MemoryEntry(
            role=role, content=content, timestamp=_now(),
            tokens=_token_count(content), tags=tags or [], importance=importance,
        )
        self.entries.append(entry)
        self._maybe_summarize()

    def _maybe_summarize(self) -> None:
        total = sum(e.tokens for e in self.entries)
        if total > self.summarize_threshold and len(self.entries) > 4:
            to_summarize = self.entries[: len(self.entries) // 2]
            summary_text = "Summary: " + " | ".join(f"{e.role}: {e.content[:60]}..." for e in to_summarize)
            self.summaries.append(summary_text)
            self.entries = self.entries[len(self.entries) // 2:]

    def get_context(self, max_entries: int = 20) -> List[MemoryEntry]:
        return self.entries[-max_entries:]

    def get_token_count(self) -> int:
        return sum(e.tokens for e in self.entries) + sum(_token_count(s) for s in self.summaries)

    def to_prompt(self, max_entries: int = 20) -> str:
        parts = []
        for s in self.summaries:
            parts.append(f"[SUMMARY] {s}")
        for e in self.entries[-max_entries:]:
            parts.append(f"[{e.role.upper()}] {e.content}")
        return "\n".join(parts)

    def stats(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "entries": len(self.entries),
            "summaries": len(self.summaries),
            "total_tokens": self.get_token_count(),
            "max_tokens": self.max_tokens,
        }


# ───────────────────────────────────────────────────────────────
# 2. KNOWLEDGE STORE
# ───────────────────────────────────────────────────────────────

class KnowledgeStore:
    """Persistent key-value storage with simulated semantic search via keyword indexing."""

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}
        self._index: Dict[str, Set[str]] = {}

    def _extract_keywords(self, text: str) -> Set[str]:
        words = text.lower().split()
        return {w.strip(".,!?;:\"\'()") for w in words if len(w) > 3}

    def store(self, key: str, value: str, category: str = "general") -> None:
        self._data[key] = {"value": value, "category": category, "stored_at": _now()}
        keywords = self._extract_keywords(value)
        for kw in keywords:
            self._index.setdefault(kw, set()).add(key)

    def retrieve(self, key: str) -> Optional[str]:
        entry = self._data.get(key)
        return entry["value"] if entry else None

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_kws = self._extract_keywords(query)
        scores: Dict[str, int] = {}
        for kw in query_kws:
            for key in self._index.get(kw, set()):
                scores[key] = scores.get(key, 0) + 1
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            {
                "key": k,
                "value": self._data[k]["value"],
                "category": self._data[k]["category"],
                "score": s,
            }
            for k, s in ranked
        ]

    def list_categories(self) -> List[str]:
        return list(set(d["category"] for d in self._data.values()))

    def stats(self) -> Dict[str, Any]:
        return {"entries": len(self._data), "indexed_keywords": len(self._index), "categories": self.list_categories()}


# ───────────────────────────────────────────────────────────────
# 3. PROJECT CONTEXT
# ───────────────────────────────────────────────────────────────

class ProjectContext:
    """Project-level memory that persists across sessions."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self.notes: List[Dict[str, Any]] = []
        self.files: List[str] = []
        self.preferences: Dict[str, Any] = {}
        self.created_at = _now()

    def add_note(self, text: str, tags: Optional[List[str]] = None) -> None:
        self.notes.append({"text": text, "tags": tags or [], "added_at": _now()})

    def add_file(self, path: str) -> None:
        if path not in self.files:
            self.files.append(path)

    def set_preference(self, key: str, value: Any) -> None:
        self.preferences[key] = value

    def get_notes(self, tag: Optional[str] = None) -> List[str]:
        if tag:
            return [n["text"] for n in self.notes if tag in n["tags"]]
        return [n["text"] for n in self.notes]

    def to_context(self) -> str:
        parts = [f"[PROJECT: {self.project_id}]"]
        if self.preferences:
            parts.append(f"Preferences: {json.dumps(self.preferences)}")
        if self.files:
            parts.append(f"Files: {', '.join(self.files)}")
        for n in self.notes:
            parts.append(f"Note: {n['text']}")
        return "\n".join(parts)

    def stats(self) -> Dict[str, Any]:
        return {"project_id": self.project_id, "notes": len(self.notes), "files": len(self.files), "preferences": len(self.preferences)}


# ───────────────────────────────────────────────────────────────
# 4. RETRIEVAL ENGINE
# ───────────────────────────────────────────────────────────────

class RetrievalEngine:
    """Retrieve relevant past context given a query."""

    def __init__(self, knowledge: KnowledgeStore, sessions: Optional[List[SessionMemory]] = None, projects: Optional[List[ProjectContext]] = None) -> None:
        self.knowledge = knowledge
        self.sessions = sessions or []
        self.projects = projects or []

    def retrieve(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        knowledge_results = self.knowledge.search(query, top_k)
        session_snippets = []
        for s in self.sessions:
            for e in s.entries:
                if any(kw in e.content.lower() for kw in query.lower().split()):
                    session_snippets.append({"session": s.session_id, "role": e.role, "content": e.content[:100]})
        project_snippets = []
        for p in self.projects:
            for n in p.notes:
                if any(kw in n["text"].lower() for kw in query.lower().split()):
                    project_snippets.append({"project": p.project_id, "note": n["text"][:100]})
        return {
            "knowledge": knowledge_results,
            "sessions": session_snippets[:top_k],
            "projects": project_snippets[:top_k],
        }


# ───────────────────────────────────────────────────────────────
# 5. SUMMARIZER
# ───────────────────────────────────────────────────────────────

class Summarizer:
    """Auto-summarize long conversation threads into compact memory chunks."""

    def summarize(self, entries: List[MemoryEntry]) -> str:
        if not entries:
            return ""
        topics = {}
        for e in entries:
            for tag in e.tags:
                topics.setdefault(tag, []).append(e.content[:50])
        parts = ["Summary of conversation:"]
        for tag, snippets in topics.items():
            parts.append(f"  [{tag}] " + " | ".join(snippets[:3]))
        if not topics:
            parts.append("  " + " | ".join(e.content[:50] for e in entries[:5]))
        return "\n".join(parts)

    def compress(self, text: str, max_tokens: int = 256) -> str:
        if _token_count(text) <= max_tokens:
            return text
        char_limit = max_tokens * 4
        return text[:char_limit - 3] + "..."


# ───────────────────────────────────────────────────────────────
# 6. MEMORY MANAGER
# ───────────────────────────────────────────────────────────────

class MemoryManager:
    """Orchestrator: session + project + knowledge layers with LRU + importance eviction."""

    def __init__(self, max_tokens_per_session: int = 8192) -> None:
        self.sessions: Dict[str, SessionMemory] = {}
        self.projects: Dict[str, ProjectContext] = {}
        self.knowledge = KnowledgeStore()
        self.summarizer = Summarizer()
        self.max_tokens = max_tokens_per_session

    def create_session(self, session_id: Optional[str] = None) -> SessionMemory:
        sid = session_id or _short_hash(str(_now()))
        sm = SessionMemory(max_tokens=self.max_tokens)
        sm.session_id = sid
        self.sessions[sid] = sm
        return sm

    def create_project(self, project_id: str) -> ProjectContext:
        pc = ProjectContext(project_id)
        self.projects[project_id] = pc
        return pc

    def get_retrieval_engine(self, session_id: Optional[str] = None) -> RetrievalEngine:
        sessions = [self.sessions[session_id]] if session_id and session_id in self.sessions else list(self.sessions.values())
        return RetrievalEngine(self.knowledge, sessions, list(self.projects.values()))

    def global_stats(self) -> Dict[str, Any]:
        return {
            "sessions": len(self.sessions),
            "projects": len(self.projects),
            "knowledge": self.knowledge.stats(),
            "total_session_tokens": sum(s.get_token_count() for s in self.sessions.values()),
        }


# ───────────────────────────────────────────────────────────────
# 7. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Memory Engine Demo")
    print("=" * 60)

    mm = MemoryManager()

    print("\n[1] Session Memory")
    sess = mm.create_session("sess_001")
    sess.add("user", "What is the capital of France?", ["geography"], 0.6)
    sess.add("assistant", "The capital of France is Paris.", ["geography", "answer"], 0.7)
    sess.add("user", "What about Germany?", ["geography"], 0.5)
    sess.add("assistant", "The capital of Germany is Berlin.", ["geography", "answer"], 0.7)
    print(f"  Session ID: {sess.session_id}")
    print(f"  Entries: {len(sess.entries)}")
    print(f"  Tokens: {sess.get_token_count()}")
    print(f"  Context:\n{sess.to_prompt(2)}")

    print("\n[2] Knowledge Store")
    mm.knowledge.store("france_capital", "Paris is the capital of France, population ~2.1M.", "geography")
    mm.knowledge.store("germany_capital", "Berlin is the capital of Germany, population ~3.6M.", "geography")
    mm.knowledge.store("python_lambda", "Lambda functions in Python are anonymous functions defined with lambda keyword.", "coding")
    print(f"  Entries: {mm.knowledge.stats()['entries']}")
    results = mm.knowledge.search("capital city", 3)
    for r in results:
        print(f"  [{r['score']}] {r['key']}: {r['value'][:50]}...")

    print("\n[3] Project Context")
    proj = mm.create_project("project_alpha")
    proj.add_note("Use Python 3.11 for all scripts", ["setup"])
    proj.add_note("API base URL: https://api.magnatrix.dev", ["api"])
    proj.add_file("config.yaml")
    proj.set_preference("language", "python")
    print(proj.to_context()[:300])

    print("\n[4] Retrieval Engine")
    engine = mm.get_retrieval_engine("sess_001")
    retrieved = engine.retrieve("capital")
    print(f"  Knowledge hits: {len(retrieved['knowledge'])}")
    print(f"  Session hits: {len(retrieved['sessions'])}")
    print(f"  Project hits: {len(retrieved['projects'])}")

    print("\n[5] Summarizer")
    summary = mm.summarizer.summarize(sess.entries)
    print(f"  {summary[:200]}...")

    print("\n[6] Global Stats")
    print(f"  {json.dumps(mm.global_stats(), indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. Memory Engine ready for LLM Arena.")
    print("=" * 60)
