"""
database_scaling_engine_native.py
MAGNATRIX-OS — Database Scaling Engine

Inspired by donnemartin/system-design-primer database scaling:
Sharding, replication, federation, denormalization, indexing strategies. Pure stdlib.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class Shard:
    shard_id: int
    range_start: str
    range_end: str
    node: str
    record_count: int = 0


@dataclass
class Replica:
    replica_id: str
    primary_node: str
    replica_node: str
    lag_ms: float = 0.0
    is_sync: bool = False


class DatabaseScalingEngine:
    """Database scaling strategies: sharding, replication, federation, denormalization."""

    def __init__(self, data_dir: str = "./db_scaling"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.shards: Dict[str, List[Shard]] = {}
        self.replicas: List[Replica] = []
        self._load()

    def _load(self) -> None:
        for fname in ["shards.json", "replicas.json"]:
            f = self.data_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "shards.json":
                            self.shards = {k: [Shard(**s) for s in v] for k, v in data.items()}
                        else:
                            self.replicas = [Replica(**r) for r in data]
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.data_dir / "shards.json", "w", encoding="utf-8") as f:
            json.dump({k: [asdict(s) for s in v] for k, v in self.shards.items()}, f, indent=2)
        with open(self.data_dir / "replicas.json", "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.replicas], f, indent=2)

    def hash_shard(self, key: str, num_shards: int) -> int:
        """Consistent hash-based sharding."""
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return h % num_shards

    def range_shard(self, key: str, ranges: List[Tuple[str, str]]) -> int:
        """Range-based sharding."""
        for i, (start, end) in enumerate(ranges):
            if start <= key <= end:
                return i
        return len(ranges) - 1

    def create_shards(self, table: str, num_shards: int, nodes: List[str]) -> List[Shard]:
        shards = []
        for i in range(num_shards):
            shard = Shard(
                shard_id=i, range_start=chr(65 + i * (26 // num_shards)),
                range_end=chr(65 + (i + 1) * (26 // num_shards) - 1),
                node=nodes[i % len(nodes)],
            )
            shards.append(shard)
        self.shards[table] = shards
        self._save()
        return shards

    def add_replica(self, primary: str, replica: str, is_sync: bool = False) -> Replica:
        rep = Replica(replica_id=f"{primary}_{replica}", primary_node=primary, replica_node=replica, is_sync=is_sync)
        self.replicas.append(rep)
        self._save()
        return rep

    def federated_query(self, table: str, key: str) -> Optional[Shard]:
        shards = self.shards.get(table, [])
        if not shards:
            return None
        shard_idx = self.hash_shard(key, len(shards))
        return shards[shard_idx] if shard_idx < len(shards) else None

    def denormalize(self, base_table: str, related_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate denormalization by embedding related data."""
        return {"table": base_table, "embedded": related_data, "redundancy": True}

    def get_stats(self) -> Dict[str, Any]:
        return {"sharded_tables": len(self.shards), "replicas": len(self.replicas)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["DatabaseScalingEngine", "Shard", "Replica"]