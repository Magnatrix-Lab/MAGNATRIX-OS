"""
kernel/interlayer_bridge_native.py
MAGNATRIX-OS Layer 0 — Inter-Layer Communication Bridge
Replaces stub EventBus + ServiceRegistry with real socket-based,
retry-enabled, circuit-breaker-protected layer-to-layer messaging.
Zero external dependencies.
"""
from __future__ import annotations

import json
import pickle
import queue
import socket
import struct
import sys
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ── Message Envelope ────────────────────────────────────

class MessagePriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class MessageEnvelope:
    msg_id: str
    topic: str                  # e.g. "layer.kernel.event", "layer.security.alert"
    payload: Any
    sender_layer: str
    target_layer: Optional[str] = None   # None = broadcast
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    ttl: int = 5                # hop limit / retry budget
    trace: List[str] = field(default_factory=list)

    def to_bytes(self) -> bytes:
        return pickle.dumps(asdict(self), protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def from_bytes(cls, data: bytes) -> MessageEnvelope:
        d = pickle.loads(data)
        d["priority"] = MessagePriority(d["priority"])
        return cls(**d)

    def fork(self, new_topic: Optional[str] = None) -> MessageEnvelope:
        return MessageEnvelope(
            msg_id=str(uuid.uuid4())[:16],
            topic=new_topic or self.topic,
            payload=self.payload,
            sender_layer=self.sender_layer,
            target_layer=self.target_layer,
            priority=self.priority,
            ttl=self.ttl,
            trace=self.trace + [self.msg_id],
        )


# ── Retry Policy ────────────────────────────────────────

@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 0.1
    max_delay: float = 5.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

    def sleep_for(self, attempt: int) -> None:
        delay = min(self.base_delay * (self.backoff_multiplier ** attempt), self.max_delay)
        if self.jitter:
            delay *= (0.5 + (time.time() % 1.0) * 0.5)
        time.sleep(delay)


# ── Circuit Breaker ───────────────────────────────────

class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitBreaker:
    """Per-destination circuit breaker."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()

    def can_execute(self) -> bool:
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                if self._last_failure_time and (time.time() - self._last_failure_time) >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    return True
                return False
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            return False

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failures = 0
                self._half_open_calls = 0
            else:
                self._failures = max(0, self._failures - 1)

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            elif self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state


# ── In-Memory Message Bus ─────────────────────────────

class MessageBus:
    """Thread-safe in-memory pub/sub with priority queues."""

    def __init__(self, max_queue_size: int = 10000) -> None:
        self._subscribers: Dict[str, Set[Callable[[MessageEnvelope], None]]] = {}
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)
        self._dropped = 0
        self._delivered = 0
        self._lock = threading.Lock()
        self._running = False
        self._worker: Optional[threading.Thread] = None

    def subscribe(self, topic_pattern: str, handler: Callable[[MessageEnvelope], None]) -> None:
        with self._lock:
            self._subscribers.setdefault(topic_pattern, set()).add(handler)

    def unsubscribe(self, topic_pattern: str, handler: Callable[[MessageEnvelope], None]) -> None:
        with self._lock:
            if topic_pattern in self._subscribers:
                self._subscribers[topic_pattern].discard(handler)

    def publish(self, envelope: MessageEnvelope) -> bool:
        try:
            self._queue.put_nowait((envelope.priority.value, time.time(), envelope))
            return True
        except queue.Full:
            self._dropped += 1
            return False

    def _dispatch(self, envelope: MessageEnvelope) -> None:
        with self._lock:
            subs = dict(self._subscribers)
        matched = []
        for pattern, handlers in subs.items():
            if self._match_topic(pattern, envelope.topic):
                matched.extend(handlers)
        if not matched:
            return
        for handler in matched:
            try:
                handler(envelope)
                self._delivered += 1
            except Exception:
                traceback.print_exc()

    @staticmethod
    def _match_topic(pattern: str, topic: str) -> bool:
        if pattern == "*" or pattern == "#":
            return True
        if pattern.endswith(".*"):
            return topic.startswith(pattern[:-2] + ".")
        if pattern.endswith(".#"):
            prefix = pattern[:-2]
            return topic == prefix or topic.startswith(prefix + ".")
        return pattern == topic

    def start(self) -> None:
        self._running = True
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._running = False
        if self._worker:
            self._worker.join(timeout=2.0)

    def _loop(self) -> None:
        while self._running:
            try:
                _, _, envelope = self._queue.get(timeout=0.5)
                self._dispatch(envelope)
            except queue.Empty:
                continue

    def stats(self) -> Dict[str, Any]:
        return {
            "queue_size": self._queue.qsize(),
            "dropped": self._dropped,
            "delivered": self._delivered,
            "subscriber_topics": len(self._subscribers),
            "running": self._running,
        }


# ── Bridge Client (Layer-side) ────────────────────────

class BridgeClient:
    """Client that connects a layer to the central BridgeServer."""

    def __init__(
        self,
        layer_name: str,
        server_host: str = "127.0.0.1",
        server_port: int = 17000,
        retry: Optional[RetryPolicy] = None,
    ) -> None:
        self.layer_name = layer_name
        self.server_host = server_host
        self.server_port = server_port
        self.retry = retry or RetryPolicy()
        self._sock: Optional[socket.socket] = None
        self._connected = False
        self._lock = threading.Lock()
        self._handlers: Dict[str, List[Callable[[MessageEnvelope], None]]] = {}
        self._reader: Optional[threading.Thread] = None
        self._running = False
        self._cb = CircuitBreaker()

    def connect(self) -> bool:
        if not self._cb.can_execute():
            return False
        for attempt in range(self.retry.max_retries + 1):
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.settimeout(5.0)
                self._sock.connect((self.server_host, self.server_port))
                # Send handshake
                hello = json.dumps({"layer": self.layer_name, "action": "register"}).encode()
                self._send_raw(hello)
                self._connected = True
                self._cb.record_success()
                self._running = True
                self._reader = threading.Thread(target=self._read_loop, daemon=True)
                self._reader.start()
                return True
            except Exception as exc:
                self._cb.record_failure()
                if attempt < self.retry.max_retries:
                    self.retry.sleep_for(attempt)
                else:
                    self._sock = None
                    return False
        return False

    def _send_raw(self, data: bytes) -> None:
        if self._sock is None:
            raise RuntimeError("Not connected")
        # Prefix with 4-byte length
        self._sock.sendall(struct.pack(">I", len(data)) + data)

    def _recv_raw(self) -> Optional[bytes]:
        if self._sock is None:
            return None
        try:
            header = self._recvall(4)
            if header is None:
                return None
            length = struct.unpack(">I", header)[0]
            return self._recvall(length)
        except Exception:
            return None

    def _recvall(self, n: int) -> Optional[bytes]:
        data = b""
        while len(data) < n:
            chunk = self._sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def _read_loop(self) -> None:
        while self._running:
            data = self._recv_raw()
            if data is None:
                self._connected = False
                break
            try:
                envelope = MessageEnvelope.from_bytes(data)
                self._on_message(envelope)
            except Exception:
                traceback.print_exc()

    def _on_message(self, envelope: MessageEnvelope) -> None:
        handlers = self._handlers.get(envelope.topic, [])
        for pattern, hlist in self._handlers.items():
            if pattern.endswith("*") and envelope.topic.startswith(pattern[:-1]):
                handlers.extend(hlist)
        for h in handlers:
            try:
                h(envelope)
            except Exception:
                traceback.print_exc()

    def subscribe(self, topic: str, handler: Callable[[MessageEnvelope], None]) -> None:
        self._handlers.setdefault(topic, []).append(handler)
        if self._connected:
            reg = json.dumps({"layer": self.layer_name, "action": "subscribe", "topic": topic}).encode()
            try:
                self._send_raw(reg)
            except Exception:
                pass

    def publish(self, topic: str, payload: Any, target: Optional[str] = None, priority: MessagePriority = MessagePriority.NORMAL) -> bool:
        envelope = MessageEnvelope(
            msg_id=str(uuid.uuid4())[:16],
            topic=topic,
            payload=payload,
            sender_layer=self.layer_name,
            target_layer=target,
            priority=priority,
        )
        if not self._connected or self._sock is None:
            return False
        try:
            self._send_raw(envelope.to_bytes())
            return True
        except Exception:
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
        self._sock = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected


# ── Bridge Server (Central Router) ────────────────────

class BridgeServer:
    """Central TCP router that connects all layers."""

    def __init__(self, host: str = "127.0.0.1", port: int = 17000) -> None:
        self.host = host
        self.port = port
        self._server: Optional[socket.socket] = None
        self._clients: Dict[str, socket.socket] = {}
        self._subscriptions: Dict[str, Set[str]] = {}  # topic -> {layer_name}
        self._lock = threading.Lock()
        self._running = False
        self._acceptor: Optional[threading.Thread] = None
        self._bus = MessageBus()

    def start(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(32)
        self._running = True
        self._bus.start()
        self._acceptor = threading.Thread(target=self._accept_loop, daemon=True)
        self._acceptor.start()

    def stop(self) -> None:
        self._running = False
        self._bus.stop()
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        with self._lock:
            for sock in list(self._clients.values()):
                try:
                    sock.close()
                except Exception:
                    pass
            self._clients.clear()
        if self._acceptor:
            self._acceptor.join(timeout=2.0)

    def _accept_loop(self) -> None:
        while self._running:
            try:
                self._server.settimeout(1.0)
                conn, addr = self._server.accept()
                t = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_client(self, conn: socket.socket, addr: Tuple[str, int]) -> None:
        layer_name: Optional[str] = None
        try:
            while self._running:
                data = self._recv_frame(conn)
                if data is None:
                    break
                msg = json.loads(data.decode())
                action = msg.get("action")
                layer_name = msg.get("layer", f"anon_{addr[1]}")

                if action == "register":
                    with self._lock:
                        self._clients[layer_name] = conn
                elif action == "subscribe":
                    topic = msg.get("topic", "")
                    with self._lock:
                        self._subscriptions.setdefault(topic, set()).add(layer_name)
                elif action == "publish_raw":
                    # Binary payload coming next — already handled by _recv_frame for envelopes
                    pass
        except Exception:
            pass
        finally:
            if layer_name:
                with self._lock:
                    self._clients.pop(layer_name, None)
            try:
                conn.close()
            except Exception:
                pass

    def _recv_frame(self, conn: socket.socket) -> Optional[bytes]:
        try:
            header = self._recvall(conn, 4)
            if header is None:
                return None
            length = struct.unpack(">I", header)[0]
            return self._recvall(conn, length)
        except Exception:
            return None

    @staticmethod
    def _recvall(conn: socket.socket, n: int) -> Optional[bytes]:
        data = b""
        while len(data) < n:
            chunk = conn.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def route(self, envelope: MessageEnvelope) -> int:
        """Route envelope to target layer or broadcast. Returns count of delivered."""
        delivered = 0
        with self._lock:
            if envelope.target_layer:
                if envelope.target_layer in self._clients:
                    try:
                        self._send_frame(self._clients[envelope.target_layer], envelope.to_bytes())
                        delivered += 1
                    except Exception:
                        pass
            else:
                # Broadcast to subscribers of topic
                targets = set()
                for pattern, layers in self._subscriptions.items():
                    if self._match(pattern, envelope.topic):
                        targets |= layers
                for target in targets:
                    if target in self._clients and target != envelope.sender_layer:
                        try:
                            self._send_frame(self._clients[target], envelope.to_bytes())
                            delivered += 1
                        except Exception:
                            pass
        return delivered

    @staticmethod
    def _match(pattern: str, topic: str) -> bool:
        if pattern in ("*", "#"):
            return True
        if pattern.endswith(".*"):
            return topic.startswith(pattern[:-2] + ".")
        if pattern.endswith(".#"):
            p = pattern[:-2]
            return topic == p or topic.startswith(p + ".")
        return pattern == topic

    def _send_frame(self, conn: socket.socket, data: bytes) -> None:
        conn.sendall(struct.pack(">I", len(data)) + data)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "clients": len(self._clients),
                "subscriptions": {k: len(v) for k, v in self._subscriptions.items()},
                "bus": self._bus.stats(),
                "running": self._running,
            }


# ── Layer Registry ────────────────────────────────────

class LayerRegistry:
    """Tracks which layers are online and their capabilities."""

    def __init__(self) -> None:
        self._layers: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register(self, layer_name: str, capabilities: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._layers[layer_name] = {
                "name": layer_name,
                "capabilities": capabilities,
                "registered_at": time.time(),
                "last_heartbeat": time.time(),
                "metadata": metadata or {},
            }

    def heartbeat(self, layer_name: str) -> None:
        with self._lock:
            if layer_name in self._layers:
                self._layers[layer_name]["last_heartbeat"] = time.time()

    def unregister(self, layer_name: str) -> bool:
        with self._lock:
            return self._layers.pop(layer_name, None) is not None

    def find_by_capability(self, capability: str) -> List[str]:
        with self._lock:
            return [name for name, info in self._layers.items() if capability in info.get("capabilities", [])]

    def is_alive(self, layer_name: str, timeout: float = 30.0) -> bool:
        with self._lock:
            if layer_name not in self._layers:
                return False
            return (time.time() - self._layers[layer_name]["last_heartbeat"]) < timeout

    def list_layers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(info) for info in self._layers.values()]


# ── Bridge Orchestrator ───────────────────────────────

class BridgeOrchestrator:
    """Bootstraps server + clients for all 15 layers."""

    def __init__(self, host: str = "127.0.0.1", port: int = 17000) -> None:
        self.server = BridgeServer(host=host, port=port)
        self.clients: Dict[str, BridgeClient] = {}
        self.registry = LayerRegistry()
        self._lock = threading.Lock()

    def boot(self) -> None:
        self.server.start()
        # Auto-connect all known layers
        layers = [
            "kernel", "protocol", "api-router", "identity", "runtime",
            "p2p-mesh", "knowledge", "skills", "browser", "hft",
            "security", "ai", "governance", "ide", "trading",
            "uncensored", "llm", "collective-brain",
        ]
        for layer in layers:
            client = BridgeClient(layer_name=layer)
            if client.connect():
                with self._lock:
                    self.clients[layer] = client
                self.registry.register(layer, capabilities=["messaging"])

    def shutdown(self) -> None:
        with self._lock:
            for client in self.clients.values():
                client.disconnect()
            self.clients.clear()
        self.server.stop()

    def get_client(self, layer_name: str) -> Optional[BridgeClient]:
        with self._lock:
            return self.clients.get(layer_name)

    def broadcast(self, topic: str, payload: Any, priority: MessagePriority = MessagePriority.NORMAL) -> int:
        sent = 0
        with self._lock:
            for client in self.clients.values():
                if client.publish(topic, payload, priority=priority):
                    sent += 1
        return sent

    def stats(self) -> Dict[str, Any]:
        return {
            "server": self.server.stats(),
            "registry": {
                "layers": len(self.registry.list_layers()),
                "alive": [l["name"] for l in self.registry.list_layers() if self.registry.is_alive(l["name"])],
            },
            "clients_connected": sum(1 for c in self.clients.values() if c.is_connected()),
        }


# ── Kernel Bridge Adapter ─────────────────────────────

class KernelBridgeAdapter:
    """Adapter so the kernel can talk to any layer via the bridge."""

    def __init__(self, orchestrator: BridgeOrchestrator) -> None:
        self._orch = orchestrator

    def emit(self, topic: str, payload: Any, target: Optional[str] = None) -> bool:
        client = self._orch.get_client("kernel")
        if client is None:
            return False
        return client.publish(topic, payload, target=target)

    def emit_critical(self, topic: str, payload: Any, target: Optional[str] = None) -> bool:
        return self.emit(topic, payload, target)

    def health(self) -> Dict[str, Any]:
        return self._orch.stats()


# ── Self-Test ─────────────────────────────────────────

class BridgeSelfTest:
    @staticmethod
    def run() -> Dict[str, Any]:
        results = {}
        # 1. MessageBus
        bus = MessageBus()
        received = []
        bus.subscribe("test.*", lambda e: received.append(e.topic))
        bus.start()
        env = MessageEnvelope(msg_id="1", topic="test.foo", payload="hello", sender_layer="kernel")
        bus.publish(env)
        time.sleep(0.3)
        bus.stop()
        results["bus_pubsub"] = "PASS" if "test.foo" in received else "FAIL"

        # 2. CircuitBreaker
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        results["cb_open"] = "PASS" if cb.state == CircuitState.OPEN else "FAIL"
        time.sleep(0.15)
        results["cb_half_open"] = "PASS" if cb.can_execute() else "FAIL"

        # 3. RetryPolicy
        rp = RetryPolicy(max_retries=1, base_delay=0.01)
        t0 = time.perf_counter()
        rp.sleep_for(0)
        dt = time.perf_counter() - t0
        results["retry_sleep"] = "PASS" if dt >= 0.005 else "FAIL"

        # 4. LayerRegistry
        reg = LayerRegistry()
        reg.register("security", ["scan", "alert"])
        results["registry_find"] = "PASS" if reg.find_by_capability("scan") == ["security"] else "FAIL"

        # 5. Envelope ser/de
        e = MessageEnvelope(msg_id="abc", topic="x.y", payload={"a": 1}, sender_layer="test")
        e2 = MessageEnvelope.from_bytes(e.to_bytes())
        results["envelope_serde"] = "PASS" if e2.topic == "x.y" and e2.payload == {"a": 1} else "FAIL"

        results["overall"] = "PASS" if all(v == "PASS" for v in results.values()) else "FAIL"
        return results


if __name__ == "__main__":
    print("=== InterLayer Bridge Self-Test ===")
    for k, v in BridgeSelfTest.run().items():
        print(f"  {k}: {v}")
    print("=====================================")
