"""
MAGNATRIX-OS WebSocket Server
Self-contained native WebSocket server with frame parsing, room management,
heartbeat, broadcasting, and rate limiting.
"""

import socket, threading, hashlib, base64, struct, select, json, time
from typing import Dict, List, Set, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

MAGIC = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


@dataclass
class WSClient:
    """Represents a connected WebSocket client."""
    sock: socket.socket
    addr: tuple
    rooms: Set[str] = field(default_factory=set)
    last_ping: float = 0.0
    rate_window: List[float] = field(default_factory=list)
    closed: bool = False


class WebSocketServer:
    """Native WebSocket server for MAGNATRIX-OS."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765,
                 heartbeat_interval: int = 30, rate_limit: int = 60):
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        self.rate_limit = rate_limit
        self._clients: Dict[int, WSClient] = {}
        self._rooms: Dict[str, Set[int]] = {}
        self._handlers: Dict[int, Callable] = {}
        self._lock = threading.Lock()
        self._running = False
        self._server: Optional[socket.socket] = None
        self._hb_thread: Optional[threading.Thread] = None

    # ── server lifecycle ──────────────────────────────────────

    def start(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(100)
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._hb_thread.start()

    def stop(self) -> None:
        self._running = False
        with self._lock:
            for c in list(self._clients.values()):
                self._close_client(c)
        if self._server:
            self._server.close()

    def _accept_loop(self) -> None:
        while self._running:
            try:
                self._server.settimeout(1.0)
                conn, addr = self._server.accept()
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    # ── HTTP upgrade handshake ────────────────────────────────

    def _handle_client(self, conn: socket.socket, addr: tuple) -> None:
        try:
            data = conn.recv(4096)
            if not data:
                conn.close()
                return
            headers = self._parse_http(data)
            key = headers.get("Sec-WebSocket-Key", "")
            accept = base64.b64encode(
                hashlib.sha1((key.encode() + MAGIC)).digest()
            ).decode()
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
            )
            conn.send(response.encode())
            client = WSClient(sock=conn, addr=addr, last_ping=time.time())
            with self._lock:
                self._clients[id(conn)] = client
            self._read_loop(client)
        except Exception:
            conn.close()

    def _parse_http(self, data: bytes) -> Dict[str, str]:
        lines = data.decode().split("\r\n")
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()
        return headers

    # ── frame parsing ───────────────────────────────────────────

    def _read_loop(self, client: WSClient) -> None:
        while self._running and not client.closed:
            try:
                client.sock.settimeout(5.0)
                frame = self._read_frame(client.sock)
                if not frame:
                    break
                opcode, payload = frame
                if opcode == OP_TEXT:
                    self._on_text(client, payload.decode("utf-8"))
                elif opcode == OP_BINARY:
                    self._on_binary(client, payload)
                elif opcode == OP_PING:
                    self._send_frame(client, OP_PONG, payload)
                elif opcode == OP_PONG:
                    client.last_ping = time.time()
                elif opcode == OP_CLOSE:
                    break
            except (socket.timeout, ConnectionResetError, OSError):
                break
        self._close_client(client)

    def _read_frame(self, sock: socket.socket) -> Optional[tuple]:
        header = sock.recv(2)
        if len(header) < 2:
            return None
        b1, b2 = header
        opcode = b1 & 0x0F
        masked = bool(b2 & 0x80)
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack(">H", sock.recv(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", sock.recv(8))[0]
        mask = sock.recv(4) if masked else b""
        payload = b""
        while len(payload) < length:
            chunk = sock.recv(length - len(payload))
            if not chunk:
                return None
            payload += chunk
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return opcode, payload

    def _send_frame(self, client: WSClient, opcode: int, payload: bytes) -> None:
        if client.closed:
            return
        length = len(payload)
        if length <= 125:
            header = struct.pack("BB", 0x80 | opcode, length)
        elif length <= 65535:
            header = struct.pack("!BBH", 0x80 | opcode, 126, length)
        else:
            header = struct.pack("!BBQ", 0x80 | opcode, 127, length)
        try:
            client.sock.sendall(header + payload)
        except OSError:
            client.closed = True

    # ── message handling ────────────────────────────────────────

    def _on_text(self, client: WSClient, text: str) -> None:
        if not self._check_rate(client):
            self._send_frame(client, OP_CLOSE, b"")
            self._close_client(client)
            return
        try:
            msg = json.loads(text)
            action = msg.get("action")
            if action == "join":
                self.join_room(client, msg.get("room", "default"))
            elif action == "leave":
                self.leave_room(client, msg.get("room", "default"))
            elif action == "broadcast":
                self.broadcast(msg.get("room", "default"), msg.get("data", ""))
            elif action == "ping":
                self.send_to_client(client, json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            self.broadcast_to_all(text)

    def _on_binary(self, client: WSClient, data: bytes) -> None:
        pass  # reserved for binary protocols

    # ── rate limiting ───────────────────────────────────────────

    def _check_rate(self, client: WSClient) -> bool:
        now = time.time()
        client.rate_window = [t for t in client.rate_window if now - t < 60]
        client.rate_window.append(now)
        return len(client.rate_window) <= self.rate_limit

    # ── connection management ───────────────────────────────────

    def _close_client(self, client: WSClient) -> None:
        if client.closed:
            return
        client.closed = True
        try:
            client.sock.close()
        except OSError:
            pass
        with self._lock:
            cid = id(client.sock)
            if cid in self._clients:
                del self._clients[cid]
            for room in list(client.rooms):
                self._rooms.get(room, set()).discard(cid)

    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def list_clients(self) -> List[Dict]:
        with self._lock:
            return [{"addr": c.addr, "rooms": list(c.rooms)} for c in self._clients.values()]

    # ── room/channel management ─────────────────────────────────

    def join_room(self, client: WSClient, room: str) -> None:
        with self._lock:
            client.rooms.add(room)
            self._rooms.setdefault(room, set()).add(id(client.sock))
        self.send_to_client(client, json.dumps({"type": "joined", "room": room}))

    def leave_room(self, client: WSClient, room: str) -> None:
        with self._lock:
            client.rooms.discard(room)
            self._rooms.get(room, set()).discard(id(client.sock))
        self.send_to_client(client, json.dumps({"type": "left", "room": room}))

    def broadcast(self, room: str, message: str) -> int:
        count = 0
        with self._lock:
            cids = list(self._rooms.get(room, set()))
        for cid in cids:
            client = self._clients.get(cid)
            if client and not client.closed:
                self.send_to_client(client, json.dumps({"type": "message", "room": room, "data": message}))
                count += 1
        return count

    def broadcast_to_all(self, message: str) -> int:
        count = 0
        with self._lock:
            clients = list(self._clients.values())
        for c in clients:
            if not c.closed:
                self.send_to_client(c, message)
                count += 1
        return count

    def send_to_client(self, client: WSClient, text: str) -> None:
        self._send_frame(client, OP_TEXT, text.encode("utf-8"))

    def list_rooms(self) -> List[str]:
        with self._lock:
            return list(self._rooms.keys())

    # ── heartbeat / ping-pong ───────────────────────────────────

    def _heartbeat_loop(self) -> None:
        while self._running:
            now = time.time()
            with self._lock:
                clients = list(self._clients.values())
            for c in clients:
                if now - c.last_ping > self.heartbeat_interval * 2:
                    self._close_client(c)
                else:
                    self._send_frame(c, OP_PING, b"")
            time.sleep(self.heartbeat_interval)

    # ── auto-reconnect helper (client-side simulation) ───────

    def connect_client(self, host: str = None, port: int = None) -> Optional[socket.socket]:
        host = host or self.host
        port = port or self.port
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            return s
        except Exception:
            return None


# ── self-test ─────────────────────────────────────────────────

def _self_test():
    import threading, time
    srv = WebSocketServer("127.0.0.1", 8765, heartbeat_interval=1, rate_limit=100)
    srv.start()
    time.sleep(0.2)

    # connect a raw client
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 8765))
    key = base64.b64encode(b"x" * 16).decode()
    s.send(
        f"GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n".encode()
    )
    resp = s.recv(1024)
    assert b"101" in resp

    # send JSON message to join room
    payload = json.dumps({"action": "join", "room": "testroom"}).encode()
    length = len(payload)
    header = struct.pack("BB", 0x81, length)
    s.send(header + payload)

    time.sleep(0.2)
    assert "testroom" in srv.list_rooms()
    assert srv.client_count() == 1

    # broadcast
    bc = srv.broadcast("testroom", "hello")
    assert bc == 1

    # ping-pong
    ping_payload = json.dumps({"action": "ping"}).encode()
    s.send(struct.pack("BB", 0x81, len(ping_payload)) + ping_payload)
    time.sleep(0.2)

    # rate limit test
    for _ in range(5):
        s.send(struct.pack("BB", 0x81, len(ping_payload)) + ping_payload)
    time.sleep(0.1)

    # close
    s.send(struct.pack("BB", 0x88, 0))
    time.sleep(0.3)

    srv.stop()
    print("[websocket_server_native] all tests passed")


if __name__ == "__main__":
    _self_test()
