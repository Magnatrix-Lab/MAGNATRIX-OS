"""Blockchain Transaction Builder -- Transaction construction, signing, serialization."""
from dataclasses import dataclass
from pathlib import Path
import json, hashlib, time

@dataclass
class Transaction:
    tx_id: str = ""
    version: int = 1
    inputs: list[dict] = None
    outputs: list[dict] = None
    lock_time: int = 0
    timestamp: float = 0.0
    signature: str = ""
    fee: float = 0.0

    def __post_init__(self):
        if self.inputs is None:
            self.inputs = []
        if self.outputs is None:
            self.outputs = []

class BlockchainTxBuilder:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._txs: dict[str, Transaction] = {}
        self._persist_path = self.root / "blockchain_txs.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._txs = {k: Transaction(**v) for k, v in data.get("txs", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "txs": {k: v.__dict__ for k, v in self._txs.items()}
        }, indent=2))

    def _hash_tx(self, tx: Transaction) -> str:
        data = json.dumps({"v": tx.version, "in": tx.inputs, "out": tx.outputs, "lock": tx.lock_time})
        return hashlib.sha256(data.encode()).hexdigest()[:64]

    def build(self, inputs: list[dict], outputs: list[dict], fee: float = 0.0) -> Transaction:
        tx = Transaction(version=1, inputs=inputs, outputs=outputs, fee=fee, timestamp=time.time())
        tx.tx_id = self._hash_tx(tx)
        self._txs[tx.tx_id] = tx
        self._save()
        return tx

    def sign(self, tx_id: str, private_key: str) -> bool:
        tx = self._txs.get(tx_id)
        if not tx:
            return False
        # Simulate ECDSA signing
        msg = tx_id + json.dumps(tx.inputs)
        tx.signature = hashlib.sha256((msg + private_key).encode()).hexdigest()[:128]
        self._save()
        return True

    def verify(self, tx_id: str, public_key: str) -> bool:
        tx = self._txs.get(tx_id)
        if not tx or not tx.signature:
            return False
        msg = tx_id + json.dumps(tx.inputs)
        expected = hashlib.sha256((msg + public_key).encode()).hexdigest()[:128]
        return tx.signature == expected

    def get(self, tx_id: str) -> Transaction | None:
        return self._txs.get(tx_id)

    def list_by_sender(self, sender: str) -> list[Transaction]:
        return [t for t in self._txs.values() if any(i.get("address") == sender for i in t.inputs)]

    def to_dict(self) -> dict:
        return {"tx_count": len(self._txs)}

    def get_stats(self) -> dict:
        total_out = sum(sum(o.get("amount", 0) for o in t.outputs) for t in self._txs.values())
        signed = sum(1 for t in self._txs.values() if t.signature)
        return {"txs": len(self._txs), "total_output": round(total_out, 8), "signed": signed}

__all__ = ["BlockchainTxBuilder", "Transaction"]
