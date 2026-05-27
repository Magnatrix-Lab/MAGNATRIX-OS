#!/usr/bin/env python3
"""
MAGNATRIX-OS WebSocket Server — Pure Python stdlib
Native socket implementation, no external dependencies.

Broadcasts live metrics every 1-3 seconds:
  system    → CPU, memory, disk, uptime
  llm       → model load, tokens/sec, queue depth, latency
  trading   → NAV, PnL, open positions, signal count
  p2p       → peers, bandwidth, message rate
  governance→ constitution status, active agents, task flow
  security  → threat level, blocked events, audit score

Usage:
    python3 websocket_server_native.py          # start on 0.0.0.0:8765
    python3 websocket_server_native.py 8766     # custom port
    python3 websocket_server_native.py --daemon   # background
"""

import sys, os, json, time, struct, base64, hashlib, threading, socket, select, random, math
from datetime import datetime, timezone
from collections import deque

# ────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────
HOST = os.environ.get("WS_HOST", "0.0.0.0")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8765
BROADCAST_INTERVAL = 2.0          # seconds between metric pushes
HEARTBEAT_INTERVAL = 30.0         # seconds between server→client pings
MAX_FRAME_SIZE = 65536

# ────────────────────────────────────────────────
# WebSocket Protocol Helpers
# ─────────────────────────────────────────────────
WS_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def make_accept_key(key: str) -> str:
    sha = hashlib.sha1((key + WS_GUID.decode()).encode())
    return base64.b64encode(sha.digest()).decode()


def encode_frame(payload: bytes, opcode: int = 0x1, fin: bool = True) -> bytes:
    """Encode a WebSocket frame. opcode 0x1=text, 0x2=binary, 0x8=close, 0x9=ping, 0xA=pong."""
    frame = bytearray()
    b0 = (0x80 if fin else 0x00) | (opcode & 0x0F)
    frame.append(b0)
    length = len(payload)
    if length < 126:
        frame.append(length)  # server→client: no mask bit
    elif length < 65536:
        frame.append(126)
        frame.extend(struct.pack(">H", length))
    else:
        frame.append(127)
        frame.extend(struct.pack(">Q", length))
    frame.extend(payload)
    return bytes(frame)


def decode_frame(buf: bytearray) -> tuple:
    """
    Attempt to parse one WebSocket frame from `buf`.
    Returns (opcode, payload, consumed_bytes) or (None, None, 0) if incomplete.
    """
    if len(buf) < 2:
        return None, None, 0
    b0, b1 = buf[0], buf[1]
    fin = bool(b0 & 0x80)
    opcode = b0 & 0x0F
    masked = bool(b1 & 0x80)
    length = b1 & 0x7F
    offset = 2
    if length == 126:
        if len(buf) < 4:
            return None, None, 0
        length = struct.unpack(">H", buf[2:4])[0]
        offset = 4
    elif length == 127:
        if len(buf) < 10:
            return None, None, 0
        length = struct.unpack(">Q", buf[2:10])[0]
        offset = 10
    mask_key = None
    if masked:
        if len(buf) < offset + 4:
            return None, None, 0
        mask_key = buf[offset:offset + 4]
        offset += 4
    if len(buf) < offset + length:
        return None, None, 0
    payload = buf[offset:offset + length]
    if masked and mask_key:
        payload = bytearray(payload)
        for i in range(length):
            payload[i] ^= mask_key[i % 4]
        payload = bytes(payload)
    del buf[:offset + length]
    return opcode, payload, (offset + length)


def make_handshake_response(key: str) -> bytes:
    accept = make_accept_key(key)
    return (
        b"HTTP/1.1 101 Switching Protocols\r\n"
        b"Upgrade: websocket\r\n"
        b"Connection: Upgrade\r\n"
        b"Sec-WebSocket-Accept: " + accept.encode() + b"\r\n"
        b"\r\n"
    )


