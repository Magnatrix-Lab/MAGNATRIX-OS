"""
chat_interface_native.py
MAGNATRIX-OS — Chat Interface

Inspired by langflow-ai/langflow chat interface:
Interactive chat session management with message history and context tracking. Pure stdlib.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ChatMessage:
    msg_id: str
    role: str  # user, assistant, system
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatSession:
    session_id: str
    flow_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: str = ""
    last_active: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_active:
            self.last_active = self.created_at


class ChatInterface:
    """Interactive chat session management with message history."""

    def __init__(self, chat_dir: str = "./chat_sessions"):
        self.chat_dir = Path(chat_dir)
        self.chat_dir.mkdir(exist_ok=True)
        self.sessions: Dict[str, ChatSession] = {}
        self._load()

    def _load(self) -> None:
        file = self.chat_dir / "sessions.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        sd["messages"] = [ChatMessage(**m) for m in sd.get("messages", [])]
                        self.sessions[sid] = ChatSession(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.chat_dir / "sessions.json", "w", encoding="utf-8") as f:
            out = {}
            for sid, session in self.sessions.items():
                d = asdict(session)
                d["messages"] = [asdict(m) for m in session.messages]
                out[sid] = d
            json.dump(out, f, indent=2)

    def create_session(self, session_id: str, flow_id: str) -> ChatSession:
        session = ChatSession(session_id=session_id, flow_id=flow_id)
        self.sessions[session_id] = session
        self._save()
        return session

    def send_message(self, session_id: str, role: str, content: str,
                     metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        msg = ChatMessage(
            msg_id=f"{session_id}_{len(session.messages)}", role=role, content=content,
            timestamp=time.time(), metadata=metadata or {},
        )
        session.messages.append(msg)
        session.last_active = datetime.now().isoformat()
        self._save()
        return msg

    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        session = self.sessions.get(session_id)
        if not session:
            return []
        msgs = session.messages
        if limit:
            msgs = msgs[-limit:]
        return msgs

    def get_context_window(self, session_id: str, max_tokens: int = 4000) -> str:
        """Build context window from recent messages."""
        history = self.get_history(session_id, limit=20)
        parts = []
        total = 0
        for msg in reversed(history):
            part = f"{msg.role}: {msg.content}\n"
            total += len(part)
            if total > max_tokens:
                break
            parts.append(part)
        return "".join(reversed(parts))

    def clear_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.messages = []
            self._save()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        total_msgs = sum(len(s.messages) for s in self.sessions.values())
        return {"sessions": len(self.sessions), "total_messages": total_msgs}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ChatInterface", "ChatMessage", "ChatSession"]