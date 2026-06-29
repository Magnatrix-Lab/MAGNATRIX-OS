"""
summary_buffer_memory_native.py
MAGNATRIX-OS — Summary Buffer Memory

Inspired by Agent Memory Techniques: Summarize old conversation, keep summary + recent messages. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class SummaryEntry:
    summary_id: str
    summary: str
    message_count: int
    start_time: str
    end_time: str


class SummaryBufferMemory:
    """Summarize old conversation, keep summary + recent messages."""

    def __init__(self, memory_dir: str = "./summary_buffer", buffer_size: int = 5):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.buffer_size = buffer_size
        self.messages: List[Dict[str, Any]] = []
        self.summaries: List[SummaryEntry] = []
        self.current_summary: str = ""
        self._load()

    def _load(self) -> None:
        for fname, attr in [("messages.json", "messages"), ("summaries.json", "summaries")]:
            f = self.memory_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "summaries.json":
                            self.summaries = [SummaryEntry(**s) for s in data]
                        else:
                            self.messages = data
                except Exception:
                    pass
        summary_file = self.memory_dir / "current_summary.txt"
        if summary_file.exists():
            self.current_summary = summary_file.read_text()

    def _save(self) -> None:
        with open(self.memory_dir / "messages.json", "w", encoding="utf-8") as f:
            json.dump(self.messages, f, indent=2)
        with open(self.memory_dir / "summaries.json", "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in self.summaries], f, indent=2)
        with open(self.memory_dir / "current_summary.txt", "w", encoding="utf-8") as f:
            f.write(self.current_summary)

    def _summarize(self, messages: List[Dict[str, Any]]) -> str:
        """Simple extractive summary: concatenate key messages."""
        if not messages:
            return ""
        roles = [m.get("role", "") for m in messages]
        contents = [m.get("content", "")[:50] for m in messages]
        return f"Summary: {len(messages)} messages. Roles: {', '.join(set(roles))}. Topics: {'; '.join(contents[:3])}"

    def add(self, message_id: str, role: str, content: str) -> None:
        self.messages.append({"message_id": message_id, "role": role, "content": content, "timestamp": datetime.now().isoformat()})
        if len(self.messages) > self.buffer_size:
            # Summarize older messages
            to_summarize = self.messages[:-self.buffer_size]
            self.current_summary = self._summarize(to_summarize)
            self.summaries.append(SummaryEntry(
                summary_id=f"summary_{len(self.summaries)}", summary=self.current_summary,
                message_count=len(to_summarize), start_time=to_summarize[0].get("timestamp", ""),
                end_time=to_summarize[-1].get("timestamp", ""),
            ))
            self.messages = self.messages[-self.buffer_size:]
        self._save()

    def get_context(self) -> Dict[str, Any]:
        return {
            "summary": self.current_summary,
            "recent_messages": self.messages,
            "total_summaries": len(self.summaries),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"messages": len(self.messages), "summaries": len(self.summaries), "buffer_size": self.buffer_size}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SummaryBufferMemory", "SummaryEntry"]