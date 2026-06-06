#!/usr/bin/env python3
"""
Session Manager for MAGNATRIX-OS
Session handling, cookie management, expiry, concurrent limit.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import secrets
import time
from typing import Any, Dict, List, Optional


class Session:
    """User session."""

    def __init__(self, session_id: str, user_id: str, data: Dict[str, Any] = None) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.data = data or {}
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.expires_at = time.time() + 3600
        self.ip_address = ""
        self.user_agent = ""


class SessionManager:
    """Session management with expiry and concurrent limits."""

    def __init__(self, max_sessions_per_user: int = 5, default_ttl: int = 3600) -> None:
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, List[str]] = {}
        self._max_per_user = max_sessions_per_user
        self._default_ttl = default_ttl

    def create(self, user_id: str, data: Dict[str, Any] = None, ip: str = "", user_agent: str = "") -> Session:
        # Enforce max sessions per user
        if user_id in self._user_sessions:
            self._cleanup_user_sessions(user_id)
            while len(self._user_sessions[user_id]) >= self._max_per_user:
                oldest = self._user_sessions[user_id].pop(0)
                self._sessions.pop(oldest, None)

        session_id = secrets.token_urlsafe(32)
        session = Session(session_id, user_id, data)
        session.expires_at = time.time() + self._default_ttl
        session.ip_address = ip
        session.user_agent = user_agent

        self._sessions[session_id] = session
        self._user_sessions.setdefault(user_id, []).append(session_id)
        return session

    def get(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if not session:
            return None

        if session.expires_at < time.time():
            self.delete(session_id)
            return None

        session.last_accessed = time.time()
        return session

    def delete(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session and session.user_id in self._user_sessions:
            self._user_sessions[session.user_id] = [
                sid for sid in self._user_sessions[session.user_id] if sid != session_id
            ]
            return True
        return False

    def invalidate_user(self, user_id: str) -> int:
        session_ids = self._user_sessions.pop(user_id, [])
        for sid in session_ids:
            self._sessions.pop(sid, None)
        return len(session_ids)

    def _cleanup_user_sessions(self, user_id: str) -> None:
        valid = []
        for sid in self._user_sessions.get(user_id, []):
            session = self._sessions.get(sid)
            if session and session.expires_at > time.time():
                valid.append(sid)
            else:
                self._sessions.pop(sid, None)
        self._user_sessions[user_id] = valid

    def cleanup_expired(self) -> int:
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if s.expires_at < now]
        for sid in expired:
            self.delete(sid)
        return len(expired)

    def list_active(self, user_id: Optional[str] = None) -> List[Session]:
        if user_id:
            return [self._sessions[sid] for sid in self._user_sessions.get(user_id, []) if sid in self._sessions]
        return [s for s in self._sessions.values() if s.expires_at > time.time()]

    def stats(self) -> Dict[str, int]:
        return {
            'total_sessions': len(self._sessions),
            'active_users': len(self._user_sessions),
            'expired': len([s for s in self._sessions.values() if s.expires_at < time.time()]),
        }


def _demo() -> None:
    print("=== Session Manager Demo ===\n")

    mgr = SessionManager(max_sessions_per_user=3)

    # Create sessions
    s1 = mgr.create('user_1', {'role': 'admin'}, '192.168.1.1', 'Mozilla/5.0')
    s2 = mgr.create('user_1', {'role': 'admin'}, '192.168.1.2', 'Chrome/120')
    s3 = mgr.create('user_1', {'role': 'admin'}, '192.168.1.3', 'Firefox/121')
    s4 = mgr.create('user_1', {'role': 'admin'}, '192.168.1.4', 'Safari/17')  # Should evict oldest

    print(f"User 1 sessions: {len(mgr.list_active('user_1'))}")
    print(f"Session 1 exists: {mgr.get(s1.session_id) is not None}")

    # Get session
    session = mgr.get(s2.session_id)
    if session:
        print(f"Session data: {session.data}")

    # Invalidate all
    count = mgr.invalidate_user('user_1')
    print(f"Invalidated sessions: {count}")
    print(f"Stats: {mgr.stats()}")

    print("\n=== Session Manager Demo Complete ===")


if __name__ == '__main__':
    _demo()
