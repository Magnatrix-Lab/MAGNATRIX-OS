"""Conversation Manager — Thread lifecycle, context window, memory injection.

Modul ini menyediakan:
- ConversationThread untuk manajemen sesi percakapan
- ContextWindow untuk sliding window dan token estimation
- MemoryInjector untuk RAG-based memory augmentation
- ThreadArchive untuk persistent storage dan retrieval
- ConversationRouter untuk routing ke model yang sesuai

Arsitektur: User → Thread → ContextWindow → MemoryInjector → Model → Response
"""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    MEMORY = "memory"


class ThreadStatus(Enum):
    ACTIVE = auto()
    PAUSED = auto()
    ARCHIVED = auto()
    EXPIRED = auto()


@dataclass
class ConversationMessage:
    """Single message in a conversation."""
    message_id: str
    role: MessageRole
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: int = 0

    def estimate_tokens(self) -> int:
        if self.tokens == 0:
            self.tokens = len(self.content.split()) + len(self.content) // 4
        return self.tokens


@dataclass
class MemoryFragment:
    """Retrieved memory fragment for context augmentation."""
    fragment_id: str
    content: str
    source: str
    relevance: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConversationThread:
    """Active conversation thread."""
    thread_id: str
    user_id: str
    title: str = ""
    status: ThreadStatus = ThreadStatus.ACTIVE
    messages: List[ConversationMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    max_window_tokens: int = 4096
    model_id: str = "default"

    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> ConversationMessage:
        msg = ConversationMessage(
            message_id=str(uuid.uuid4())[:12],
            role=role,
            content=content,
            metadata=metadata or {}
        )
        msg.estimate_tokens()
        self.messages.append(msg)
        self.last_active = time.time()
        # Prune if needed
        self._prune_if_needed()
        return msg

    def _prune_if_needed(self) -> None:
        total = sum(m.tokens for m in self.messages)
        while total > self.max_window_tokens and len(self.messages) > 2:
            removed = self.messages.pop(1)  # Keep system and first user
            total -= removed.tokens

    def get_window(self, include_system: bool = True) -> List[ConversationMessage]:
        result = []
        total = 0
        for msg in reversed(self.messages):
            if msg.role == MessageRole.SYSTEM and not include_system:
                continue
            if total + msg.tokens > self.max_window_tokens and result:
                break
            result.append(msg)
            total += msg.tokens
        return list(reversed(result))

    def summary(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "message_count": len(self.messages),
            "total_tokens": sum(m.tokens for m in self.messages),
            "status": self.status.name,
            "last_active": self.last_active,
            "model": self.model_id,
        }


class ContextWindow:
    """Manage context window size and token allocation."""

    def __init__(self, max_tokens: int = 4096, system_reserve: int = 500, response_reserve: int = 1000):
        self.max_tokens = max_tokens
        self.system_reserve = system_reserve
        self.response_reserve = response_reserve
        self.available = max_tokens - system_reserve - response_reserve

    def fit_messages(self, messages: List[ConversationMessage]) -> List[ConversationMessage]:
        total = 0
        result = []
        for msg in reversed(messages):
            if msg.role == MessageRole.SYSTEM:
                if total + msg.tokens <= self.system_reserve:
                    result.append(msg)
                    total += msg.tokens
                continue
            if total + msg.tokens <= self.available:
                result.append(msg)
                total += msg.tokens
            else:
                break
        return list(reversed(result))

    def token_count(self, messages: List[ConversationMessage]) -> int:
        return sum(m.tokens for m in messages)

    def set_budget(self, system: int, response: int) -> None:
        self.system_reserve = system
        self.response_reserve = response
        self.available = self.max_tokens - system - response


class MemoryInjector:
    """Inject relevant memories into conversation context."""

    def __init__(self, max_fragments: int = 3, min_relevance: float = 0.5):
        self.max_fragments = max_fragments
        self.min_relevance = min_relevance
        self._memories: Dict[str, List[MemoryFragment]] = {}  # user_id -> memories

    def store(self, user_id: str, content: str, source: str = "user") -> MemoryFragment:
        frag = MemoryFragment(
            fragment_id=str(uuid.uuid4())[:12],
            content=content,
            source=source,
            relevance=1.0
        )
        self._memories.setdefault(user_id, []).append(frag)
        return frag

    def retrieve(self, user_id: str, query: str, top_k: int = 3) -> List[MemoryFragment]:
        memories = self._memories.get(user_id, [])
        if not memories:
            return []
        # Simple keyword overlap scoring
        query_words = set(query.lower().split())
        scored = []
        for mem in memories:
            mem_words = set(mem.content.lower().split())
            overlap = len(query_words & mem_words)
            score = overlap / max(len(query_words), 1)
            mem.relevance = score
            if score >= self.min_relevance:
                scored.append((score, mem))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [m for _, m in scored[:top_k]]

    def inject(self, thread: ConversationThread, query: str) -> List[ConversationMessage]:
        frags = self.retrieve(thread.user_id, query)
        if not frags:
            return []
        memory_msgs = []
        for frag in frags:
            msg = ConversationMessage(
                message_id=frag.fragment_id,
                role=MessageRole.MEMORY,
                content=f"[Memory from {frag.source}] {frag.content}",
                metadata={"relevance": frag.relevance, "source": frag.source}
            )
            memory_msgs.append(msg)
        return memory_msgs

    def get_user_memories(self, user_id: str) -> List[MemoryFragment]:
        return self._memories.get(user_id, [])


class ThreadArchive:
    """Archive and retrieve conversation threads."""

    def __init__(self, max_active: int = 100):
        self.max_active = max_active
        self._active: Dict[str, ConversationThread] = {}
        self._archived: Dict[str, ConversationThread] = {}

    def create(self, user_id: str, title: str = "", model_id: str = "default") -> ConversationThread:
        tid = str(uuid.uuid4())[:12]
        thread = ConversationThread(
            thread_id=tid,
            user_id=user_id,
            title=title,
            model_id=model_id
        )
        self._active[tid] = thread
        return thread

    def get(self, thread_id: str) -> Optional[ConversationThread]:
        return self._active.get(thread_id) or self._archived.get(thread_id)

    def archive(self, thread_id: str) -> bool:
        thread = self._active.pop(thread_id, None)
        if thread:
            thread.status = ThreadStatus.ARCHIVED
            self._archived[thread_id] = thread
            return True
        return False

    def restore(self, thread_id: str) -> bool:
        thread = self._archived.pop(thread_id, None)
        if thread:
            thread.status = ThreadStatus.ACTIVE
            self._active[thread_id] = thread
            return True
        return False

    def list_active(self, user_id: Optional[str] = None) -> List[ConversationThread]:
        threads = list(self._active.values())
        if user_id:
            threads = [t for t in threads if t.user_id == user_id]
        return sorted(threads, key=lambda t: t.last_active, reverse=True)

    def list_archived(self, user_id: Optional[str] = None) -> List[ConversationThread]:
        threads = list(self._archived.values())
        if user_id:
            threads = [t for t in threads if t.user_id == user_id]
        return threads

    def export(self, thread_id: str) -> str:
        thread = self.get(thread_id)
        if not thread:
            return "{}"
        data = {
            "thread_id": thread.thread_id,
            "title": thread.title,
            "messages": [
                {"role": m.role.value, "content": m.content, "timestamp": m.timestamp}
                for m in thread.messages
            ],
            "metadata": thread.metadata
        }
        return json.dumps(data, indent=2)

    def cleanup_expired(self, max_age: float = 86400.0) -> int:
        now = time.time()
        expired = [tid for tid, t in self._active.items() if now - t.last_active > max_age]
        for tid in expired:
            self.archive(tid)
        return len(expired)


class ConversationRouter:
    """Route conversations to appropriate models based on task."""

    def __init__(self):
        self._routes: Dict[str, str] = {}  # capability -> model_id
        self._fallback: str = "default"

    def register(self, capability: str, model_id: str) -> None:
        self._routes[capability] = model_id

    def route(self, task_description: str) -> str:
        # Simple keyword-based routing
        task_lower = task_description.lower()
        for cap, model in self._routes.items():
            if cap in task_lower:
                return model
        return self._fallback

    def set_fallback(self, model_id: str) -> None:
        self._fallback = model_id

    def get_routes(self) -> Dict[str, str]:
        return dict(self._routes)


class ConversationManager:
    """End-to-end conversation manager."""

    def __init__(self, max_tokens: int = 4096):
        self.archive = ThreadArchive()
        self.window = ContextWindow(max_tokens=max_tokens)
        self.memory = MemoryInjector()
        self.router = ConversationRouter()

    def start_conversation(self, user_id: str, title: str = "", model_id: str = "default") -> ConversationThread:
        return self.archive.create(user_id, title, model_id)

    def send_message(self, thread_id: str, content: str, role: MessageRole = MessageRole.USER,
                     metadata: Optional[Dict[str, Any]] = None) -> Tuple[ConversationMessage, List[ConversationMessage]]:
        thread = self.archive.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        # Add user message
        user_msg = thread.add_message(role, content, metadata)

        # Inject memories
        memories = self.memory.inject(thread, content)

        # Get context window
        all_msgs = thread.get_window(include_system=True)
        if memories:
            all_msgs = all_msgs[:1] + memories + all_msgs[1:]  # System, memories, rest
        fitted = self.window.fit_messages(all_msgs)

        return user_msg, fitted

    def add_response(self, thread_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> ConversationMessage:
        thread = self.archive.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")
        return thread.add_message(MessageRole.ASSISTANT, content, metadata)

    def store_memory(self, user_id: str, content: str, source: str = "user") -> MemoryFragment:
        return self.memory.store(user_id, content, source)

    def get_thread_summary(self, thread_id: str) -> Optional[Dict[str, Any]]:
        thread = self.archive.get(thread_id)
        return thread.summary() if thread else None

    def get_user_threads(self, user_id: str) -> List[ConversationThread]:
        return self.archive.list_active(user_id)

    def export_conversation(self, thread_id: str) -> str:
        return self.archive.export(thread_id)

    def cleanup(self, max_age: float = 86400.0) -> int:
        return self.archive.cleanup_expired(max_age)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CONVERSATION MANAGER DEMO")
    print("=" * 70)

    manager = ConversationManager(max_tokens=4096)

    # 1. Start conversation
    print("\n[1] Start Conversation")
    thread = manager.start_conversation("user-123", "Python Help", model_id="llama-70b")
    print(f"  Thread: {thread.thread_id}")
    print(f"  Summary: {thread.summary()}")

    # 2. Add messages
    print("\n[2] Add Messages")
    manager.send_message(thread.thread_id, "How do I optimize Python loops?")
    manager.add_response(thread.thread_id, "Use list comprehensions and vectorization with numpy.")
    manager.send_message(thread.thread_id, "What about parallel processing?")
    manager.add_response(thread.thread_id, "Use multiprocessing for CPU-bound tasks.")
    print(f"  Messages: {len(thread.messages)}")
    print(f"  Total tokens: {sum(m.tokens for m in thread.messages)}")

    # 3. Context window
    print("\n[3] Context Window")
    window = manager.window
    fitted = window.fit_messages(thread.messages)
    print(f"  Fitted {len(fitted)} messages (total: {window.token_count(fitted)} tokens)")

    # 4. Memory injection
    print("\n[4] Memory Injection")
    manager.store_memory("user-123", "User prefers Python over JavaScript", "preference")
    manager.store_memory("user-123", "User works on data science projects", "profile")
    mems = manager.memory.retrieve("user-123", "Python data processing")
    print(f"  Retrieved {len(mems)} memories")
    for m in mems:
        print(f"    [{m.relevance:.2f}] {m.content[:50]}...")

    # 5. Memory injection into thread
    print("\n[5] Memory Injection into Thread")
    user_msg, context = manager.send_message(thread.thread_id, "Best tools for data analysis?")
    memory_msgs = [m for m in context if m.role == MessageRole.MEMORY]
    print(f"  Context messages: {len(context)}")
    print(f"  Memory messages injected: {len(memory_msgs)}")

    # 6. Thread archive
    print("\n[6] Thread Archive")
    manager.archive.archive(thread.thread_id)
    print(f"  Active threads: {len(manager.archive.list_active())}")
    print(f"  Archived threads: {len(manager.archive.list_archived())}")
    manager.archive.restore(thread.thread_id)
    print(f"  After restore - Active: {len(manager.archive.list_active())}")

    # 7. Export
    print("\n[7] Export Conversation")
    export = manager.export_conversation(thread.thread_id)
    print(f"  Export size: {len(export)} chars")

    # 8. Router
    print("\n[8] Conversation Router")
    manager.router.register("code", "codellama-34b")
    manager.router.register("math", "deepseek-math")
    manager.router.register("creative", "stablelm-7b")
    print(f"  Route 'write Python': {manager.router.route('write Python function')}")
    print(f"  Route 'solve equation': {manager.router.route('solve math equation')}")
    print(f"  Route 'write poem': {manager.router.route('write creative poem')}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
