"""
Session Manager — MAGNATRIX-OS Core
Agent session persistence, conversation state, checkpoint/restore.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import json, time, hashlib, os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SessionState:
    """State of a single agent session."""
    session_id: str
    agent_id: str
    created_at: float
    last_activity: float
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    context_variables: Dict[str, Any] = field(default_factory=dict)
    tool_calls_made: int = 0
    policies_applied: List[str] = field(default_factory=list)
    checkpoint_count: int = 0
    status: str = "active"  # active, paused, terminated, error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "conversation_history": self.conversation_history,
            "context_variables": self.context_variables,
            "tool_calls_made": self.tool_calls_made,
            "policies_applied": self.policies_applied,
            "checkpoint_count": self.checkpoint_count,
            "status": self.status,
        }


class SessionManager:
    """
    Manage agent sessions: creation, persistence, checkpoint, restore.
    """

    def __init__(self, storage_dir: str = ".sessions") -> None:
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._sessions: Dict[str, SessionState] = {}
        self._max_history_per_session = 1000

    def create_session(self, agent_id: str, session_id: Optional[str] = None) -> SessionState:
        sid = session_id or f"sess_{agent_id}_{int(time.time())}"
        session = SessionState(
            session_id=sid,
            agent_id=agent_id,
            created_at=time.time(),
            last_activity=time.time(),
        )
        self._sessions[sid] = session
        self._save(session)
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        if session_id in self._sessions:
            return self._sessions[session_id]
        # Try to load from disk
        loaded = self._load(session_id)
        if loaded:
            self._sessions[session_id] = loaded
        return loaded

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {},
        })
        if len(session.conversation_history) > self._max_history_per_session:
            session.conversation_history = session.conversation_history[-self._max_history_per_session:]
        session.last_activity = time.time()
        self._save(session)
        return True

    def set_context(self, session_id: str, key: str, value: Any) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.context_variables[key] = value
        session.last_activity = time.time()
        self._save(session)
        return True

    def get_context(self, session_id: str, key: str) -> Any:
        session = self.get_session(session_id)
        if not session:
            return None
        return session.context_variables.get(key)

    def checkpoint(self, session_id: str, label: str = "") -> Optional[str]:
        """Create a checkpoint for session recovery."""
        session = self.get_session(session_id)
        if not session:
            return None
        session.checkpoint_count += 1
        checkpoint_id = f"chk_{session_id}_{session.checkpoint_count}"
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "label": label,
            "timestamp": time.time(),
            "state": session.to_dict(),
        }
        filepath = os.path.join(self.storage_dir, f"{checkpoint_id}.json")
        with open(filepath, "w") as f:
            json.dump(checkpoint_data, f)
        self._save(session)
        return checkpoint_id

    def restore(self, checkpoint_id: str) -> Optional[SessionState]:
        filepath = os.path.join(self.storage_dir, f"{checkpoint_id}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r") as f:
            data = json.load(f)
        state = data["state"]
        session = SessionState(
            session_id=state["session_id"],
            agent_id=state["agent_id"],
            created_at=state["created_at"],
            last_activity=time.time(),
            conversation_history=state.get("conversation_history", []),
            context_variables=state.get("context_variables", {}),
            tool_calls_made=state.get("tool_calls_made", 0),
            policies_applied=state.get("policies_applied", []),
            checkpoint_count=state.get("checkpoint_count", 0),
            status="restored",
        )
        self._sessions[session.session_id] = session
        self._save(session)
        return session

    def terminate(self, session_id: str, reason: str = "") -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.status = "terminated"
        self._save(session)
        return True

    def list_sessions(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sessions = [s.to_dict() for s in self._sessions.values()]
        if agent_id:
            sessions = [s for s in sessions if s["agent_id"] == agent_id]
        return sessions

    def _save(self, session: SessionState) -> None:
        filepath = os.path.join(self.storage_dir, f"{session.session_id}.json")
        with open(filepath, "w") as f:
            json.dump(session.to_dict(), f)

    def _load(self, session_id: str) -> Optional[SessionState]:
        filepath = os.path.join(self.storage_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            return SessionState(
                session_id=data["session_id"],
                agent_id=data["agent_id"],
                created_at=data["created_at"],
                last_activity=data["last_activity"],
                conversation_history=data.get("conversation_history", []),
                context_variables=data.get("context_variables", {}),
                tool_calls_made=data.get("tool_calls_made", 0),
                policies_applied=data.get("policies_applied", []),
                checkpoint_count=data.get("checkpoint_count", 0),
                status=data.get("status", "active"),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def stats(self) -> Dict[str, Any]:
        return {
            "active_sessions": len([s for s in self._sessions.values() if s.status == "active"]),
            "total_sessions": len(self._sessions),
            "storage_dir": self.storage_dir,
            "max_history": self._max_history_per_session,
        }


def run():
    print("=" * 60)
    print("Session Manager — Demo")
    print("=" * 60)

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = SessionManager(tmpdir)

        print("\n[1] Create session")
        sess = mgr.create_session("agent_1")
        print(f"   Session: {sess.session_id}")

        print("\n[2] Add messages")
        mgr.add_message(sess.session_id, "user", "Hello, calculate BMI")
        mgr.add_message(sess.session_id, "assistant", "I can help with that. What is your weight?")
        mgr.add_message(sess.session_id, "user", "70 kg")
        sess2 = mgr.get_session(sess.session_id)
        print(f"   Messages: {len(sess2.conversation_history)}")

        print("\n[3] Set context")
        mgr.set_context(sess.session_id, "weight_kg", 70)
        mgr.set_context(sess.session_id, "height_cm", 175)
        print(f"   Weight: {mgr.get_context(sess.session_id, 'weight_kg')}")

        print("\n[4] Checkpoint")
        chk = mgr.checkpoint(sess.session_id, "before_calculation")
        print(f"   Checkpoint: {chk}")

        print("\n[5] Terminate and restore")
        mgr.terminate(sess.session_id, "completed")
        restored = mgr.restore(chk)
        if restored:
            print(f"   Restored: {restored.session_id}, status={restored.status}")
            print(f"   Messages: {len(restored.conversation_history)}")

        print(f"\n[6] Stats: {mgr.stats()}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
