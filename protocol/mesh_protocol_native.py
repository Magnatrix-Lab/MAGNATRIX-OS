"""protocol/mesh_protocol_native.py — Mesh network protocol"""
from __future__ import annotations
import json
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

@dataclass
class MeshMessage:
    msg_type: str = "data"
    sender: str = ""
    target: str = ""
    payload: Any = None
    ttl: int = 10
    timestamp: float = 0.0
    id: str = ""

class MeshProtocol:
    """Mesh protocol with framing, heartbeat, and routing."""

    MSG_TYPES = {"data", "heartbeat", "route", "ack", "broadcast"}

    def __init__(self, node_id: str = ""):
        self.node_id = node_id or f"node_{int(time.time() * 1000) % 10000}"
        self.neighbors: Set[str] = set()
        self.routes: Dict[str, str] = {}
        self.seen_ids: Set[str] = set()

    def frame_message(self, msg: MeshMessage) -> bytes:
        """Frame message with length prefix."""
        data = json.dumps({
            "type": msg.msg_type,
            "sender": msg.sender,
            "target": msg.target,
            "payload": msg.payload,
            "ttl": msg.ttl,
            "timestamp": msg.timestamp,
            "id": msg.id,
        }).encode()
        return struct.pack(">I", len(data)) + data

    def parse_frame(self, data: bytes) -> Optional[MeshMessage]:
        """Parse framed message."""
        if len(data) < 4:
            return None
        length = struct.unpack(">I", data[:4])[0]
        if len(data) < 4 + length:
            return None
        body = json.loads(data[4:4+length])
        return MeshMessage(**body)

    def heartbeat(self) -> MeshMessage:
        return MeshMessage(
            msg_type="heartbeat",
            sender=self.node_id,
            target="broadcast",
            payload={"neighbors": list(self.neighbors)},
            timestamp=time.time(),
        )

    def route_advertisement(self) -> MeshMessage:
        return MeshMessage(
            msg_type="route",
            sender=self.node_id,
            target="broadcast",
            payload={"routes": self.routes},
            timestamp=time.time(),
        )

    def should_forward(self, msg: MeshMessage) -> bool:
        if msg.id in self.seen_ids:
            return False
        self.seen_ids.add(msg.id)
        if msg.ttl <= 0:
            return False
        msg.ttl -= 1
        return True

if __name__ == "__main__":
    print("MeshProtocol self-test")
    mp = MeshProtocol("node_a")
    msg = mp.heartbeat()
    framed = mp.frame_message(msg)
    parsed = mp.parse_frame(framed)
    assert parsed is not None
    assert parsed.msg_type == "heartbeat"
    print("All tests pass")
