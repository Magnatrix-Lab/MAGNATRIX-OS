"""DB Write-Ahead Log -- WAL manager, checkpoint, replay, recovery."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class WALEntry:
    lsn: int = 0  # Log Sequence Number
    tx_id: str = ""
    op: str = ""  # insert | update | delete | commit | abort
    table: str = ""
    key: str = ""
    old_value: str = ""
    new_value: str = ""
    timestamp: float = 0.0

class DBWriteAheadLog:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._entries: list[WALEntry] = []
        self._lsn: int = 0
        self._checkpoint_lsn: int = 0
        self._persist_path = self.root / "db_wal.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._entries = [WALEntry(**e) for e in data.get("entries", [])]
            self._lsn = data.get("lsn", 0)
            self._checkpoint_lsn = data.get("checkpoint", 0)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "entries": [e.__dict__ for e in self._entries],
            "lsn": self._lsn,
            "checkpoint": self._checkpoint_lsn
        }, indent=2))

    def append(self, tx_id: str, op: str, table: str, key: str, old_value: str = "", new_value: str = "") -> WALEntry:
        self._lsn += 1
        entry = WALEntry(
            lsn=self._lsn, tx_id=tx_id, op=op, table=table,
            key=key, old_value=old_value, new_value=new_value,
            timestamp=time.time()
        )
        self._entries.append(entry)
        self._save()
        return entry

    def checkpoint(self) -> int:
        self._checkpoint_lsn = self._lsn
        # Truncate entries before checkpoint (simulate)
        self._entries = [e for e in self._entries if e.lsn >= self._checkpoint_lsn]
        self._save()
        return self._checkpoint_lsn

    def replay(self, from_lsn: int = 0) -> list[WALEntry]:
        return [e for e in self._entries if e.lsn >= from_lsn]

    def recover(self) -> list[dict]:
        # Replay all committed transactions since last checkpoint
        committed_txs = set()
        for e in self._entries:
            if e.op == "commit":
                committed_txs.add(e.tx_id)

        redo = []
        for e in self._entries:
            if e.tx_id in committed_txs and e.lsn >= self._checkpoint_lsn:
                if e.op in ("insert", "update", "delete"):
                    redo.append({"op": e.op, "table": e.table, "key": e.key, "value": e.new_value})
        return redo

    def get_by_tx(self, tx_id: str) -> list[WALEntry]:
        return [e for e in self._entries if e.tx_id == tx_id]

    def to_dict(self) -> dict:
        return {"entry_count": len(self._entries), "lsn": self._lsn, "checkpoint": self._checkpoint_lsn}

    def get_stats(self) -> dict:
        by_op = {}
        for e in self._entries:
            by_op[e.op] = by_op.get(e.op, 0) + 1
        return {"entries": len(self._entries), "by_op": by_op, "checkpoint": self._checkpoint_lsn}

__all__ = ["DBWriteAheadLog", "WALEntry"]