# ────────────────────────────────────────────────
# Simulated Metrics Engine
# ────────────────────────────────────────────────
class MetricsEngine:
    """Generate plausible live metrics without external deps."""

    def __init__(self):
        self.start_ts = time.time()
        self._history = {"trading": deque(maxlen=60), "llm": deque(maxlen=60)}
        self._base_nav = 1_000_000.0
        self._last_nav = self._base_nav
        self._positions = []
        self._threat_level = "green"
        self._threat_counter = 0

    def _system(self) -> dict:
        uptime = time.time() - self.start_ts
        # Simulate with deterministic noise based on uptime
        cpu = 15.0 + 25.0 * abs(math.sin(uptime * 0.07)) + random.gauss(0, 3)
        mem = 42.0 + 20.0 * abs(math.sin(uptime * 0.05)) + random.gauss(0, 2)
        disk = 68.0 + random.gauss(0, 0.5)
        return {
            "cpu_percent": round(max(0, min(100, cpu)), 2),
            "mem_percent": round(max(0, min(100, mem)), 2),
            "disk_percent": round(max(0, min(100, disk)), 2),
            "uptime_seconds": round(uptime, 1),
            "load_avg": [round(cpu / 100 * 4 + random.gauss(0, 0.1), 2) for _ in range(3)],
            "hostname": os.environ.get("HOSTNAME", "magnatrix-node"),
        }

    def _llm(self) -> dict:
        uptime = time.time() - self.start_ts
        tps = 45.0 + 30.0 * abs(math.sin(uptime * 0.12)) + random.gauss(0, 5)
        queue = max(0, int(3 + 5 * math.sin(uptime * 0.09) + random.gauss(0, 1)))
        latency = 120.0 + 80.0 * abs(math.cos(uptime * 0.06)) + random.gauss(0, 10)
        model = "kimi-k2p6"
        return {
            "model": model,
            "tokens_per_sec": round(max(0, tps), 1),
            "queue_depth": queue,
            "avg_latency_ms": round(max(10, latency), 1),
            "requests_total": int(uptime * 0.8),
            "errors_total": int(uptime * 0.01),
        }

    def _trading(self) -> dict:
        uptime = time.time() - self.start_ts
        drift = random.gauss(0, 800)
        nav = self._last_nav + drift
        self._last_nav = nav
        pnl = nav - self._base_nav
        # Simulate positions
        if random.random() < 0.1:
            self._positions.append({"sym": random.choice(["BTC","ETH","SOL"]),
                                     "side": random.choice(["LONG","SHORT"]),
                                     "size": round(random.uniform(0.1, 2.0), 4),
                                     "entry": round(random.uniform(3000, 70000), 2)})
        if len(self._positions) > 5:
            self._positions.pop(0)
        signals = int(2 + 3 * abs(math.sin(uptime * 0.04)))
        return {
            "nav": round(nav, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl / self._base_nav * 100, 3),
            "open_positions": len(self._positions),
            "positions": self._positions[-3:],
            "signals_24h": signals,
            "win_rate": round(55 + 15 * math.sin(uptime * 0.02), 1),
            "sharpe": round(0.8 + 0.6 * math.sin(uptime * 0.03), 2),
        }

    def _p2p(self) -> dict:
        uptime = time.time() - self.start_ts
        peers = max(1, int(5 + 8 * math.sin(uptime * 0.03) + random.gauss(0, 1)))
        bw_up = 120.0 + 60.0 * abs(math.sin(uptime * 0.08)) + random.gauss(0, 10)
        bw_down = 250.0 + 100.0 * abs(math.cos(uptime * 0.07)) + random.gauss(0, 15)
        msg_rate = 15.0 + 20.0 * abs(math.sin(uptime * 0.11)) + random.gauss(0, 3)
        return {
            "peers_connected": peers,
            "bandwidth_up_kbps": round(max(0, bw_up), 1),
            "bandwidth_down_kbps": round(max(0, bw_down), 1),
            "messages_per_sec": round(max(0, msg_rate), 1),
            "topic_subscriptions": ["/magnatrix/tasks", "/magnatrix/signals", "/magnatrix/heartbeat"],
        }

    def _governance(self) -> dict:
        uptime = time.time() - self.start_ts
        agents = max(2, int(3 + 4 * math.sin(uptime * 0.025)))
        tasks_in = int(uptime * 0.3)
        tasks_out = int(tasks_in * 0.85)
        tasks_rej = int(tasks_in * 0.05)
        return {
            "constitution_active": True,
            "constitution_version": "v1.2.0",
            "agents_online": agents,
            "tasks_inbox": max(0, tasks_in - tasks_out - tasks_rej),
            "tasks_completed": tasks_out,
            "tasks_rejected": tasks_rej,
            "memory_chunks": int(1200 + 400 * math.sin(uptime * 0.015)),
            "skills_loaded": 18,
        }

    def _security(self) -> dict:
        uptime = time.time() - self.start_ts
        self._threat_counter += 1
        # Occasionally flip threat level for drama
        if self._threat_counter % 47 == 0:
            self._threat_level = random.choice(["green", "yellow", "green", "green"])
        blocked = int(uptime * 0.05 + random.gauss(0, 2))
        audit = 94.0 + 5.0 * math.sin(uptime * 0.04) + random.gauss(0, 1)
        return {
            "threat_level": self._threat_level,
            "blocked_events": max(0, blocked),
            "audit_score": round(max(0, min(100, audit)), 1),
            "last_scan": datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z",
            "firewall_rules_active": 42,
            "anomalies_24h": max(0, int(blocked * 0.1)),
        }

    def snapshot(self) -> dict:
        return {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z",
            "system": self._system(),
            "llm": self._llm(),
            "trading": self._trading(),
            "p2p": self._p2p(),
            "governance": self._governance(),
            "security": self._security(),
        }


