"""Squad Terminal Coordinator — Multi-terminal session coordination."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class TerminalSession:
    session_id: str = ""
    agent_id: str = ""
    terminal_type: str = ""  # tmux | screen | native | vscode
    pid: int = 0
    active: bool = True
    started_at: float = 0.0
    commands_executed: int = 0

class SquadTerminalCoordinator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._sessions: dict[str, TerminalSession] = {}
        self._persist_path = self.root / "squad_sessions.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._sessions = {k: TerminalSession(**v) for k, v in data.get("sessions", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "sessions": {k: v.__dict__ for k, v in self._sessions.items()}
        }, indent=2))

    def spawn(self, session_id: str, agent_id: str, terminal_type: str = "native") -> TerminalSession:
        import time, os
        session = TerminalSession(
            session_id=session_id, agent_id=agent_id,
            terminal_type=terminal_type, pid=os.getpid(),
            started_at=time.time()
        )
        self._sessions[session_id] = session
        self._save()
        return session

    def attach(self, session_id: str) -> TerminalSession | None:
        return self._sessions.get(session_id)

    def detach(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.active = False
            self._save()
            return True
        return False

    def record_command(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.commands_executed += 1
            self._save()
            return True
        return False

    def list_active(self) -> list[TerminalSession]:
        return [s for s in self._sessions.values() if s.active]

    def get_by_agent(self, agent_id: str) -> list[TerminalSession]:
        return [s for s in self._sessions.values() if s.agent_id == agent_id]

    def cleanup_inactive(self) -> list[str]:
        removed = [sid for sid, s in self._sessions.items() if not s.active]
        for sid in removed:
            del self._sessions[sid]
        self._save()
        return removed

    def to_dict(self) -> dict:
        return {"session_count": len(self._sessions), "active": len(self.list_active())}

    def get_stats(self) -> dict:
        by_type = {}
        for s in self._sessions.values():
            by_type[s.terminal_type] = by_type.get(s.terminal_type, 0) + 1
        total_cmds = sum(s.commands_executed for s in self._sessions.values())
        return {"sessions": len(self._sessions), "active": len(self.list_active()), "by_type": by_type, "total_commands": total_cmds}

__all__ = ["SquadTerminalCoordinator", "TerminalSession"]
