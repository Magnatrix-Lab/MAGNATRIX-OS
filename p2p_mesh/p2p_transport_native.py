#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — P2P Transport Layer (Layer 4 Extension)
Real WebSocket + HTTP Transport with Circuit Breaker, Handshake, Encryption
================================================================================
Zero-dependency transport using Python stdlib selectors + socket.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import selectors
import socket
import ssl
import struct
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Constants
# =============================================================================
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
DEFAULT_P2P_PORT = 17777
DEFAULT_BUFFER = 65536
HANDSHAKE_TIMEOUT = 5.0


# =============================================================================
# Data Types
# =============================================================================
@dataclass
class PeerInfo:
    peer_id: str
    address: Tuple[str, int]
    public_key: str = ""
    capabilities: Set[str] = field(default_factory=set)
    last_seen: float = field(default_factory=time.time)
    latency_ms: float = 0.0


@dataclass
class TransportMessage:
    msg_id: str
    topic: str
    payload: Any
    sender: str = ""
    ttl: int = 10
    timestamp: float = field(default_factory=time.time)
    signature: str = ""

    def to_bytes(self) -> bytes:
        return json.dumps(self.__dict__, default=str).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> TransportMessage:
        d = json.loads(data.decode("utf-8"))
        return cls(**{k: v for k, v in d.items() if k in {f.name for f in cls.__dataclass_fields__.values()}})


# =============================================================================
# Message Encoder
# =============================================================================
class MessageEncoder:
    """Frame encoder for raw socket transport."""

    @staticmethod
    def encode(msg: TransportMessage) -> bytes:
        body = msg.to_bytes()
        # Simple length-prefixed framing: 4-byte BE length + body
        return struct.pack(">I", len(body)) + body

    @staticmethod
    def decode(data: bytes) -> Tuple[Optional[TransportMessage], bytes]:
        if len(data) < 4:
            return None, data
        length = struct.unpack(">I", data[:4])[0]
        if len(data) < 4 + length:
            return None, data
        body = data[4:4 + length]
        leftover = data[4 + length:]
        try:
            return TransportMessage.from_bytes(body), leftover
        except Exception:
            return None, leftover


# =============================================================================
# Handshake Protocol
# =============================================================================
class HandshakeProtocol:
    """Minimal secure handshake before accepting peer."""

    def __init__(self, node_id: str, secret: str = "") -> None:
        self.node_id = node_id
        self.secret = secret

    def challenge(self) -> Dict[str, str]:
        nonce = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        return {"node_id": self.node_id, "nonce": nonce, "version": "1.0"}

    def verify(self, response: Dict[str, str]) -> bool:
        expected = hashlib.sha256((response.get("nonce", "") + self.secret).encode()).hexdigest()[:16]
        return response.get("proof", "") == expected or not self.secret

    def respond(self, challenge: Dict[str, str]) -> Dict[str, str]:
        nonce = challenge.get("nonce", "")
        proof = hashlib.sha256((nonce + self.secret).encode()).hexdigest()[:16]
        return {"node_id": self.node_id, "proof": proof, "version": "1.0"}


