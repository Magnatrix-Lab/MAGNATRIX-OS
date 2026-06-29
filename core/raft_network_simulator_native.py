"""Raft Network Simulator — Delay, partition, packet loss."""
from dataclasses import dataclass
from pathlib import Path
import json, random

@dataclass
class NetworkCondition:
    latency_ms: int = 0
    packet_loss_pct: float = 0.0
    partition: bool = False
    bandwidth_kbps: int = 100000

class RaftNetworkSimulator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._links: dict[str, NetworkCondition] = {}
        self._events: list[dict] = []
        self._persist_path = self.root / "raft_network.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._links = {k: NetworkCondition(**v) for k, v in data.get("links", {}).items()}
            self._events = data.get("events", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "links": {k: v.__dict__ for k, v in self._links.items()},
            "events": self._events
        }, indent=2))

    def set_link(self, node_a: str, node_b: str, latency_ms: int = 0, loss_pct: float = 0.0) -> None:
        key = f"{node_a}:{node_b}"
        self._links[key] = NetworkCondition(latency_ms=latency_ms, packet_loss_pct=loss_pct)
        self._save()

    def simulate_send(self, from_node: str, to_node: str, msg: dict) -> dict | None:
        key = f"{from_node}:{to_node}"
        cond = self._links.get(key, NetworkCondition())
        if cond.partition:
            self._events.append({"event": "dropped_partition", "from": from_node, "to": to_node})
            self._save()
            return None
        if random.random() * 100 < cond.packet_loss_pct:
            self._events.append({"event": "dropped_loss", "from": from_node, "to": to_node})
            self._save()
            return None
        self._events.append({"event": "delivered", "from": from_node, "to": to_node, "latency_ms": cond.latency_ms})
        self._save()
        return msg

    def partition(self, nodes: list[str]) -> None:
        for a in nodes:
            for b in nodes:
                if a != b:
                    key = f"{a}:{b}"
                    cond = self._links.get(key, NetworkCondition())
                    cond.partition = True
                    self._links[key] = cond
        self._events.append({"event": "partition", "nodes": nodes})
        self._save()

    def heal(self, nodes: list[str]) -> None:
        for a in nodes:
            for b in nodes:
                if a != b:
                    key = f"{a}:{b}"
                    cond = self._links.get(key, NetworkCondition())
                    cond.partition = False
                    self._links[key] = cond
        self._events.append({"event": "heal", "nodes": nodes})
        self._save()

    def to_dict(self) -> dict:
        return {"link_count": len(self._links), "event_count": len(self._events)}

    def get_stats(self) -> dict:
        partitions = sum(1 for c in self._links.values() if c.partition)
        return {"links": len(self._links), "partitions": partitions, "events": len(self._events)}

__all__ = ["RaftNetworkSimulator", "NetworkCondition"]
