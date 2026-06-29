"""Raft Node State Machine — Follower/Candidate/Leader transitions."""
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass
class RaftNodeState:
    node_id: str = "node_0"
    state: str = "follower"  # follower | candidate | leader
    current_term: int = 0
    voted_for: str = ""
    votes_received: int = 0
    leader_id: str = ""
    last_heartbeat_ms: int = 0

class RaftNodeStateMachine:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self.state = RaftNodeState()
        self._log: list[dict] = []
        self._persist_path = self.root / "raft_state.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self.state = RaftNodeState(**data.get("state", {}))
            self._log = data.get("log", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "state": self.state.__dict__,
            "log": self._log
        }, indent=2))

    def transition(self, new_state: str, term: int = 0) -> None:
        if term > self.state.current_term:
            self.state.current_term = term
            self.state.voted_for = ""
            self.state.votes_received = 0
        self.state.state = new_state
        self._log.append({"event": "transition", "to": new_state, "term": term, "ts": json.dumps(None)})
        self._save()

    def receive_vote(self, from_node: str) -> None:
        if self.state.state == "candidate":
            self.state.votes_received += 1
            self._save()

    def reset_election_timer(self) -> None:
        self.state.last_heartbeat_ms = 0
        self._save()

    def to_dict(self) -> dict:
        return {"state": self.state.__dict__, "log_len": len(self._log)}

    def get_stats(self) -> dict:
        return {"term": self.state.current_term, "state": self.state.state, "votes": self.state.votes_received}

__all__ = ["RaftNodeStateMachine", "RaftNodeState"]
