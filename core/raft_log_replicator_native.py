"""Raft Log Replicator — Append entries, log consistency."""
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass
class LogEntry:
    term: int = 0
    index: int = 0
    command: str = ""
    committed: bool = False

class RaftLogReplicator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._log: list[LogEntry] = []
        self._commit_index = 0
        self._match_index: dict[str, int] = {}
        self._persist_path = self.root / "raft_log.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._log = [LogEntry(**e) for e in data.get("log", [])]
            self._commit_index = data.get("commit_index", 0)
            self._match_index = data.get("match_index", {})

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "log": [e.__dict__ for e in self._log],
            "commit_index": self._commit_index,
            "match_index": self._match_index
        }, indent=2))

    def append(self, entry: LogEntry) -> int:
        entry.index = len(self._log) + 1
        self._log.append(entry)
        self._save()
        return entry.index

    def append_entries(self, prev_index: int, prev_term: int, entries: list[LogEntry]) -> bool:
        if prev_index > len(self._log):
            return False
        if prev_index > 0 and self._log[prev_index - 1].term != prev_term:
            return False
        self._log = self._log[:prev_index]
        for e in entries:
            e.index = len(self._log) + 1
            self._log.append(e)
        self._save()
        return True

    def update_match_index(self, node_id: str, index: int) -> None:
        self._match_index[node_id] = max(self._match_index.get(node_id, 0), index)
        self._save()

    def advance_commit(self, quorum: int) -> None:
        for i in range(self._commit_index + 1, len(self._log) + 1):
            matches = sum(1 for idx in self._match_index.values() if idx >= i)
            if matches + 1 >= quorum and self._log[i - 1].term == self._log[-1].term if self._log else False:
                self._commit_index = i
                self._log[i - 1].committed = True
        self._save()

    def to_dict(self) -> dict:
        return {"log_len": len(self._log), "commit_index": self._commit_index, "match_index": self._match_index}

    def get_stats(self) -> dict:
        return {"log_len": len(self._log), "commit_index": self._commit_index, "replicated_to": self._match_index}

__all__ = ["RaftLogReplicator", "LogEntry"]
