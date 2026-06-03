"""Failover Handler - Automatic failover for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class FailoverStatus(Enum):
    ACTIVE = auto(); STANDBY = auto(); FAILED = auto()

@dataclass
class FailoverHandler:
    primary: str = ""
    secondaries: List[str] = field(default_factory=list)
    status: Dict[str, FailoverStatus] = field(default_factory=dict)

    def register(self, node_id: str, is_primary: bool = False) -> None:
        if is_primary: self.primary = node_id
        else: self.secondaries.append(node_id)
        self.status[node_id] = FailoverStatus.ACTIVE if is_primary else FailoverStatus.STANDBY

    def failover(self, failed_node: str) -> Optional[str]:
        self.status[failed_node] = FailoverStatus.FAILED
        if failed_node == self.primary and self.secondaries:
            self.primary = self.secondaries[0]
            self.status[self.primary] = FailoverStatus.ACTIVE
            return self.primary
        return None

    def stats(self) -> dict:
        return {"primary": self.primary, "secondaries": len(self.secondaries), "status": {k:v.name for k,v in self.status.items()}}

def run():
    fh = FailoverHandler()
    fh.register("node1", True)
    fh.register("node2", False)
    print("Failover:", fh.failover("node1"))
    print("Stats:", fh.stats())

if __name__ == "__main__": run()
