"""Raft Heartbeat Coordinator — Leader dispatch, step-down."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class HeartbeatState:
    leader_id: str = ""
    term: int = 0
    last_sent_ms: int = 0
    last_received_ms: int = 0
    step_down_count: int = 0

class RaftHeartbeatCoordinator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self.state = HeartbeatState()
        self._peers: list[str] = []
        self._persist_path = self.root / "raft_heartbeat.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self.state = HeartbeatState(**data.get("state", {}))
            self._peers = data.get("peers", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "state": self.state.__dict__,
            "peers": self._peers
        }, indent=2))

    def set_peers(self, peers: list[str]) -> None:
        self._peers = peers
        self._save()

    def send_heartbeat(self, leader_id: str, term: int) -> list[dict]:
        self.state.leader_id = leader_id
        self.state.term = term
        self.state.last_sent_ms = int(time.time() * 1000)
        acks = [{"peer": p, "ack": True} for p in self._peers]
        self._save()
        return acks

    def receive_heartbeat(self, leader_id: str, term: int) -> bool:
        now = int(time.time() * 1000)
        if term < self.state.term:
            return False
        self.state.leader_id = leader_id
        self.state.term = term
        self.state.last_received_ms = now
        self._save()
        return True

    def check_timeout(self, timeout_ms: int = 500) -> bool:
        now = int(time.time() * 1000)
        if self.state.leader_id and (now - self.state.last_received_ms) > timeout_ms:
            self.state.step_down_count += 1
            self.state.leader_id = ""
            self._save()
            return True
        return False

    def to_dict(self) -> dict:
        return self.state.__dict__

    def get_stats(self) -> dict:
        return {"leader": self.state.leader_id, "term": self.state.term, "timeouts": self.state.step_down_count}

__all__ = ["RaftHeartbeatCoordinator", "HeartbeatState"]
