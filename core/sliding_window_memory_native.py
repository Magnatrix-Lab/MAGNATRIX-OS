"""
sliding_window_memory_native.py
MAGNATRIX-OS — Sliding Window Memory

Inspired by Agent Memory Techniques: Keep only last k messages, sliding window. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class WindowMessage:
    message_id: str
    role: str
    content: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class SlidingWindowMemory:
    """Keep only the last k messages in a sliding window."""

    def __init__(self, memory_dir: str = "./sliding_window", k: int = 10):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.k = k
        self.messages: List[WindowMessage] = []
        self._load()

    def _load(self) -> None:
        file = self.memory_dir / "messages.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.messages = [WindowMessage(**m) for m in data]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.memory_dir / "messages.json", "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self.messages], f, indent=2)

    def add(self, message_id: str, role: str, content: str) -> WindowMessage:
        msg = WindowMessage(message_id=message_id, role=role, content=content)
        self.messages.append(msg)
        if len(self.messages) > self.k:
            self.messages = self.messages[-self.k:]
        self._save()
        return msg

    def get_window(self) -> List[WindowMessage]:
        return self.messages

    def set_window_size(self, k: int) -> None:
        self.k = k
        if len(self.messages) > self.k:
            self.messages = self.messages[-self.k:]
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        return {"window_size": self.k, "current_messages": len(self.messages), "dropped": max(0, len(self.messages) - self.k)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SlidingWindowMemory", "WindowMessage"]