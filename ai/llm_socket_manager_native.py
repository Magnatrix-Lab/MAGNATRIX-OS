"""Socket Manager - Socket state tracking for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum, auto
import time

class SocketState(Enum):
    CLOSED = auto(); LISTEN = auto(); SYN_SENT = auto(); SYN_RECV = auto(); ESTABLISHED = auto(); CLOSE_WAIT = auto()

@dataclass
class SocketManager:
    sockets: Dict[str, Dict] = field(default_factory=dict)

    def create(self, socket_id: str, state: SocketState = SocketState.CLOSED) -> None:
        self.sockets[socket_id] = {"state": state, "created": time.time(), "bytes_sent": 0, "bytes_recv": 0}

    def transition(self, socket_id: str, new_state: SocketState) -> bool:
        if socket_id not in self.sockets: return False
        self.sockets[socket_id]["state"] = new_state
        return True

    def send_data(self, socket_id: str, bytes_count: int) -> None:
        if socket_id in self.sockets: self.sockets[socket_id]["bytes_sent"] += bytes_count

    def stats(self) -> dict:
        states = {}
        for info in self.sockets.values():
            states[info["state"].name] = states.get(info["state"].name, 0) + 1
        return {"total": len(self.sockets), "states": states}

def run():
    sm = SocketManager()
    sm.create("sock1", SocketState.LISTEN)
    sm.transition("sock1", SocketState.ESTABLISHED)
    sm.send_data("sock1", 1024)
    print("Stats:", sm.stats())

if __name__ == "__main__": run()
