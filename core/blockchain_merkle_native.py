"""Blockchain Merkle Tree -- Merkle tree construction, proof generation."""
from dataclasses import dataclass
from pathlib import Path
import json, hashlib

@dataclass
class MerkleProof:
    leaf_hash: str = ""
    leaf_index: int = 0
    siblings: list[str] = None
    directions: list[bool] = None  # True = right, False = left

    def __post_init__(self):
        if self.siblings is None:
            self.siblings = []
        if self.directions is None:
            self.directions = []

class BlockchainMerkleTree:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._trees: dict[str, dict] = {}
        self._persist_path = self.root / "blockchain_merkle.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._trees = data.get("trees", {})

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({"trees": self._trees}, indent=2))

    def _hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    def build(self, tree_id: str, leaves: list[str]) -> str:
        if not leaves:
            return self._hash("")
        hashes = [self._hash(leaf) for leaf in leaves]
        levels = [hashes[:]]
        while len(hashes) > 1:
            next_level = []
            for i in range(0, len(hashes), 2):
                pair = hashes[i] + (hashes[i+1] if i+1 < len(hashes) else hashes[i])
                next_level.append(self._hash(pair))
            hashes = next_level
            levels.append(hashes[:])
        root_hash = hashes[0]
        self._trees[tree_id] = {"root": root_hash, "levels": levels, "leaves": leaves}
        self._save()
        return root_hash

    def get_proof(self, tree_id: str, leaf_index: int) -> MerkleProof | None:
        tree = self._trees.get(tree_id)
        if not tree or leaf_index >= len(tree["leaves"]):
            return None
        levels = tree["levels"]
        siblings = []
        directions = []
        idx = leaf_index
        for level in levels[:-1]:
            sibling_idx = idx + 1 if idx % 2 == 0 else idx - 1
            if sibling_idx < len(level):
                siblings.append(level[sibling_idx])
                directions.append(idx % 2 == 0)  # True if sibling is on right
            else:
                siblings.append(level[idx])
                directions.append(True)
            idx //= 2
        return MerkleProof(
            leaf_hash=levels[0][leaf_index],
            leaf_index=leaf_index,
            siblings=siblings,
            directions=directions
        )

    def verify(self, tree_id: str, leaf_hash: str, proof: MerkleProof) -> bool:
        tree = self._trees.get(tree_id)
        if not tree:
            return False
        current = leaf_hash
        for sibling, direction in zip(proof.siblings, proof.directions):
            if direction:
                current = self._hash(current + sibling)
            else:
                current = self._hash(sibling + current)
        return current == tree["root"]

    def get_root(self, tree_id: str) -> str:
        tree = self._trees.get(tree_id)
        return tree["root"] if tree else ""

    def to_dict(self) -> dict:
        return {"tree_count": len(self._trees)}

    def get_stats(self) -> dict:
        total_leaves = sum(len(t.get("leaves", [])) for t in self._trees.values())
        return {"trees": len(self._trees), "total_leaves": total_leaves}

__all__ = ["BlockchainMerkleTree", "MerkleProof"]
