"""Raft Snapshot Manager — State machine snapshots, compaction."""
from dataclasses import dataclass
from pathlib import Path
import json, base64, zlib

@dataclass
class Snapshot:
    last_included_index: int = 0
    last_included_term: int = 0
    data_b64: str = ""
    checksum: str = ""

class RaftSnapshotManager:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._snapshots: list[Snapshot] = []
        self._persist_path = self.root / "raft_snapshots.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._snapshots = [Snapshot(**s) for s in data.get("snapshots", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "snapshots": [s.__dict__ for s in self._snapshots]
        }, indent=2))

    def create_snapshot(self, last_index: int, last_term: int, state_data: dict) -> Snapshot:
        raw = json.dumps(state_data).encode()
        compressed = zlib.compress(raw)
        snap = Snapshot(
            last_included_index=last_index,
            last_included_term=last_term,
            data_b64=base64.b64encode(compressed).decode(),
            checksum=hex(zlib.crc32(raw) & 0xffffffff)
        )
        self._snapshots.append(snap)
        self._save()
        return snap

    def compact_log(self, log_entries: list[dict], snap: Snapshot) -> list[dict]:
        return [e for e in log_entries if e.get("index", 0) > snap.last_included_index]

    def restore(self, snap: Snapshot) -> dict:
        raw = zlib.decompress(base64.b64decode(snap.data_b64))
        return json.loads(raw)

    def to_dict(self) -> dict:
        return {"snapshot_count": len(self._snapshots), "latest": self._snapshots[-1].__dict__ if self._snapshots else None}

    def get_stats(self) -> dict:
        return {"snapshot_count": len(self._snapshots), "latest_index": self._snapshots[-1].last_included_index if self._snapshots else 0}

__all__ = ["RaftSnapshotManager", "Snapshot"]
