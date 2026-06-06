#!/usr/bin/env python3
"""
Message Queue Router for MAGNATRIX-OS
Message queuing, priority routing, broadcast forwarding, and
collected response aggregation. Supports fan-out, fan-in, and
ordered delivery guarantees. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class MessagePriority(enum.IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class DeliveryMode(enum.Enum):
    SINGLE = "single"       # One target
    BROADCAST = "broadcast" # All targets
    MULTICAST = "multicast" # Subset of targets
    FAN_OUT = "fan_out"     # Parallel processing, gather results


@dataclasses.dataclass
class Message:
    msg_id: str
    payload: str
    sender: str
    targets: List[str]
    delivery_mode: DeliveryMode
    priority: MessagePriority
    timestamp: float
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    delivered_to: Set[str] = dataclasses.field(default_factory=set)
    responses: Dict[str, str] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "sender": self.sender,
            "targets": self.targets,
            "mode": self.delivery_mode.value,
            "priority": self.priority.value,
            "delivered": len(self.delivered_to),
            "responses": len(self.responses),
        }


class MessageQueueRouter:
    """Priority message queue with routing, forwarding, and response aggregation."""

    def __init__(self, max_queue_size: int = 10000) -> None:
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)
        self._handlers: Dict[str, Callable[[Message], str]] = {}
        self._default_handler: Optional[Callable[[Message], str]] = None
        self._workers: List[threading.Thread] = []
        self._running = False
        self._lock = threading.Lock()
        self._delivered: List[Message] = []
        self._worker_count = 4
        self._msg_counter = 0

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_handler(self, target_id: str, handler: Callable[[Message], str]) -> None:
        self._handlers[target_id] = handler

    def set_default_handler(self, handler: Callable[[Message], str]) -> None:
        self._default_handler = handler

    # ------------------------------------------------------------------
    # Message submission
    # ------------------------------------------------------------------

    def submit(
        self,
        payload: str,
        sender: str = "user",
        targets: Optional[List[str]] = None,
        delivery_mode: DeliveryMode = DeliveryMode.SINGLE,
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._msg_counter += 1
        msg_id = f"msg_{int(time.time() * 1000)}_{self._msg_counter}"
        msg = Message(
            msg_id=msg_id,
            payload=payload,
            sender=sender,
            targets=targets or ["default"],
            delivery_mode=delivery_mode,
            priority=priority,
            timestamp=time.time(),
            expires_at=time.time() + ttl_seconds if ttl_seconds else None,
            metadata=metadata or {},
        )
        try:
            self._queue.put((priority.value, msg.timestamp, msg), timeout=1.0)
        except queue.Full:
            raise RuntimeError("Message queue is full")
        return msg_id

    def broadcast(self, payload: str, sender: str = "user", targets: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.submit(payload, sender, targets, DeliveryMode.BROADCAST, MessagePriority.NORMAL, metadata=metadata)

    def fan_out(self, payload: str, targets: List[str], sender: str = "user", metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.submit(payload, sender, targets, DeliveryMode.FAN_OUT, MessagePriority.HIGH, metadata=metadata)

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    def start(self, workers: int = 4) -> None:
        self._running = True
        self._worker_count = workers
        for i in range(workers):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f"MQWorker-{i}")
            t.start()
            self._workers.append(t)

    def stop(self) -> None:
        self._running = False
        for _ in self._workers:
            try:
                self._queue.put((99, 0, None), timeout=1.0)
            except queue.Full:
                pass

    def _worker_loop(self) -> None:
        while self._running:
            try:
                _, _, msg = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if msg is None:
                break
            self._process_message(msg)

    def _process_message(self, msg: Message) -> None:
        # Check expiry
        if msg.expires_at and time.time() > msg.expires_at:
            return
        # Determine targets
        targets: List[str] = []
        if msg.delivery_mode == DeliveryMode.BROADCAST:
            targets = list(self._handlers.keys())
        elif msg.delivery_mode == DeliveryMode.SINGLE:
            targets = [msg.targets[0]] if msg.targets else ["default"]
        elif msg.delivery_mode == DeliveryMode.MULTICAST:
            targets = [t for t in msg.targets if t in self._handlers]
        elif msg.delivery_mode == DeliveryMode.FAN_OUT:
            targets = [t for t in msg.targets if t in self._handlers]

        # Deliver to each target
        for target in targets:
            handler = self._handlers.get(target)
            if not handler:
                handler = self._default_handler
            if not handler:
                continue
            try:
                resp = handler(msg)
                msg.delivered_to.add(target)
                msg.responses[target] = resp
            except Exception as e:
                msg.responses[target] = f"[ERROR: {e}]"

        with self._lock:
            self._delivered.append(msg)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_message(self, msg_id: str) -> Optional[Message]:
        for msg in self._delivered:
            if msg.msg_id == msg_id:
                return msg
        return None

    def get_response(self, msg_id: str, target: Optional[str] = None) -> Optional[str]:
        msg = self.get_message(msg_id)
        if not msg:
            return None
        if target:
            return msg.responses.get(target)
        # Return concatenated responses
        return "\n".join(f"[{k}] {v}" for k, v in msg.responses.items())

    def wait_for_responses(self, msg_id: str, timeout: float = 30.0, expected_count: Optional[int] = None) -> Optional[Message]:
        start = time.time()
        while time.time() - start < timeout:
            msg = self.get_message(msg_id)
            if msg:
                if expected_count is None or len(msg.responses) >= expected_count:
                    return msg
            time.sleep(0.1)
        return None

    def list_delivered(self, limit: int = 100) -> List[Message]:
        return self._delivered[-limit:]

    def stats(self) -> Dict[str, Any]:
        pending = self._queue.qsize()
        delivered = len(self._delivered)
        by_mode = {}
        for msg in self._delivered:
            by_mode[msg.delivery_mode.value] = by_mode.get(msg.delivery_mode.value, 0) + 1
        return {
            "pending": pending,
            "delivered": delivered,
            "handlers": len(self._handlers),
            "workers": self._worker_count,
            "by_mode": by_mode,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    router = MessageQueueRouter()

    def handler_a(msg):
        return f"Agent-A processed: {msg.payload[:30]}"
    def handler_b(msg):
        return f"Agent-B processed: {msg.payload[:30]}"
    def handler_c(msg):
        return f"Agent-C processed: {msg.payload[:30]}"

    router.register_handler("agent-a", handler_a)
    router.register_handler("agent-b", handler_b)
    router.register_handler("agent-c", handler_c)

    router.start(workers=2)
    print("=== Message Queue Router Demo ===\n")
    # Single
    mid = router.submit("Hello single", targets=["agent-a"], delivery_mode=DeliveryMode.SINGLE)
    time.sleep(0.2)
    print(f"Single: {router.get_response(mid)}")
    # Broadcast
    mid = router.broadcast("Hello all agents", targets=["agent-a", "agent-b", "agent-c"])
    time.sleep(0.2)
    print(f"\nBroadcast:\n{router.get_response(mid)}")
    # Fan-out
    mid = router.fan_out("Parallel task", targets=["agent-a", "agent-b", "agent-c"])
    msg = router.wait_for_responses(mid, timeout=2.0, expected_count=3)
    if msg:
        print(f"\nFan-out responses: {len(msg.responses)} received")
    # Stats
    print(f"\nStats: {router.stats()}")
    router.stop()


if __name__ == "__main__":
    _demo()
