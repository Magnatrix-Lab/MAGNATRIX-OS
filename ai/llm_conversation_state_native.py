"""
llm_conversation_state_native.py
MAGNATRIX-OS Conversation State Engine
Native Python, stdlib only.
Provides conversation state management, persistence, branching, and rollback.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class ConversationStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class Message:
    role: str
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "content": self.content[:100], "timestamp": self.timestamp, "metadata": self.metadata}


@dataclass
class ConversationState:
    conversation_id: str
    messages: List[Message] = field(default_factory=list)
    status: ConversationStatus = ConversationStatus.ACTIVE
    context: Dict[str, Any] = field(default_factory=dict)
    branches: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id, "status": self.status.value,
            "message_count": len(self.messages), "context": self.context,
            "parent_id": self.parent_id, "created_at": self.created_at,
            "updated_at": self.updated_at, "tags": self.tags,
        }

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = time.time()

    def get_last_n(self, n: int) -> List[Message]:
        return self.messages[-n:]

    def get_token_estimate(self, chars_per_token: float = 4.0) -> int:
        total_chars = sum(len(m.content) for m in self.messages)
        return int(total_chars / chars_per_token)

    def fork(self, new_id: str) -> ConversationState:
        return ConversationState(
            conversation_id=new_id, messages=list(self.messages), status=ConversationStatus.ACTIVE,
            context=dict(self.context), parent_id=self.conversation_id, tags=list(self.tags)
        )

    def rollback(self, message_count: int) -> bool:
        if message_count >= len(self.messages):
            return False
        self.messages = self.messages[:message_count]
        self.updated_at = time.time()
        return True


class ConversationStateEngine:
    """Conversation state management with persistence and branching."""

    def __init__(self) -> None:
        self._conversations: Dict[str, ConversationState] = {}
        self._handlers: List[Callable[[ConversationState], None]] = []

    def create(self, conversation_id: str, parent_id: Optional[str] = None,
               context: Optional[Dict[str, Any]] = None) -> ConversationState:
        state = ConversationState(
            conversation_id=conversation_id, parent_id=parent_id, context=context or {}
        )
        self._conversations[conversation_id] = state
        return state

    def get(self, conversation_id: str) -> Optional[ConversationState]:
        return self._conversations.get(conversation_id)

    def add_message(self, conversation_id: str, role: str, content: str,
                    metadata: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        state = self._conversations.get(conversation_id)
        if not state:
            return None
        msg = Message(role=role, content=content, timestamp=time.time(), metadata=metadata or {},
                      message_id=f"msg_{int(time.time() * 1000)}")
        state.add_message(msg)
        for handler in self._handlers:
            try:
                handler(state)
            except Exception:
                pass
        return msg

    def fork(self, conversation_id: str, new_id: str) -> Optional[ConversationState]:
        state = self._conversations.get(conversation_id)
        if not state:
            return None
        forked = state.fork(new_id)
        self._conversations[new_id] = forked
        return forked

    def rollback(self, conversation_id: str, message_count: int) -> bool:
        state = self._conversations.get(conversation_id)
        if not state:
            return False
        return state.rollback(message_count)

    def archive(self, conversation_id: str) -> bool:
        state = self._conversations.get(conversation_id)
        if not state:
            return False
        state.status = ConversationStatus.ARCHIVED
        return True

    def list_conversations(self, status: Optional[ConversationStatus] = None) -> List[ConversationState]:
        conversations = list(self._conversations.values())
        if status:
            conversations = [c for c in conversations if c.status == status]
        return conversations

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in self._conversations.values()], f, indent=2, default=str)

    def stats(self) -> Dict[str, Any]:
        total_messages = sum(len(c.messages) for c in self._conversations.values())
        return {
            "conversations": len(self._conversations),
            "total_messages": total_messages,
            "active": len([c for c in self._conversations.values() if c.status == ConversationStatus.ACTIVE]),
        }

    def add_handler(self, handler: Callable[[ConversationState], None]) -> None:
        self._handlers.append(handler)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Conversation State Engine")
    print("=" * 60)

    engine = ConversationStateEngine()

    print("\n--- Create conversation ---")
    conv = engine.create("conv_001", context={"model": "gpt-4o", "temperature": 0.7})
    print(f"  Created: {conv.conversation_id}")

    print("\n--- Add messages ---")
    for i, (role, content) in enumerate([("user", "Hello"), ("assistant", "Hi there!"), ("user", "How are you?")]):
        engine.add_message("conv_001", role, content)
    print(f"  Messages: {len(conv.messages)}")
    print(f"  Token estimate: {conv.get_token_estimate()}")

    print("\n--- Fork ---")
    forked = engine.fork("conv_001", "conv_001_alt")
    engine.add_message("conv_001_alt", "user", "Alternative path")
    print(f"  Original: {len(engine.get('conv_001').messages)} messages")
    print(f"  Forked: {len(engine.get('conv_001_alt').messages)} messages")

    print("\n--- Rollback ---")
    engine.rollback("conv_001", 2)
    print(f"  After rollback: {len(engine.get('conv_001').messages)} messages")

    print("\n--- Stats ---")
    print(engine.stats())

    print("\nConversation State test complete.")


if __name__ == "__main__":
    run()
