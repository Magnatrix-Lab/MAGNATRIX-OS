"""WebSocket Presence Tracker — Online/away/offline, activity tracking."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class PresenceState:
    conn_id: str = ""
    user_id: str = ""
    status: str = "offline"  # online | away | offline | dnd
    last_activity: float = 0.0
    custom_status: str = ""

class WebSocketPresenceTracker:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._states: dict[str, PresenceState] = {}
        self._away_timeout: float = 300.0  # 5 minutes
        self._persist_path = self.root / "websocket_presence.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._states = {k: PresenceState(**v) for k, v in data.get("states", {}).items()}
            self._away_timeout = data.get("away_timeout", 300.0)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "states": {k: v.__dict__ for k, v in self._states.items()},
            "away_timeout": self._away_timeout
        }, indent=2))

    def set_online(self, conn_id: str, user_id: str) -> PresenceState:
        state = PresenceState(conn_id=conn_id, user_id=user_id, status="online", last_activity=time.time())
        self._states[conn_id] = state
        self._save()
        return state

    def set_away(self, conn_id: str) -> PresenceState | None:
        state = self._states.get(conn_id)
        if state:
            state.status = "away"
            self._save()
        return state

    def set_offline(self, conn_id: str) -> PresenceState | None:
        state = self._states.get(conn_id)
        if state:
            state.status = "offline"
            self._save()
        return state

    def set_dnd(self, conn_id: str) -> PresenceState | None:
        state = self._states.get(conn_id)
        if state:
            state.status = "dnd"
            self._save()
        return state

    def activity(self, conn_id: str) -> PresenceState | None:
        state = self._states.get(conn_id)
        if state:
            state.last_activity = time.time()
            state.status = "online"
            self._save()
        return state

    def check_idle(self) -> list[str]:
        now = time.time()
        away_list = []
        for conn_id, state in self._states.items():
            if state.status == "online" and (now - state.last_activity) > self._away_timeout:
                state.status = "away"
                away_list.append(conn_id)
        self._save()
        return away_list

    def get_online(self) -> list[str]:
        return [conn_id for conn_id, state in self._states.items() if state.status == "online"]

    def get_by_user(self, user_id: str) -> list[PresenceState]:
        return [s for s in self._states.values() if s.user_id == user_id]

    def to_dict(self) -> dict:
        return {"state_count": len(self._states), "online": len(self.get_online())}

    def get_stats(self) -> dict:
        by_status = {}
        for s in self._states.values():
            by_status[s.status] = by_status.get(s.status, 0) + 1
        return {"total": len(self._states), "by_status": by_status}

__all__ = ["WebSocketPresenceTracker", "PresenceState"]
