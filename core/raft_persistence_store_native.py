"""Raft Persistence Store — WAL simulation, state recovery."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class PersistentState:
    current_term: int = 0
    voted_for: str = ""
    log: list[dict] = None

    def __post_init__(self):
        if self.log is None:
            self.log = []

class RaftPersistenceStore:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._wal_path = self.root / "raft_wal.json"
        self._state_path = self.root / "raft_persist.json"
        self._wal_buffer: list[dict] = []
        self._flush_threshold = 100
        self._load()

    def _load(self) -> None:
        if self._state_path.exists():
            data = json.loads(self._state_path.read_text())
            self.state = PersistentState(**data)
        else:
            self.state = PersistentState()
        if self._wal_path.exists():
            self._wal_buffer = json.loads(self._wal_path.read_text())

    def _save_state(self) -> None:
        self._state_path.write_text(json.dumps(self.state.__dict__, indent=2))

    def _flush_wal(self) -> None:
        self._wal_path.write_text(json.dumps(self._wal_buffer, indent=2))

    def set_term(self, term: int) -> None:
        self.state.current_term = term
        self._wal_buffer.append({"op": "set_term", "term": term})
        self._flush_if_needed()
        self._save_state()

    def vote(self, candidate: str, term: int) -> None:
        self.state.voted_for = candidate
        self.state.current_term = term
        self._wal_buffer.append({"op": "vote", "candidate": candidate, "term": term})
        self._flush_if_needed()
        self._save_state()

    def append_log(self, entry: dict) -> None:
        self.state.log.append(entry)
        self._wal_buffer.append({"op": "append", "entry": entry})
        self._flush_if_needed()
        self._save_state()

    def _flush_if_needed(self) -> None:
        if len(self._wal_buffer) >= self._flush_threshold:
            self._flush_wal()

    def truncate_log(self, index: int) -> None:
        self.state.log = self.state.log[:index]
        self._wal_buffer.append({"op": "truncate", "index": index})
        self._flush_wal()
        self._save_state()

    def recover(self) -> PersistentState:
        self._load()
        return self.state

    def to_dict(self) -> dict:
        return {"wal_len": len(self._wal_buffer), "log_len": len(self.state.log), "term": self.state.current_term}

    def get_stats(self) -> dict:
        return {"log_len": len(self.state.log), "term": self.state.current_term, "voted_for": self.state.voted_for}

__all__ = ["RaftPersistenceStore", "PersistentState"]