# ────────────────────────────────────────────────
# Connection Handler
# ────────────────────────────────────────────────
class ClientConnection:
    def __init__(self, sock: socket.socket, addr: tuple):
        self.sock = sock
        self.addr = addr
        self.handshaked = False
        self.buf = bytearray()
        self.lock = threading.Lock()
        self.last_pong = time.time()
        self.closed = False

    def send(self, payload: bytes, opcode: int = 0x1):
        if self.closed:
            return
        try:
            with self.lock:
                self.sock.sendall(encode_frame(payload, opcode))
        except (OSError, BrokenPipeError):
            self.closed = True

    def close(self, code: int = 1000):
        if self.closed:
            return
        self.closed = True
        try:
            payload = struct.pack(">H", code)
            self.send(payload, opcode=0x8)
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            try:
                self.sock.close()
            except OSError:
                pass


# ────────────────────────────────────────────────
# Server Core
# ────────────────────────────────────────────────
class WebSocketServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.clients: list[ClientConnection] = []
        self.lock = threading.Lock()
        self.metrics = MetricsEngine()
        self.server_sock: socket.socket | None = None
        self._running = False

    def _handle_client(self, conn: ClientConnection):
        """Read loop for a single client."""
        try:
            while not conn.closed and self._running:
                ready, _, _ = select.select([conn.sock], [], [], 1.0)
                if not ready:
                    continue
                chunk = conn.sock.recv(4096)
                if not chunk:
                    break
                conn.buf.extend(chunk)

                if not conn.handshaked:
                    # Try HTTP upgrade
                    if b"\r\n\r\n" in conn.buf:
                        header = conn.buf[:conn.buf.index(b"\r\n\r\n") + 4].decode("utf-8", "replace")
                        del conn.buf[:conn.buf.index(b"\r\n\r\n") + 4]
                        key = None
                        for line in header.split("\r\n"):
                            if line.lower().startswith("sec-websocket-key:"):
                                key = line.split(":", 1)[1].strip()
                                break
                        if key:
                            conn.sock.sendall(make_handshake_response(key))
                            conn.handshaked = True
                            print(f"[WS] Handshake OK from {conn.addr}")
                        else:
                            conn.sock.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                            break
                    continue

                # Decode frames
                while True:
                    opcode, payload, consumed = decode_frame(conn.buf)
                    if opcode is None:
                        break
                    if opcode == 0x8:
                        code = 1000
                        if len(payload) >= 2:
                            code = struct.unpack(">H", payload[:2])[0]
                        print(f"[WS] Close frame from {conn.addr} code={code}")
                        conn.closed = True
                        break
                    elif opcode == 0x9:
                        # Ping → Pong
                        conn.send(payload, opcode=0xA)
                    elif opcode == 0xA:
                        conn.last_pong = time.time()
                    elif opcode in (0x1, 0x2):
                        # Text / Binary — ignore for broadcast-only server
                        pass
        except Exception as e:
            print(f"[WS] Client error {conn.addr}: {e}")
        finally:
            self._remove_client(conn)
            conn.close()

    def _remove_client(self, conn: ClientConnection):
        with self.lock:
            if conn in self.clients:
                self.clients.remove(conn)
                print(f"[WS] Disconnected {conn.addr} — clients={len(self.clients)}")

    def _accept_loop(self):
        """Accept new TCP connections."""
        while self._running:
            try:
                ready, _, _ = select.select([self.server_sock], [], [], 1.0)
                if not ready:
                    continue
                sock, addr = self.server_sock.accept()
                sock.settimeout(60)
                conn = ClientConnection(sock, addr)
                with self.lock:
                    self.clients.append(conn)
                print(f"[WS] Connected {addr} — clients={len(self.clients)}")
                t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
                t.start()
            except OSError:
                break

    def _broadcast_loop(self):
        """Push metrics to all clients every BROADCAST_INTERVAL seconds."""
        while self._running:
            time.sleep(BROADCAST_INTERVAL)
            if not self._running:
                break
            snapshot = self.metrics.snapshot()
            payload = json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
            dead = []
            with self.lock:
                clients = list(self.clients)
            for c in clients:
                if c.closed or not c.handshaked:
                    dead.append(c)
                    continue
                c.send(payload)
            for c in dead:
                self._remove_client(c)
                c.close()

    def _heartbeat_loop(self):
        """Send ping frames to keep connections alive."""
        while self._running:
            time.sleep(HEARTBEAT_INTERVAL)
            if not self._running:
                break
            ping_data = str(int(time.time())).encode()
            with self.lock:
                clients = list(self.clients)
            for c in clients:
                if c.closed:
                    continue
                # Check staleness
                if time.time() - c.last_pong > HEARTBEAT_INTERVAL * 2.5:
                    print(f"[WS] Stale client {c.addr}, closing")
                    c.closed = True
                    continue
                c.send(ping_data, opcode=0x9)

    def start(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(128)
        self._running = True
        print(f"[WS] Server listening on ws://{self.host}:{self.port}")
        print(f"[WS] Broadcast every {BROADCAST_INTERVAL}s | Heartbeat every {HEARTBEAT_INTERVAL}s")

        threads = [
            threading.Thread(target=self._accept_loop, daemon=True),
            threading.Thread(target=self._broadcast_loop, daemon=True),
            threading.Thread(target=self._heartbeat_loop, daemon=True),
        ]
        for t in threads:
            t.start()

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[WS] Shutdown signal received")
        finally:
            self.stop()

    def stop(self):
        self._running = False
        with self.lock:
            clients = list(self.clients)
        for c in clients:
            c.close()
        if self.server_sock:
            self.server_sock.close()
        print("[WS] Server stopped")


# ────────────────────────────────────────────────
# Entrypoint
# ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("MAGNATRIX-OS WebSocket Metrics Server")
    print("Pure Python stdlib — no dependencies")
    print("=" * 50)
    srv = WebSocketServer(HOST, PORT)
    srv.start()
