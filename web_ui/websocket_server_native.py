"""web_ui/websocket_server_native.py — WebSocket server"""
from __future__ import annotations
import base64
import hashlib
import json
import struct
import threading
import time
from typing import Any, Dict, List, Optional, Set

class WebSocketServer:
    """WebSocket server with rooms and broadcasting."""

    def __init__(self):
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.rooms: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    def connect(self, client_id: str) -> None:
        with self._lock:
            self.connections[client_id] = {
                "joined": time.time(),
                "rooms": set(),
            }

    def disconnect(self, client_id: str) -> None:
        with self._lock:
            if client_id in self.connections:
                for room in self.connections[client_id]["rooms"]:
                    self.rooms.get(room, set()).discard(client_id)
                del self.connections[client_id]

    def join_room(self, client_id: str, room: str) -> None:
        with self._lock:
            if client_id in self.connections:
                self.connections[client_id]["rooms"].add(room)
                if room not in self.rooms:
                    self.rooms[room] = set()
                self.rooms[room].add(client_id)

    def broadcast(self, room: str, message: Dict[str, Any]) -> int:
        with self._lock:
            clients = self.rooms.get(room, set()).copy()

        count = 0
        for client_id in clients:
            if client_id in self.connections:
                count += 1
        return count

    def parse_frame(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse WebSocket frame."""
        if len(data) < 2:
            return None

        opcode = data[0] & 0x0F
        masked = (data[1] & 0x80) != 0
        length = data[1] & 0x7F

        payload_start = 2
        if length == 126:
            length = struct.unpack(">H", data[2:4])[0]
            payload_start = 4
        elif length == 127:
            length = struct.unpack(">Q", data[2:10])[0]
            payload_start = 10

        if masked:
            mask = data[payload_start:payload_start + 4]
            payload_start += 4
            payload = bytearray(data[payload_start:payload_start + length])
            for i in range(len(payload)):
                payload[i] ^= mask[i % 4]
        else:
            payload = data[payload_start:payload_start + length]

        return {
            "opcode": opcode,
            "text": payload.decode("utf-8", errors="replace") if opcode == 1 else "",
            "binary": payload if opcode == 2 else b"",
        }

if __name__ == "__main__":
    print("WebSocketServer self-test")
    ws = WebSocketServer()
    ws.connect("client_1")
    ws.join_room("room_1", "client_1")
    count = ws.broadcast("room_1", {"msg": "hello"})
    assert count == 1
    print("All tests pass")
