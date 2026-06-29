"""WebSocket Server — WebSocket server simulation, handshake, frame parsing."""
from dataclasses import dataclass
from pathlib import Path
import json, base64, hashlib

@dataclass
class WSConnection:
    conn_id: str = ""
    state: str = "connecting"  # connecting | open | closing | closed
    client_ip: str = ""
    handshake_complete: bool = False
    last_frame_time: float = 0.0

class WebSocketServer:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._connections: dict[str, WSConnection] = {}
        self._frame_log: list[dict] = []
        self._persist_path = self.root / "websocket_server.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._connections = {k: WSConnection(**v) for k, v in data.get("connections", {}).items()}
            self._frame_log = data.get("frame_log", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "connections": {k: v.__dict__ for k, v in self._connections.items()},
            "frame_log": self._frame_log
        }, indent=2))

    def generate_accept_key(self, client_key: str) -> str:
        magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        sha = hashlib.sha1((client_key + magic).encode()).digest()
        return base64.b64encode(sha).decode()

    def handshake(self, client_key: str, client_ip: str) -> tuple[str, WSConnection]:
        accept_key = self.generate_accept_key(client_key)
        conn_id = f"ws_{len(self._connections)}"
        conn = WSConnection(conn_id=conn_id, state="open", client_ip=client_ip, handshake_complete=True)
        self._connections[conn_id] = conn
        self._save()
        return accept_key, conn

    def receive_frame(self, conn_id: str, opcode: int, payload: str) -> dict:
        conn = self._connections.get(conn_id)
        if not conn or conn.state != "open":
            return {"error": "connection not open"}
        self._frame_log.append({"conn_id": conn_id, "opcode": opcode, "payload_len": len(payload)})
        self._save()
        return {"conn_id": conn_id, "opcode": opcode, "payload": payload}

    def close_connection(self, conn_id: str, code: int = 1000) -> bool:
        conn = self._connections.get(conn_id)
        if conn:
            conn.state = "closed"
            self._save()
            return True
        return False

    def list_connections(self) -> list[WSConnection]:
        return [c for c in self._connections.values() if c.state == "open"]

    def to_dict(self) -> dict:
        return {"connection_count": len(self._connections), "open": len(self.list_connections())}

    def get_stats(self) -> dict:
        return {"total": len(self._connections), "open": len(self.list_connections()), "frames": len(self._frame_log)}

__all__ = ["WebSocketServer", "WSConnection"]
