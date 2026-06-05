"""State Machine Replication — native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable
from enum import Enum, auto
from copy import deepcopy

class ReplicaRole(Enum):
    PRIMARY = auto()
    BACKUP = auto()

@dataclass
class Replica:
    replica_id: str
    role: ReplicaRole
    state: Dict[str, Any] = field(default_factory=dict)
    log: List[Dict] = field(default_factory=list)
    applied_index: int = 0

    def apply(self, op: Dict) -> Any:
        cmd = op.get("cmd")
        key = op.get("key")
        val = op.get("val")
        if cmd == "SET":
            self.state[key] = val
            return True
        elif cmd == "GET":
            return self.state.get(key)
        elif cmd == "DELETE":
            return self.state.pop(key, None) is not None
        elif cmd == "INCR":
            self.state[key] = self.state.get(key, 0) + val
            return self.state[key]
        return None

    def replicate(self, op: Dict):
        self.log.append(deepcopy(op))
        return self.apply(op)

    def catch_up(self, ops: List[Dict]):
        for op in ops[self.applied_index:]:
            self.apply(op)
            self.applied_index += 1

    def stats(self) -> Dict:
        return {"id": self.replica_id, "role": self.role.name, "state": self.state, "log_len": len(self.log), "applied": self.applied_index}

class ReplicationEngine:
    def __init__(self):
        self.replicas: List[Replica] = []
        self.primary: Optional[Replica] = None

    def add_replica(self, rid: str, role: ReplicaRole = ReplicaRole.BACKUP):
        r = Replica(rid, role)
        self.replicas.append(r)
        if role == ReplicaRole.PRIMARY:
            self.primary = r
        return r

    def promote(self, rid: str):
        for r in self.replicas:
            r.role = ReplicaRole.BACKUP
        target = next((r for r in self.replicas if r.replica_id == rid), None)
        if target:
            target.role = ReplicaRole.PRIMARY
            self.primary = target

    def execute(self, op: Dict) -> List[Any]:
        if not self.primary:
            raise RuntimeError("No primary")
        result = self.primary.replicate(op)
        for r in self.replicas:
            if r != self.primary:
                r.catch_up(self.primary.log)
        return [result] + [r.state for r in self.replicas]

    def stats(self) -> Dict:
        return {"replicas": [r.stats() for r in self.replicas], "primary": self.primary.replica_id if self.primary else None}

def run():
    engine = ReplicationEngine()
    engine.add_replica("R0", ReplicaRole.PRIMARY)
    for i in range(1, 4):
        engine.add_replica(f"R{i}")
    engine.execute({"cmd": "SET", "key": "x", "val": 10})
    engine.execute({"cmd": "INCR", "key": "x", "val": 5})
    print(engine.stats())

if __name__ == "__main__":
    run()
