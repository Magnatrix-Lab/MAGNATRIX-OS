"""Block Builder - Blockchain block creation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import hashlib
import time

@dataclass
class BlockBuilder:
    index: int = 0; previous_hash: str = "0" * 64
    transactions: List[Dict] = field(default_factory=list)
    timestamp: float = 0.0; nonce: int = 0; hash: str = ""

    def __post_init__(self):
        if self.timestamp == 0.0: self.timestamp = time.time()
        if not self.hash: self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        data = f"{self.index}{self.previous_hash}{self.timestamp}{self.nonce}{self.transactions}"
        return hashlib.sha256(data.encode()).hexdigest()

    def mine(self, difficulty: int = 2) -> None:
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()

    def add_transaction(self, sender: str, receiver: str, amount: float) -> None:
        self.transactions.append({"sender": sender, "receiver": receiver, "amount": amount})
        self.hash = self.compute_hash()

    def stats(self) -> dict:
        return {"index": self.index, "hash": self.hash[:16], "tx_count": len(self.transactions), "nonce": self.nonce}

def run():
    bb = BlockBuilder(1, "0"*64)
    bb.add_transaction("alice", "bob", 10.0)
    bb.mine(2)
    print("Hash:", bb.hash[:16])
    print("Stats:", bb.stats())

if __name__ == "__main__": run()
