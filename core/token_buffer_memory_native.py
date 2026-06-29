"""
token_buffer_memory_native.py
MAGNATRIX-OS — Token Buffer Memory

Inspired by Agent Memory Techniques: Token-limited buffer that truncates when token count exceeds limit. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class TokenMessage:
    message_id: str
    role: str
    content: str
    token_count: int
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class TokenBufferMemory:
    """Token-limited buffer that truncates when token count exceeds limit."""

    def __init__(self, memory_dir: str = "./token_buffer", max_tokens: int = 4096):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.max_tokens = max_tokens
        self.messages: List[TokenMessage] = []
        self._load()

    def _load(self) -> None:
        file = self.memory_dir / "messages.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.messages = [TokenMessage(**m) for m in data]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.memory_dir / "messages.json", "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self.messages], f, indent=2)

    def _count_tokens(self, text: str) -> int:
        """Simple token estimation: ~4 chars per token."""
        return max(1, len(text) // 4)

    def add(self, message_id: str, role: str, content: str) -> TokenMessage:
        tokens = self._count_tokens(content)
        msg = TokenMessage(message_id=message_id, role=role, content=content, token_count=tokens)
        self.messages.append(msg)
        self._enforce_limit()
        self._save()
        return msg

    def _enforce_limit(self) -> None:
        total = sum(m.token_count for m in self.messages)
        while total > self.max_tokens and self.messages:
            removed = self.messages.pop(0)
            total -= removed.token_count

    def get_messages(self) -> List[TokenMessage]:
        return self.messages

    def get_total_tokens(self) -> int:
        return sum(m.token_count for m in self.messages)

    def get_stats(self) -> Dict[str, Any]:
        return {"messages": len(self.messages), "total_tokens": self.get_total_tokens(), "max_tokens": self.max_tokens}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TokenBufferMemory", "TokenMessage"]