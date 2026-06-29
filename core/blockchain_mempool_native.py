"""Blockchain Mempool -- Transaction pool, fee prioritization, eviction."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class MempoolTx:
    tx_id: str = ""
    sender: str = ""
    recipient: str = ""
    amount: float = 0.0
    fee: float = 0.0
    nonce: int = 0
    data: str = ""
    timestamp: float = 0.0
    priority: float = 0.0

class BlockchainMempool:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._txs: dict[str, MempoolTx] = {}
        self._max_size: int = 10000
        self._min_fee: float = 0.0001
        self._persist_path = self.root / "mempool.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._txs = {k: MempoolTx(**v) for k, v in data.get("txs", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "txs": {k: v.__dict__ for k, v in self._txs.items()}
        }, indent=2))

    def add(self, tx: MempoolTx) -> bool:
        if tx.fee < self._min_fee:
            return False
        tx.priority = tx.fee / (tx.amount + 1)
        self._txs[tx.tx_id] = tx
        if len(self._txs) > self._max_size:
            self._evict_lowest()
        self._save()
        return True

    def _evict_lowest(self) -> None:
        if not self._txs:
            return
        lowest = min(self._txs.values(), key=lambda t: t.priority)
        self._txs.pop(lowest.tx_id, None)

    def get_top(self, n: int = 100) -> list[MempoolTx]:
        return sorted(self._txs.values(), key=lambda t: t.priority, reverse=True)[:n]

    def remove(self, tx_id: str) -> bool:
        if tx_id in self._txs:
            del self._txs[tx_id]
            self._save()
            return True
        return False

    def get_by_sender(self, sender: str) -> list[MempoolTx]:
        return [t for t in self._txs.values() if t.sender == sender]

    def get_by_recipient(self, recipient: str) -> list[MempoolTx]:
        return [t for t in self._txs.values() if t.recipient == recipient]

    def to_dict(self) -> dict:
        return {"tx_count": len(self._txs), "max_size": self._max_size}

    def get_stats(self) -> dict:
        total_value = sum(t.amount for t in self._txs.values())
        total_fee = sum(t.fee for t in self._txs.values())
        return {"txs": len(self._txs), "total_value": round(total_value, 4), "total_fee": round(total_fee, 8)}

__all__ = ["BlockchainMempool", "MempoolTx"]
