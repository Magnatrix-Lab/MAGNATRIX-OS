"""Deduplication Engine — exact, fuzzy, and LSH deduplication, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum, auto
import hashlib

class DedupMethod(Enum):
    EXACT = auto()
    FUZZY = auto()
    LSH = auto()

@dataclass
class DuplicateGroup:
    group_id: str
    records: List[Dict]
    similarity: float

class DeduplicationEngine:
    def __init__(self, method: DedupMethod = DedupMethod.EXACT, threshold: float = 0.9):
        self.method = method
        self.threshold = threshold
        self.groups: List[DuplicateGroup] = []
        self.seen: Set[str] = set()

    def _hash_record(self, record: Dict) -> str:
        return hashlib.sha256(str(sorted(record.items())).encode()).hexdigest()

    def _jaccard(self, a: Dict, b: Dict) -> float:
        keys_a = set(a.keys())
        keys_b = set(b.keys())
        intersection = sum(1 for k in keys_a & keys_b if a.get(k) == b.get(k))
        union = len(keys_a | keys_b)
        return intersection / union if union else 0

    def _lsh_signature(self, record: Dict, num_hashes: int = 8) -> List[str]:
        text = str(sorted(record.items()))
        return [hashlib.md5((text + str(i)).encode()).hexdigest()[:4] for i in range(num_hashes)]

    def find_duplicates(self, records: List[Dict]) -> List[DuplicateGroup]:
        self.groups = []
        self.seen = set()
        ungrouped = list(enumerate(records))
        while ungrouped:
            idx, rec = ungrouped.pop(0)
            group = [rec]
            if self.method == DedupMethod.EXACT:
                h = self._hash_record(rec)
                matches = [(i, r) for i, r in ungrouped if self._hash_record(r) == h]
            elif self.method == DedupMethod.FUZZY:
                matches = [(i, r) for i, r in ungrouped if self._jaccard(rec, r) >= self.threshold]
            else:
                sig = self._lsh_signature(rec)
                matches = [(i, r) for i, r in ungrouped if len(set(sig) & set(self._lsh_signature(r))) >= len(sig) * self.threshold]
            for i, r in matches:
                group.append(r)
                ungrouped = [(j, x) for j, x in ungrouped if j != i]
            if len(group) > 1:
                self.groups.append(DuplicateGroup(f"g{idx}", group, 1.0 if self.method == DedupMethod.EXACT else self._jaccard(group[0], group[1])))
        return self.groups

    def deduplicate(self, records: List[Dict]) -> List[Dict]:
        groups = self.find_duplicates(records)
        deduped = []
        used = set()
        for g in groups:
            deduped.append(g.records[0])
            for r in g.records:
                used.add(id(r))
        for r in records:
            if id(r) not in used:
                deduped.append(r)
        return deduped

    def stats(self) -> Dict:
        return {"method": self.method.name, "groups": len(self.groups), "total_duplicates": sum(len(g.records) - 1 for g in self.groups)}

def run():
    records = [
        {"name": "Alice", "age": 30},
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Alice", "age": 31},
    ]
    engine = DeduplicationEngine(DedupMethod.FUZZY, threshold=0.8)
    groups = engine.find_duplicates(records)
    print(f"Groups: {len(groups)}")
    for g in groups:
        print(g.group_id, len(g.records))
    print(engine.stats())

if __name__ == "__main__":
    run()
