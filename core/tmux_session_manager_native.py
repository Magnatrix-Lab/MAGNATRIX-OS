"""
tmux_session_manager_native.py
MAGNATRIX-OS — Tmux Session Manager

Inspired by gajae-code: Tmux-backed session management for agent workers. Pure stdlib.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class TmuxSession:
    session_id: str
    name: str
    window_count: int
    pane_count: int
    is_active: bool
    created_at: str = ""
    last_activity: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class TmuxSessionManager:
    """Manage tmux sessions for agent workers."""

    def __init__(self, cache_dir: str = "./tmux_sessions"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.sessions: Dict[str, TmuxSession] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "sessions.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.sessions[sid] = TmuxSession(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "sessions.json", "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.sessions.items()}, f, indent=2)

    def create_session(self, session_id: str, name: str) -> TmuxSession:
        session = TmuxSession(
            session_id=session_id, name=name, window_count=1, pane_count=1, is_active=True,
        )
        self.sessions[session_id] = session
        self._save()
        return session

    def simulate_command(self, session_id: str, command: str) -> Dict[str, Any]:
        """Simulate running a command in a tmux session."""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        session.last_activity = datetime.now().isoformat()
        self._save()
        return {"session_id": session_id, "command": command, "status": "simulated", "output": f"Executed: {command}"}

    def list_sessions(self) -> List[TmuxSession]:
        return list(self.sessions.values())

    def kill_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
            self._save()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for s in self.sessions.values() if s.is_active)
        return {"total": len(self.sessions), "active": active}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TmuxSessionManager", "TmuxSession"]