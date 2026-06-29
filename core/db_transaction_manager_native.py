"""DB Transaction Manager -- ACID transactions, WAL, rollback, commit."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class Transaction:
    tx_id: str = ""
    status: str = "active"  # active | committed | aborted
    start_time: float = 0.0
    commit_time: float = 0.0
    operations: list[dict] = None
    read_set: list[str] = None
    write_set: list[str] = None

    def __post_init__(self):
        if self.operations is None:
            self.operations = []
        if self.read_set is None:
            self.read_set = []
        if self.write_set is None:
            self.write_set = []

class DBTransactionManager:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._transactions: dict[str, Transaction] = {}
        self._committed: list[str] = []
        self._wal: list[dict] = []
        self._persist_path = self.root / "db_transactions.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._transactions = {k: Transaction(**v) for k, v in data.get("transactions", {}).items()}
            self._committed = data.get("committed", [])
            self._wal = data.get("wal", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "transactions": {k: v.__dict__ for k, v in self._transactions.items()},
            "committed": self._committed,
            "wal": self._wal
        }, indent=2))

    def begin(self, tx_id: str) -> Transaction:
        tx = Transaction(tx_id=tx_id, start_time=time.time(), status="active")
        self._transactions[tx_id] = tx
        self._wal.append({"op": "begin", "tx_id": tx_id, "ts": time.time()})
        self._save()
        return tx

    def write(self, tx_id: str, key: str, old_value: str, new_value: str) -> bool:
        tx = self._transactions.get(tx_id)
        if not tx or tx.status != "active":
            return False
        op = {"op": "write", "tx_id": tx_id, "key": key, "old": old_value, "new": new_value}
        tx.operations.append(op)
        tx.write_set.append(key)
        self._wal.append(op)
        self._save()
        return True

    def read(self, tx_id: str, key: str) -> bool:
        tx = self._transactions.get(tx_id)
        if not tx or tx.status != "active":
            return False
        tx.read_set.append(key)
        self._save()
        return True

    def commit(self, tx_id: str) -> bool:
        tx = self._transactions.get(tx_id)
        if not tx or tx.status != "active":
            return False
        tx.status = "committed"
        tx.commit_time = time.time()
        self._committed.append(tx_id)
        self._wal.append({"op": "commit", "tx_id": tx_id, "ts": time.time()})
        self._save()
        return True

    def rollback(self, tx_id: str) -> list[dict]:
        tx = self._transactions.get(tx_id)
        if not tx or tx.status != "active":
            return []
        tx.status = "aborted"
        # Generate undo operations
        undo = []
        for op in reversed(tx.operations):
            if op["op"] == "write":
                undo.append({"op": "undo_write", "key": op["key"], "value": op["old"]})
        self._wal.append({"op": "rollback", "tx_id": tx_id, "ts": time.time()})
        self._save()
        return undo

    def get_active(self) -> list[Transaction]:
        return [t for t in self._transactions.values() if t.status == "active"]

    def to_dict(self) -> dict:
        return {"tx_count": len(self._transactions), "committed": len(self._committed)}

    def get_stats(self) -> dict:
        by_status = {}
        for t in self._transactions.values():
            by_status[t.status] = by_status.get(t.status, 0) + 1
        return {"transactions": len(self._transactions), "by_status": by_status, "wal_entries": len(self._wal)}

__all__ = ["DBTransactionManager", "Transaction"]
