"""Fraud Detector — anomaly, velocity, pattern, rule-based, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime

@dataclass
class Transaction:
    id: str
    amount: float
    timestamp: str
    merchant: str
    location: str

class FraudDetector:
    def __init__(self):
        self.transactions: List[Transaction] = []
        self.rules: List[Dict] = []

    def add_transaction(self, t: Transaction):
        self.transactions.append(t)

    def velocity_check(self, user_id: str, window_minutes: int = 60, threshold: int = 5) -> bool:
        user_txns = [t for t in self.transactions if t.id.startswith(user_id)]
        if len(user_txns) < 2:
            return False
        recent = len(user_txns)
        return recent > threshold

    def amount_anomaly(self, amount: float, avg: float, std: float) -> float:
        if std <= 0:
            return 0.0
        z = abs(amount - avg) / std
        return min(1.0, z / 3)

    def location_anomaly(self, current: str, history: List[str]) -> float:
        if not history:
            return 0.0
        return 0.0 if current in history else 0.5

    def round_amount_check(self, amount: float) -> float:
        return 0.3 if amount % 100 == 0 else 0.0

    def fraud_score(self, txn: Transaction) -> float:
        amounts = [t.amount for t in self.transactions]
        avg = sum(amounts) / len(amounts) if amounts else 0
        std = (sum((a - avg)**2 for a in amounts) / len(amounts))**0.5 if amounts else 1
        score = 0.0
        score += self.amount_anomaly(txn.amount, avg, std)
        score += self.round_amount_check(txn.amount)
        locations = [t.location for t in self.transactions]
        score += self.location_anomaly(txn.location, locations)
        return min(1.0, score)

    def stats(self) -> Dict:
        return {"transactions": len(self.transactions), "avg_amount": sum(t.amount for t in self.transactions) / len(self.transactions) if self.transactions else 0}

def run():
    fd = FraudDetector()
    fd.add_transaction(Transaction("T1", 100, "2024-01-01", "A", "NY"))
    fd.add_transaction(Transaction("T2", 5000, "2024-01-01", "B", "LA"))
    fd.add_transaction(Transaction("T3", 100, "2024-01-01", "C", "NY"))
    print(fd.stats())
    print("Fraud score T2:", fd.fraud_score(fd.transactions[1]))

if __name__ == "__main__":
    run()
