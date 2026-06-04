"""Transaction Manager - ACID transactions for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum, auto
import time

class TxState(Enum):
    ACTIVE = auto(); COMMITTED = auto(); ABORTED = auto()

@dataclass
class TransactionManager:
    active_transactions: Dict[str, Dict] = field(default_factory=dict)
    log: List[Dict] = field(default_factory=list)
    data: Dict[str, str] = field(default_factory=dict)
    locks: Dict[str, str] = field(default_factory=dict)

    def begin(self, tx_id: str) -> None:
        self.active_transactions[tx_id] = {"state": TxState.ACTIVE, "read_set": set(), "write_set": set(), "start_time": time.time()}

    def read(self, tx_id: str, key: str) -> Optional[str]:
        if tx_id not in self.active_transactions: return None
        self.active_transactions[tx_id]["read_set"].add(key)
        return self.data.get(key)

    def write(self, tx_id: str, key: str, value: str) -> bool:
        if tx_id not in self.active_transactions: return False
        if key in self.locks and self.locks[key] != tx_id: return False
        self.locks[key] = tx_id
        self.active_transactions[tx_id]["write_set"].add(key)
        self.active_transactions[tx_id]["write_set_values"] = self.active_transactions[tx_id].get("write_set_values", {})
        self.active_transactions[tx_id]["write_set_values"][key] = value
        return True

    def commit(self, tx_id: str) -> bool:
        if tx_id not in self.active_transactions: return False
        tx = self.active_transactions[tx_id]
        for key in tx.get("write_set_values", {}):
            self.data[key] = tx["write_set_values"][key]
            if key in self.locks and self.locks[key] == tx_id: del self.locks[key]
        tx["state"] = TxState.COMMITTED
        self.log.append({"tx_id": tx_id, "action": "commit", "time": time.time()})
        del self.active_transactions[tx_id]
        return True

    def stats(self) -> dict:
        return {"active": len(self.active_transactions), "data_size": len(self.data), "locks": len(self.locks)}

def run():
    tm = TransactionManager()
    tm.begin("tx1")
    tm.write("tx1", "x", "100")
    tm.write("tx1", "y", "200")
    tm.commit("tx1")
    print("Data:", tm.data)
    print("Stats:", tm.stats())

if __name__ == "__main__": run()
