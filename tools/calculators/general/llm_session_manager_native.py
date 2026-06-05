"""Session Manager — session creation, storage, expiry, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto
import time
import hashlib
import random

@dataclass
class Session:
    session_id: str
    created_at: float
    expires_at: float
    data: Dict[str, Any]
    last_accessed: float

class SessionManager:
    def __init__(self, max_age: int = 3600):
        self.max_age = max_age
        self.sessions: Dict[str, Session] = {}

    def create(self, data: Dict = None) -> Session:
        sid = hashlib.sha256(str(random.random() + time.time()).encode()).hexdigest()[:16]
        now = time.time()
        session = Session(sid, now, now + self.max_age, data or {}, now)
        self.sessions[sid] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        session = self.sessions.get(session_id)
        if session and session.expires_at > time.time():
            session.last_accessed = time.time()
            return session
        return None

    def set(self, session_id: str, key: str, value: Any):
        session = self.get(session_id)
        if session:
            session.data[key] = value

    def destroy(self, session_id: str):
        self.sessions.pop(session_id, None)

    def extend(self, session_id: str):
        session = self.get(session_id)
        if session:
            session.expires_at = time.time() + self.max_age

    def clear_expired(self):
        now = time.time()
        expired = [sid for sid, s in self.sessions.items() if s.expires_at <= now]
        for sid in expired:
            self.sessions.pop(sid)

    def stats(self) -> Dict:
        return {"sessions": len(self.sessions), "max_age": self.max_age}

def run():
    sm = SessionManager(60)
    s = sm.create({"user": "Alice"})
    sm.set(s.session_id, "role", "admin")
    print(sm.get(s.session_id).data)
    sm.destroy(s.session_id)
    print(sm.stats())

if __name__ == "__main__":
    run()
