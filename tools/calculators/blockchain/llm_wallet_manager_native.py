"""Wallet Manager — key pairs, transactions, balances, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import hashlib
import random
import time

class TransactionType(Enum):
    SEND = auto()
    RECEIVE = auto()
    STAKE = auto()
    UNSTAKE = auto()

@dataclass
class Transaction:
    tx_id: str
    sender: str
    receiver: str
    amount: float
    tx_type: TransactionType
    timestamp: float
    signature: str = ""

class Wallet:
    def __init__(self, address: str, private_key: str = ""):
        self.address = address
        self.private_key = private_key or hashlib.sha256(address.encode()).hexdigest()[:16]
        self.balance = 0.0
        self.transactions: List[Transaction] = []
        self.staked = 0.0

    def sign(self, data: str) -> str:
        return hashlib.sha256((self.private_key + data).encode()).hexdigest()[:16]

    def receive(self, amount: float):
        self.balance += amount

    def send(self, amount: float) -> bool:
        if self.balance >= amount:
            self.balance -= amount
            return True
        return False

    def stake(self, amount: float) -> bool:
        if self.balance >= amount:
            self.balance -= amount
            self.staked += amount
            return True
        return False

    def unstake(self, amount: float) -> bool:
        if self.staked >= amount:
            self.staked -= amount
            self.balance += amount
            return True
        return False

class WalletManager:
    def __init__(self):
        self.wallets: Dict[str, Wallet] = {}
        self.transactions: List[Transaction] = []
        self.mempool: List[Transaction] = []

    def create_wallet(self, address: str) -> Wallet:
        wallet = Wallet(address)
        self.wallets[address] = wallet
        return wallet

    def transfer(self, from_addr: str, to_addr: str, amount: float) -> Optional[Transaction]:
        sender = self.wallets.get(from_addr)
        receiver = self.wallets.get(to_addr)
        if not sender or not receiver:
            return None
        if sender.send(amount):
            receiver.receive(amount)
            tx_id = hashlib.sha256(f"{from_addr}:{to_addr}:{amount}:{time.time()}".encode()).hexdigest()[:8]
            tx = Transaction(tx_id, from_addr, to_addr, amount, TransactionType.SEND, time.time())
            tx.signature = sender.sign(tx_id)
            self.transactions.append(tx)
            return tx
        return None

    def get_balance(self, address: str) -> float:
        wallet = self.wallets.get(address)
        return wallet.balance if wallet else 0.0

    def get_history(self, address: str) -> List[Transaction]:
        return [tx for tx in self.transactions if tx.sender == address or tx.receiver == address]

    def stats(self) -> Dict:
        total = sum(w.balance for w in self.wallets.values())
        return {"wallets": len(self.wallets), "transactions": len(self.transactions), "total_balance": total}

def run():
    wm = WalletManager()
    wm.create_wallet("Alice")
    wm.create_wallet("Bob")
    wm.wallets["Alice"].balance = 100
    wm.transfer("Alice", "Bob", 30)
    print("Alice:", wm.get_balance("Alice"))
    print("Bob:", wm.get_balance("Bob"))
    print(wm.stats())

if __name__ == "__main__":
    run()
