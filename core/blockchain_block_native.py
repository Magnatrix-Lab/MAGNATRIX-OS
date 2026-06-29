"""Blockchain Block Builder -- Block construction, validation, chain linking."""
from dataclasses import dataclass
from pathlib import Path
import json, hashlib, time

@dataclass
class Block:
    block_id: str = ""
    height: int = 0
    previous_hash: str = ""
    timestamp: float = 0.0
    merkle_root: str = ""
    tx_ids: list[str] = None
    nonce: int = 0
    difficulty: int = 4
    hash: str = ""

    def __post_init__(self):
        if self.tx_ids is None:
            self.tx_ids = []

class BlockchainBlockBuilder:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._blocks: dict[str, Block] = {}
        self._chain: list[str] = []
        self._persist_path = self.root / "blockchain_blocks.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._blocks = {k: Block(**v) for k, v in data.get("blocks", {}).items()}
            self._chain = data.get("chain", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "blocks": {k: v.__dict__ for k, v in self._blocks.items()},
            "chain": self._chain
        }, indent=2))

    def _compute_hash(self, block: Block) -> str:
        data = str(block.height) + block.previous_hash + str(block.timestamp) + block.merkle_root + str(block.nonce)
        return hashlib.sha256(data.encode()).hexdigest()

    def _compute_merkle_root(self, tx_ids: list[str]) -> str:
        if not tx_ids:
            return hashlib.sha256(b"").hexdigest()
        hashes = [hashlib.sha256(t.encode()).hexdigest() for t in tx_ids]
        while len(hashes) > 1:
            next_level = []
            for i in range(0, len(hashes), 2):
                pair = hashes[i] + (hashes[i+1] if i+1 < len(hashes) else hashes[i])
                next_level.append(hashlib.sha256(pair.encode()).hexdigest())
            hashes = next_level
        return hashes[0]

    def mine(self, tx_ids: list[str], previous_hash: str = "", difficulty: int = 4) -> Block:
        height = len(self._chain)
        merkle = self._compute_merkle_root(tx_ids)
        block = Block(
            height=height, previous_hash=previous_hash or ("0" * 64),
            timestamp=time.time(), merkle_root=merkle,
            tx_ids=tx_ids, difficulty=difficulty
        )
        target = "0" * difficulty
        while True:
            block.hash = self._compute_hash(block)
            if block.hash.startswith(target):
                break
            block.nonce += 1
        block.block_id = block.hash[:16]
        self._blocks[block.block_id] = block
        self._chain.append(block.block_id)
        self._save()
        return block

    def validate(self, block_id: str) -> bool:
        block = self._blocks.get(block_id)
        if not block:
            return False
        expected = self._compute_hash(block)
        if block.hash != expected:
            return False
        target = "0" * block.difficulty
        if not block.hash.startswith(target):
            return False
        if block.height > 0:
            prev = self._blocks.get(self._chain[block.height - 1]) if block.height - 1 < len(self._chain) else None
            if prev and block.previous_hash != prev.hash:
                return False
        return True

    def get_chain(self) -> list[Block]:
        return [self._blocks[bid] for bid in self._chain if bid in self._blocks]

    def get_latest(self) -> Block | None:
        if self._chain:
            return self._blocks.get(self._chain[-1])
        return None

    def to_dict(self) -> dict:
        return {"block_count": len(self._blocks), "chain_length": len(self._chain)}

    def get_stats(self) -> dict:
        total_txs = sum(len(b.tx_ids) for b in self._blocks.values())
        return {"blocks": len(self._blocks), "chain": len(self._chain), "total_txs": total_txs}

__all__ = ["BlockchainBlockBuilder", "Block"]
