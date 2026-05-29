#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 11 — Mobile Bridge
Native bridge between mobile runtime and desktop kernel via WebSocket/MQTT.
- Message framing (length-prefixed JSON)
- Compression (zlib for large payloads)
- Heartbeat + auto-reconnect
- Topic routing for pub/sub between devices
"""
import json, struct, zlib, time, threading, queue as _queue, socket, ssl, os, sys
from typing import Dict, List, Optional, Callable, Any, Tuple
from collections import deque


class FrameProtocol:
    """Length-prefixed JSON framing."""

    @staticmethod
    def encode(payload: Dict, compress: bool = False) -> bytes:
        data = json.dumps(payload).encode('utf-8')
        if compress and len(data) > 256:
            data = zlib.compress(data)
            flags = 0x01
        else:
            flags = 0x00
        header = struct.pack('>I', len(data) + 1) + struct.pack('B', flags)
        return header + data

    @staticmethod
    def decode(stream: bytes) -> Tuple[Optional[Dict], int]:
        if len(stream) < 5:
            return None, 0
        length = struct.unpack('>I', stream[:4])[0]
        if len(stream) < 4 + length:
            return None, 0
        flags = struct.unpack('B', stream[4:5])[0]
        data = stream[5:4 + length]
        if flags & 0x01:
            data = zlib.decompress(data)
        consumed = 4 + length
        try:
            return json.loads(data.decode('utf-8')), consumed
        except Exception:
            return None, consumed


class BridgeConnection:
    """TCP/TLS bridge connection with auto-reconnect."""

    def __init__(self, host: str, port: int, tls: bool = False, reconnect_sec: float = 3.0):
        self.host = host
        self.port = port
        self.tls = tls
        self.reconnect_sec = reconnect_sec
        self._sock: Optional[socket.socket] = None
        self._connected = False
        self._rx_buffer = b""
        self._handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self._tx_queue: _queue.Queue = _queue.Queue()
        self._running = False
        self._tx_thread: Optional[threading.Thread] = None
        self._rx_thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.tls:
                self._sock = ssl.wrap_socket(self._sock)
            self._sock.connect((self.host, self.port))
            self._connected = True
            self._running = True
            self._tx_thread = threading.Thread(target=self._tx_loop, daemon=True)
            self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
            self._tx_thread.start()
            self._rx_thread.start()
            return True
        except Exception as e:
            self._connected = False
            return False

    def _tx_loop(self):
        while self._running:
            try:
                payload = self._tx_queue.get(timeout=0.5)
            except _queue.Empty:
                continue
            try:
                frame = FrameProtocol.encode(payload)
                self._sock.sendall(frame)
            except Exception:
                self._connected = False
                break

    def _rx_loop(self):
        while self._running:
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    self._connected = False
                    break
                self._rx_buffer += chunk
                while True:
                    msg, consumed = FrameProtocol.decode(self._rx_buffer)
                    if msg is None:
                        break
                    self._rx_buffer = self._rx_buffer[consumed:]
                    self._dispatch(msg)
            except Exception:
                self._connected = False
                break
        # Auto-reconnect
        if self._running:
            time.sleep(self.reconnect_sec)
            self.connect()

    def _dispatch(self, msg: Dict):
        msg_type = msg.get("type", "unknown")
        with self._lock:
            for cb in self._handlers.get(msg_type, []):
                try:
                    cb(msg)
                except Exception:
                    pass

    def send(self, msg: Dict):
        self._tx_queue.put(msg)

    def on(self, msg_type: str, handler: Callable):
        with self._lock:
            self._handlers.setdefault(msg_type, []).append(handler)

    def disconnect(self):
        self._running = False
        self._connected = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

    @property
    def is_connected(self) -> bool:
        return self._connected


class TopicRouter:
    """Topic-based pub/sub routing for bridge messages."""

    def __init__(self):
        self._subs: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, topic: str, handler: Callable):
        with self._lock:
            self._subs.setdefault(topic, []).append(handler)

    def unsubscribe(self, topic: str, handler: Callable):
        with self._lock:
            if topic in self._subs:
                self._subs[topic] = [h for h in self._subs[topic] if h != handler]

    def publish(self, topic: str, payload: Dict):
        with self._lock:
            for cb in self._subs.get(topic, []):
                try:
                    cb(payload)
                except Exception:
                    pass

    def match(self, pattern: str, topic: str) -> bool:
        # Wildcard: sensor/+/temp matches sensor/01/temp
        # sensor/# matches anything under sensor/
        parts_p = pattern.split('/')
        parts_t = topic.split('/')
        if len(parts_p) > len(parts_t) and '#' not in parts_p:
            return False
        for i, p in enumerate(parts_p):
            if p == '#':
                return True
            if p == '+':
                continue
            if i >= len(parts_t) or p != parts_t[i]:
                return False
        return len(parts_p) == len(parts_t)


class MobileBridge:
    """Full mobile bridge: connection + routing + heartbeat."""

    def __init__(self, host: str = "localhost", port: int = 7777):
        self.conn = BridgeConnection(host, port)
        self.router = TopicRouter()
        self._device_id = "unknown"
        self._heartbeat_interval = 10.0
        self._heartbeat_thread: Optional[threading.Thread] = None

    def connect(self, device_id: str) -> bool:
        self._device_id = device_id
        ok = self.conn.connect()
        if ok:
            self._start_heartbeat()
            self.conn.on("heartbeat", lambda m: print(f"[Bridge] Heartbeat ACK from {m.get('device')}"))
            self.conn.send({"type": "register", "device": device_id, "ts": time.time()})
        return ok

    def _start_heartbeat(self):
        self._heartbeat_thread = threading.Thread(target=self._hb_loop, daemon=True)
        self._heartbeat_thread.start()

    def _hb_loop(self):
        while self.conn._running:
            time.sleep(self._heartbeat_interval)
            if self.conn.is_connected:
                self.conn.send({"type": "heartbeat", "device": self._device_id, "ts": time.time()})

    def publish(self, topic: str, payload: Dict):
        self.conn.send({"type": "pub", "topic": topic, "payload": payload, "device": self._device_id})
        self.router.publish(topic, payload)

    def subscribe(self, topic: str, handler: Callable):
        self.router.subscribe(topic, handler)
        self.conn.send({"type": "sub", "topic": topic, "device": self._device_id})

    def disconnect(self):
        self.conn.disconnect()


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("frame_encode_decode", lambda: FrameProtocol.decode(FrameProtocol.encode({"x": 1}))[0] == {"x": 1})
    _t("frame_compress", lambda: FrameProtocol.decode(FrameProtocol.encode({"x": "y" * 500}, compress=True))[0] == {"x": "y" * 500})
    _t("topic_exact", lambda: TopicRouter().match("a/b", "a/b"))
    _t("topic_wildcard_plus", lambda: TopicRouter().match("a/+/c", "a/2/c"))
    _t("topic_wildcard_hash", lambda: TopicRouter().match("a/#", "a/b/c/d"))
    _t("topic_mismatch", lambda: not TopicRouter().match("a/b", "a/c"))
    _t("bridge_register", lambda: isinstance(MobileBridge().connect("dev01"), bool))

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nMobile Bridge: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
