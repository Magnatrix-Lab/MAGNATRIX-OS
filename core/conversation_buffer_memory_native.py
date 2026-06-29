"""
conversation_buffer_memory_native.py
MAGNATRIX-OS — Conversation Buffer Memory

Inspired by Agent Memory Techniques (NirDiamant): Store complete conversation history. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ConversationMessage:
    message_id: str
    role: str  # user, assistant, system
    content: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ConversationBufferMemory:
    """Store complete conversation history as a buffer."""

    def __init__(self, memory_dir: str = "./conversation_buffer"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.messages: List[ConversationMessage] = []
        self._load()

    def _load(self) -> None:
        file = self.memory_dir / "messages.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.messages = [ConversationMessage(**m) for m in data]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.memory_dir / "messages.json", "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self.messages], f, indent=2)

    def add(self, message_id: str, role: str, content: str) -> ConversationMessage:
        msg = ConversationMessage(message_id=message_id, role=role, content=content)
        self.messages.append(msg)
        self._save()
        return msg

    def get_recent(self, n: int = 10) -> List[ConversationMessage]:
        return self.messages[-n:]

    def get_all(self) -> List[ConversationMessage]:
        return self.messages

    def clear(self) -> None:
        self.messages = []
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        return {"total_messages": len(self.messages), "roles": list(set(m.role for m in self.messages))}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ConversationBufferMemory", "ConversationMessage"]