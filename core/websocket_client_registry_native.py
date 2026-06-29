"""WebSocket Client Registry — Client registration, session tracking, heartbeat."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class ClientSession:
    conn_id: str = ""
    client_id: str = ""
    connected_at: float = 0.0
    last_heartbeat: float = 0.0
    state: str = "active"  # active | idle | disconnected
    subscriptions: list[str] = None
    metadata: dict = None

    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = []
        if self.metadata is None:
            self.metadata = {}

class WebSocketClientRegistry:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._sessions: dict[str, ClientSession] = {}
        self._persist_path = self.root / "websocket_registry.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._sessions = {k: ClientSession(**v) for k, v in data.get("sessions", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "sessions": {k: v.__dict__ for k, v in self._sessions.items()}
        }, indent=2))

    def register(self, conn_id: str, client_id: str, metadata: dict = None) -> ClientSession:
        session = ClientSession(
            conn_id=conn_id,
            client_id=client_id,
            connected_at=time.time(),
            last_heartbeat=time.time(),
            metadata=metadata or {}
        )
        self._sessions[conn_id] = session
        self._save()
        return session

    def heartbeat(self, conn_id: str) -> bool:
        session = self._sessions.get(conn_id)
        if session:
            session.last_heartbeat = time.time()
            session.state = "active"
            self._save()
            return True
        return False

    def disconnect(self, conn_id: str) -> bool:
        session = self._sessions.get(conn_id)
        if session:
            session.state = "disconnected"
            self._save()
            return True
        return False

    def get_active(self) -> list[ClientSession]:
        return [s for s in self._sessions.values() if s.state == "active"]

    def get_by_client_id(self, client_id: str) -> list[ClientSession]:
        return [s for s in self._sessions.values() if s.client_id == client_id]

    def cleanup_idle(self, timeout_sec: float = 60.0) -> list[str]:
        now = time.time()
        removed = []
        for conn_id, session in list(self._sessions.items()):
            if session.state != "disconnected" and (now - session.last_heartbeat) > timeout_sec:
                session.state = "idle"
                removed.append(conn_id)
        self._save()
        return removed

    def to_dict(self) -> dict:
        return {"session_count": len(self._sessions), "active": len(self.get_active())}

    def get_stats(self) -> dict:
        return {"sessions": len(self._sessions), "active": len(self.get_active()), "disconnected": sum(1 for s in self._sessions.values() if s.state == "disconnected")}

__all__ = ["WebSocketClientRegistry", "ClientSession"]
