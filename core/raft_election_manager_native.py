"""Raft Election Manager — Randomized timeouts, quorum voting."""
from dataclasses import dataclass
from pathlib import Path
import json, random, time

@dataclass
class ElectionState:
    term: int = 0
    is_voting: bool = False
    votes_received: int = 0
    votes_needed: int = 0
    voted_for: str = ""

class RaftElectionManager:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self.state = ElectionState()
        self._vote_log: list[dict] = []
        self._persist_path = self.root / "raft_election.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self.state = ElectionState(**data.get("state", {}))
            self._vote_log = data.get("vote_log", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "state": self.state.__dict__,
            "vote_log": self._vote_log
        }, indent=2))

    def random_timeout(self, min_ms: int = 150, max_ms: int = 300) -> int:
        return random.randint(min_ms, max_ms)

    def start_election(self, term: int, cluster_size: int) -> None:
        self.state.term = term
        self.state.is_voting = True
        self.state.votes_received = 1
        self.state.votes_needed = (cluster_size // 2) + 1
        self.state.voted_for = "self"
        self._vote_log.append({"term": term, "event": "started", "needed": self.state.votes_needed})
        self._save()

    def receive_vote(self, voter: str, granted: bool) -> None:
        if granted and self.state.is_voting:
            self.state.votes_received += 1
            self._vote_log.append({"voter": voter, "granted": granted})
            self._save()

    def has_quorum(self) -> bool:
        return self.state.votes_received >= self.state.votes_needed

    def request_vote(self, candidate_id: str, candidate_term: int, last_log_index: int, last_log_term: int, my_term: int, my_log_len: int) -> bool:
        if candidate_term < my_term:
            return False
        if candidate_term == my_term and self.state.voted_for and self.state.voted_for != candidate_id:
            return False
        # Up-to-date check
        if last_log_term < my_term or (last_log_term == my_term and last_log_index < my_log_len):
            return False
        self.state.voted_for = candidate_id
        self._save()
        return True

    def to_dict(self) -> dict:
        return self.state.__dict__

    def get_stats(self) -> dict:
        return {"votes": self.state.votes_received, "needed": self.state.votes_needed, "quorum": self.has_quorum()}

__all__ = ["RaftElectionManager", "ElectionState"]
