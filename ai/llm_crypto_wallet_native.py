"""Crypto Wallet - Simple wallet for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
import hashlib
import random

@dataclass
class CryptoWallet:
    address: str = ""
    private_key: str = ""
    balance: float = 0.0
    transactions: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.private_key:
            self.private_key = hashlib.sha256(str(random.random()).encode()).hexdigest()[:32]
        if not self.address:
            self.address = hashlib.sha256(self.private_key.encode()).hexdigest()[:20]

    def receive(self, amount: float, from_addr: str) -> None:
        self.balance += amount
        self.transactions.append({"type": "receive", "amount": amount, "from": from_addr})

    def send(self, amount: float, to_addr: str) -> bool:
        if self.balance >= amount:
            self.balance -= amount
            self.transactions.append({"type": "send", "amount": amount, "to": to_addr})
            return True
        return False

    def stats(self) -> dict:
        return {"address": self.address, "balance": round(self.balance, 4), "tx_count": len(self.transactions)}

def run():
    w = CryptoWallet()
    w.receive(100.0, "miner1")
    w.send(30.0, "addr2")
    print("Balance:", w.balance)
    print("Stats:", w.stats())

if __name__ == "__main__": run()
