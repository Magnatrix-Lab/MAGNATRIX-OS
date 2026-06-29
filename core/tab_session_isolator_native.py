
"""
tab_session_isolator_native.py
MAGNATRIX-OS — Tab Session Isolator

Inspired by Hermes Browser Extension v0.1.6 per-tab conversation isolation:
Pinned tabs get separate local message caches and separate
session bindings, keeping workstreams split by browser tab.

Pure Python standard library.
"""

import json
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class TabSession:
    session_id: str
    tab_id: str
    tab_title: str
    tab_url: str
    messages: List[Dict] = field(default_factory=list)
    created_at: str = ""
    last_active: str = ""
    is_pinned: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_active:
            self.last_active = self.created_at


class TabSessionIsolator:
    """Isolate AI conversations per browser tab."""

    def __init__(self, sessions_dir: str = "./tab_sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.sessions: Dict[str, TabSession] = {}
        self._load_all_sessions()

    def _session_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def _load_all_sessions(self) -> None:
        for f in self.sessions_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    self.sessions[data["session_id"]] = TabSession(**data)
            except Exception:
                pass

    def _save_session(self, session: TabSession) -> None:
        path = self._session_file(session.session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(session), f, indent=2)

    def create_session(self, tab_id: str, tab_title: str = "", tab_url: str = "", pinned: bool = False) -> TabSession:
        session_id = self._generate_session_id(tab_id)
        session = TabSession(
            session_id=session_id,
            tab_id=tab_id,
            tab_title=tab_title,
            tab_url=tab_url,
            is_pinned=pinned,
        )
        self.sessions[session_id] = session
        self._save_session(session)
        return session

    def _generate_session_id(self, tab_id: str) -> str:
        data = f"{tab_id}_{datetime.now().timestamp()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def get_session(self, tab_id: str) -> Optional[TabSession]:
        for session in self.sessions.values():
            if session.tab_id == tab_id:
                return session
        return None

    def get_or_create(self, tab_id: str, tab_title: str = "", tab_url: str = "", pinned: bool = False) -> TabSession:
        session = self.get_session(tab_id)
        if session:
            session.last_active = datetime.now().isoformat()
            session.tab_title = tab_title or session.tab_title
            session.tab_url = tab_url or session.tab_url
            self._save_session(session)
            return session
        return self.create_session(tab_id, tab_title, tab_url, pinned)

    def add_message(self, tab_id: str, role: str, content: str) -> bool:
        session = self.get_session(tab_id)
        if not session:
            return False
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        session.messages.append(message)
        session.last_active = message["timestamp"]
        self._save_session(session)
        return True

    def get_messages(self, tab_id: str, limit: Optional[int] = None) -> List[Dict]:
        session = self.get_session(tab_id)
        if not session:
            return []
        msgs = session.messages
        if limit:
            msgs = msgs[-limit:]
        return msgs

    def clear_session(self, tab_id: str) -> bool:
        session = self.get_session(tab_id)
        if not session:
            return False
        session.messages = []
        session.last_active = datetime.now().isoformat()
        self._save_session(session)
        return True

    def delete_session(self, tab_id: str) -> bool:
        session = self.get_session(tab_id)
        if not session:
            return False
        path = self._session_file(session.session_id)
        if path.exists():
            path.unlink()
        del self.sessions[session.session_id]
        return True

    def list_sessions(self) -> List[Dict]:
        return [asdict(s) for s in self.sessions.values()]

    def get_pinned_sessions(self) -> List[TabSession]:
        return [s for s in self.sessions.values() if s.is_pinned]

    def get_context_for_tab(self, tab_id: str) -> str:
        session = self.get_session(tab_id)
        if not session:
            return ""
        lines = [f"## Tab Conversation: {session.tab_title}", ""]
        for msg in session.messages[-10:]:
            lines.append(f"**{msg['role'].title()}:** {msg['content'][:100]}")
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "total_sessions": len(self.sessions),
            "pinned_sessions": len(self.get_pinned_sessions()),
            "sessions_dir": str(self.sessions_dir),
        }


__all__ = ["TabSessionIsolator", "TabSession"]
