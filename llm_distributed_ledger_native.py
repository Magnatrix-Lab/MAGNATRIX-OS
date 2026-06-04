"""Distributed Ledger / Consensus Log — native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import hashlib
import time
import json

class LogEntryType(Enum):
    COMMAND = auto()
    CONFIG = auto()
    NOOP = auto()

@dataclass
class LogEntry:
    index: int
    term: int
    entry_type: LogEntryType
    data: Dict
    prev_hash: str = ""
    hash: str = field(default="", repr=False)

    def __post_init__(self):
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = json.dumps({"index": self.index, "term": self.term, "type": self.entry_type.name, "data": self.data, "prev": self.prev_hash}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

@dataclass
class Ledger:
    entries: List[LogEntry] = field(default_factory=list)
    committed_index: int = 0
    current_term: int = 0

    def append(self, data: Dict, entry_type: LogEntryType = LogEntryType.COMMAND) -> LogEntry:
        self.current_term += 1
        prev_hash = self.entries[-1].hash if self.entries else ""
        entry = LogEntry(index=len(self.entries) + 1, term=self.current_term, entry_type=entry_type, data=data, prev_hash=prev_hash)
        self.entries.append(entry)
        return entry

    def commit(self, index: int) -> bool:
        if 0 < index <= len(self.entries):
            self.committed_index = max(self.committed_index, index)
            return True
        return False

    def verify_chain(self) -> bool:
        for i in range(1, len(self.entries)):
            if self.entries[i].prev_hash != self.entries[i-1].hash:
                return False
        return True

    def range_query(self, start: int, end: int) -> List[LogEntry]:
        return [e for e in self.entries if start <= e.index <= end]

    def stats(self) -> Dict:
        return {"total_entries": len(self.entries), "committed": self.committed_index, "current_term": self.current_term, "chain_valid": self.verify_chain()}

def run():
    ledger = Ledger()
    ledger.append({"action": "init", "value": 100})
    ledger.append({"action": "transfer", "from": "A", "to": "B", "amount": 30})
    ledger.append({"action": "transfer", "from": "B", "to": "C", "amount": 10})
    ledger.commit(2)
    print(ledger.stats())
    print(ledger.entries)

if __name__ == "__main__":
    run()
