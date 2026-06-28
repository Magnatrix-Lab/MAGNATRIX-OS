#!/usr/bin/env python3
"""Blockchain Consensus Simulator for MAGNATRIX-OS."""
from __future__ import annotations
import hashlib, json, random, time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

@dataclass
class Block:
    index: int
    timestamp: float
    data: str
    previous_hash: str
    nonce: int = 0
    hash: str = ""
    def calculate_hash(self) -> str:
        payload = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(payload.encode()).hexdigest()
    def mine(self, difficulty: int = 4) -> None:
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()
    def to_dict(self): return {"index": self.index, "timestamp": self.timestamp, "data": self.data, "hash": self.hash, "nonce": self.nonce}

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.difficulty = 4
        self.create_genesis()
    def create_genesis(self):
        b = Block(0, time.time(), "genesis", "0")
        b.hash = b.calculate_hash()
        self.chain.append(b)
    def add_block(self, data: str) -> Block:
        prev = self.chain[-1]
        b = Block(len(self.chain), time.time(), data, prev.hash)
        b.mine(self.difficulty)
        self.chain.append(b)
        return b
    def is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i-1]
            if curr.hash != curr.calculate_hash() or curr.previous_hash != prev.hash:
                return False
        return True
    def to_dict(self): return {"length": len(self.chain), "valid": self.is_valid()}

class PoSValidator:
    def __init__(self):
        self.stakes: Dict[str, float] = {}
    def stake(self, node: str, amount: float):
        self.stakes[node] = self.stakes.get(node, 0) + amount
    def select_validator(self) -> Optional[str]:
        if not self.stakes: return None
        total = sum(self.stakes.values())
        r = random.uniform(0, total)
        cumulative = 0
        for node, stake in self.stakes.items():
            cumulative += stake
            if r <= cumulative:
                return node
        return list(self.stakes.keys())[-1]
    def to_dict(self): return {"validators": len(self.stakes), "total_stake": sum(self.stakes.values())}

class BlockchainConsensus:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.blockchain = Blockchain()
        self.pos = PoSValidator()
    def add_block(self, data: str) -> Block:
        return self.blockchain.add_block(data)
    def validate(self) -> bool:
        return self.blockchain.is_valid()
    def to_dict(self):
        return {"blockchain": self.blockchain.to_dict(), "pos": self.pos.to_dict()}