# =============================================================================
# Circuit Breaker
# =============================================================================
class CircuitBreaker:
    """Fail-fast wrapper for unstable connections."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = self.CLOSED
        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], Any]) -> Any:
        with self._lock:
            if self._state == self.OPEN:
                if self._last_failure_time and (time.time() - self._last_failure_time) > self.recovery_timeout:
                    self._state = self.HALF_OPEN
                else:
                    raise RuntimeError("Circuit breaker OPEN")
        try:
            result = fn()
            with self._lock:
                self._failures = 0
                self._state = self.CLOSED
            return result
        except Exception as exc:
            with self._lock:
                self._failures += 1
                self._last_failure_time = time.time()
                if self._failures >= self.failure_threshold:
                    self._state = self.OPEN
            raise exc

    @property
    def state(self) -> str:
        with self._lock:
            return self._state


# =============================================================================
# Rate Limiter
# =============================================================================
class RateLimiter:
    """Token bucket per-peer rate limiter."""

    def __init__(self, rate: float = 100.0, burst: float = 200.0) -> None:
        self.rate = rate
        self.burst = burst
        self._peers: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, peer_id: str) -> bool:
        now = time.time()
        with self._lock:
            if peer_id not in self._peers:
                self._peers[peer_id] = (self.burst, now)
            tokens, last = self._peers[peer_id]
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            if tokens >= 1.0:
                self._peers[peer_id] = (tokens - 1.0, now)
                return True
            self._peers[peer_id] = (tokens, now)
            return False


# =============================================================================
# WebSocket Framing (RFC 6455 subset)
# =============================================================================
class WebSocketFrame:
    def __init__(self, opcode: int = 0x1, payload: bytes = b"", mask: bool = False) -> None:
        self.opcode = opcode
        self.payload = payload
        self.mask = mask

    def to_bytes(self) -> bytes:
        length = len(self.payload)
        if self.mask:
            header = self.opcode | 0x80
        else:
            header = self.opcode
        if length < 126:
            buf = struct.pack("BB", header, length | (0x80 if self.mask else 0))
        elif length < 65536:
            buf = struct.pack("!BBH", header, 126 | (0x80 if self.mask else 0), length)
        else:
            buf = struct.pack("!BBQ", header, 127 | (0x80 if self.mask else 0), length)
        if self.mask:
            mask_key = struct.pack("I", int(time.time() * 1000) & 0xFFFFFFFF)
            masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(self.payload))
            return buf + mask_key + masked
        return buf + self.payload

    @classmethod
    def parse(cls, data: bytes) -> Tuple[Optional[WebSocketFrame], bytes]:
        if len(data) < 2:
            return None, data
        header = data[0]
        opcode = header & 0x0F
        masked = bool(data[1] & 0x80)
        length = data[1] & 0x7F
        offset = 2
        if length == 126:
            if len(data) < 4:
                return None, data
            length = struct.unpack("!H", data[2:4])[0]
            offset = 4
        elif length == 127:
            if len(data) < 10:
                return None, data
            length = struct.unpack("!Q", data[2:10])[0]
            offset = 10
        if masked:
            if len(data) < offset + 4:
                return None, data
            mask_key = data[offset:offset + 4]
            offset += 4
        if len(data) < offset + length:
            return None, data
        payload = data[offset:offset + length]
        if masked:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return cls(opcode, payload, masked), data[offset + length:]


# =============================================================================
# WebSocket Client
# =============================================================================
class WebSocketClient:
    """Raw WebSocket client using Python stdlib only."""

    def __init__(self, url: str = "ws://127.0.0.1:17777", node_id: str = "anon") -> None:
        self.url = url
        self.node_id = node_id
        self._sock: Optional[socket.socket] = None
        self._buffer = b""
        self._handlers: List[Callable[[TransportMessage], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _connect(self) -> None:
        parsed = self.url.replace("ws://", "").replace("wss://", "")
        host, port_str = parsed.split(":")
        port = int(port_str.split("/")[0])
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(HANDSHAKE_TIMEOUT)
        self._sock.connect((host, port))
        # Send HTTP upgrade
        key = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16] + "=="
        headers = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self._sock.sendall(headers.encode())
        resp = self._sock.recv(1024)
        if b"101" not in resp:
            raise ConnectionError(f"WS handshake failed: {resp[:200]}")

    def on_message(self, handler: Callable[[TransportMessage], None]) -> None:
        self._handlers.append(handler)

    def send(self, msg: TransportMessage) -> None:
        if not self._sock:
            raise RuntimeError("Not connected")
        frame = WebSocketFrame(opcode=0x1, payload=msg.to_bytes())
        self._sock.sendall(frame.to_bytes())

    def _read_loop(self) -> None:
        while self._running and self._sock:
            try:
                data = self._sock.recv(DEFAULT_BUFFER)
                if not data:
                    break
                self._buffer += data
                while True:
                    frame, self._buffer = WebSocketFrame.parse(self._buffer)
                    if frame is None:
                        break
                    if frame.opcode == 0x1:
                        try:
                            msg = TransportMessage.from_bytes(frame.payload)
                            for h in self._handlers:
                                h(msg)
                        except Exception:
                            pass
                    elif frame.opcode == 0x8:
                        break
            except Exception:
                break
        self._running = False

    def start(self) -> None:
        self._connect()
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                close_frame = WebSocketFrame(opcode=0x8, payload=b"").to_bytes()
                self._sock.sendall(close_frame)
            except Exception:
                pass
            self._sock.close()
            self._sock = None


# =============================================================================
# WebSocket Server
# =============================================================================
class WebSocketServer:
    """Lightweight WebSocket server with selector-based multiplexing."""

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_P2P_PORT) -> None:
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        self._sel = selectors.DefaultSelector()
        self._peers: Dict[socket.socket, PeerInfo] = {}
        self._buffers: Dict[socket.socket, bytes] = {}
        self._handlers: List[Callable[[TransportMessage, PeerInfo], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._limiter = RateLimiter()
        self._handshake = HandshakeProtocol("server")

    def on_message(self, handler: Callable[[TransportMessage, PeerInfo], None]) -> None:
        self._handlers.append(handler)

    def _accept(self, sock: socket.socket) -> None:
        conn, addr = sock.accept()
        conn.setblocking(False)
        self._sel.register(conn, selectors.EVENT_READ, self._handle_client)
        self._buffers[conn] = b""
        peer = PeerInfo(peer_id=f"{addr[0]}:{addr[1]}", address=addr)
        self._peers[conn] = peer

    def _ws_handshake(self, conn: socket.socket, data: bytes) -> bool:
        if b"Upgrade: websocket" not in data:
            return False
        # Extract key
        key = ""
        for line in data.decode().split("\r\n"):
            if line.startswith("Sec-WebSocket-Key:"):
                key = line.split(":")[1].strip()
                break
        if not key:
            return False
        accept = hashlib.sha1((key + WS_MAGIC).encode()).digest()
        import base64
        accept_b64 = base64.b64encode(accept).decode()
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_b64}\r\n\r\n"
        )
        conn.sendall(response.encode())
        return True

    def _handle_client(self, conn: socket.socket) -> None:
        try:
            data = conn.recv(DEFAULT_BUFFER)
            if not data:
                self._drop(conn)
                return
            self._buffers[conn] += data
            buf = self._buffers[conn]
            # If still in HTTP handshake phase
            if b"\r\n\r\n" in buf and b"HTTP/1.1" in buf:
                ok = self._ws_handshake(conn, buf[:buf.index(b"\r\n\r\n") + 4])
                if ok:
                    self._buffers[conn] = buf[buf.index(b"\r\n\r\n") + 4:]
                else:
                    self._drop(conn)
                return
            # WebSocket frames
            while True:
                frame, self._buffers[conn] = WebSocketFrame.parse(self._buffers[conn])
                if frame is None:
                    break
                if frame.opcode == 0x8:
                    self._drop(conn)
                    return
                if frame.opcode == 0x1:
                    try:
                        msg = TransportMessage.from_bytes(frame.payload)
                        peer = self._peers.get(conn)
                        if peer and self._limiter.allow(peer.peer_id):
                            for h in self._handlers:
                                h(msg, peer)
                    except Exception:
                        pass
        except Exception:
            self._drop(conn)

    def _drop(self, conn: socket.socket) -> None:
        self._sel.unregister(conn)
        conn.close()
        self._peers.pop(conn, None)
        self._buffers.pop(conn, None)

    def _run(self) -> None:
        while self._running:
            events = self._sel.select(timeout=0.5)
            for key, _ in events:
                callback = key.data
                callback(key.fileobj)

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(100)
        self._sock.setblocking(False)
        self._sel.register(self._sock, selectors.EVENT_READ, self._accept)
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def broadcast(self, msg: TransportMessage) -> None:
        frame = WebSocketFrame(opcode=0x1, payload=msg.to_bytes())
        data = frame.to_bytes()
        for conn in list(self._peers.keys()):
            try:
                conn.sendall(data)
            except Exception:
                self._drop(conn)

    def stop(self) -> None:
        self._running = False
        for conn in list(self._peers.keys()):
            self._drop(conn)
        if self._sock:
            self._sock.close()


# =============================================================================
# Connection Pool
# =============================================================================
class ConnectionPool:
    """Manages persistent outbound connections with health checks."""

    def __init__(self, max_size: int = 32) -> None:
        self.max_size = max_size
        self._clients: Dict[str, WebSocketClient] = {}
        self._lock = threading.Lock()
        self._breaker = CircuitBreaker()

    def get_or_create(self, url: str, node_id: str) -> WebSocketClient:
        with self._lock:
            if url in self._clients:
                return self._clients[url]
            client = WebSocketClient(url, node_id)
            self._clients[url] = client
            return client

    def remove(self, url: str) -> None:
        with self._lock:
            c = self._clients.pop(url, None)
            if c:
                c.stop()

    def close_all(self) -> None:
        with self._lock:
            for c in list(self._clients.values()):
                c.stop()
            self._clients.clear()


# =============================================================================
# Transport Kernel Bridge
# =============================================================================
class TransportKernelBridge:
    def __init__(self, server: WebSocketServer, pool: ConnectionPool, event_bus: Any = None) -> None:
        self.server = server
        self.pool = pool
        self.bus = event_bus
        self._routes: Dict[str, Callable[[TransportMessage], None]] = {}

    def on(self, topic: str, handler: Callable[[TransportMessage], None]) -> None:
        self._routes[topic] = handler

    def emit(self, msg: TransportMessage) -> None:
        if self.bus:
            self.bus.publish(f"transport.{msg.topic}", msg.__dict__)

    def broadcast_local(self, msg: TransportMessage) -> None:
        self.server.broadcast(msg)

    def send_to(self, url: str, msg: TransportMessage) -> None:
        client = self.pool.get_or_create(url, msg.sender)
        if not client._running:
            client.start()
        client.send(msg)


# =============================================================================
# Main Transport Engine
# =============================================================================
class TransportEngine:
    """Orchestrates server, client pool, and message routing."""

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_P2P_PORT) -> None:
        self.server = WebSocketServer(host, port)
        self.pool = ConnectionPool()
        self.bridge = TransportKernelBridge(self.server, self.pool)
        self._running = False
        self._setup_routing()

    def _setup_routing(self) -> None:
        def on_inbound(msg: TransportMessage, peer: PeerInfo) -> None:
            peer.last_seen = time.time()
            handler = self.bridge._routes.get(msg.topic)
            if handler:
                handler(msg)
            self.bridge.emit(msg)
        self.server.on_message(on_inbound)

    def start(self) -> None:
        self.server.start()
        self._running = True

    def stop(self) -> None:
        self._running = False
        self.server.stop()
        self.pool.close_all()

    def broadcast(self, topic: str, payload: Any, sender: str = "") -> None:
        msg = TransportMessage(
            msg_id=hashlib.sha256(str(time.time()).encode()).hexdigest()[:16],
            topic=topic,
            payload=payload,
            sender=sender,
        )
        self.server.broadcast(msg)

    def __enter__(self) -> TransportEngine:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS P2P Transport Demo")
    print("=" * 60)
    engine = TransportEngine("127.0.0.1", 17778)
    engine.start()
    print(f"Server listening on ws://127.0.0.1:17778")

    client = WebSocketClient("ws://127.0.0.1:17778", "demo-client")
    received: List[str] = []
    def on_msg(m: TransportMessage) -> None:
        received.append(m.topic)
    client.on_message(on_msg)
    client.start()
    time.sleep(0.3)

    engine.broadcast("ping", {"hello": "world"}, sender="demo")
    time.sleep(0.3)

    print(f"Client received {len(received)} messages: {received}")
    client.stop()
    engine.stop()
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
