"""
chat_interface_native.py
MAGNATRIX-OS — Chat Interface

Inspired by Langflow (langflow-ai): Chat interface for AI agent conversations.
Session management, message history, streaming, and context tracking. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ChatMessage:
    msg_id: str
    session_id: str
    role: str  # user, assistant, system
    content: str
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ChatSession:
    session_id: str
    title: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class ChatInterface:
    """Chat interface for AI agent conversations with session management."""

    def __init__(self, chats_dir: str = "./chats"):
        self.chats_dir = Path(chats_dir)
        self.chats_dir.mkdir(exist_ok=True)
        self.sessions: Dict[str, ChatSession] = {}
        self._load()

    def _load(self) -> None:
        file = self.chats_dir / "sessions.json"
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
        out = {}
        for sid, s in self.sessions.items():
            d = asdict(s)
            d["messages"] = [asdict(m) for m in s.messages]
            out[sid] = d
        with open(self.chats_dir / "sessions.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def create_session(self, session_id: str, title: str = "") -> ChatSession:
        session = ChatSession(session_id=session_id, title=title or f"Session {session_id}")
        self.sessions[session_id] = session
        self._save()
        return session

    def send_message(self, session_id: str, msg_id: str, role: str, content: str,
                     metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        session = self.sessions.get(session_id)
        if not session:
            session = self.create_session(session_id)
        msg = ChatMessage(
            msg_id=msg_id, session_id=session_id, role=role,
            content=content, metadata=metadata or {},
        )
        session.messages.append(msg)
        session.updated_at = datetime.now().isoformat()
        self._save()
        return msg

    def get_history(self, session_id: str, limit: int = 50) -> List[ChatMessage]:
        session = self.sessions.get(session_id)
        if not session:
            return []
        return session.messages[-limit:]

    def get_context(self, session_id: str, max_tokens: int = 4000) -> str:
        """Get recent conversation context as a formatted string."""
        history = self.get_history(session_id, limit=20)
        parts = []
        total = 0
        for msg in reversed(history):
            part = f"{msg.role}: {msg.content}\n"
            total += len(part)
            if total > max_tokens:
                break
            parts.append(part)
        return "\n".join(reversed(parts))

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save()
            return True
        return False

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self.sessions.get(session_id)

    def list_sessions(self) -> List[ChatSession]:
        return list(self.sessions.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.sessions)
        total_msgs = sum(len(s.messages) for s in self.sessions.values())
        return {"sessions": total, "total_messages": total_msgs}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ChatInterface", "ChatSession", "ChatMessage"]