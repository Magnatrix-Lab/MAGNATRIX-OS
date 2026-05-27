#!/usr/bin/env python3
"""
messaging.py — MAGNATRIX Agent-to-Agent Mesh Messaging Protocol
Layer di atas P2P Mesh (Layer 4) yang memungkinkan agent-agent
swarm berkomunikasi dengan format pesan terstruktur.

Message types:
  SIGNAL     → Data/sinyal dari scout ke analyst
  ANALYSIS   → Hasil analisis dari analyst ke executor/guardian
  EXECUTE    → Perintah eksekusi dari executor
  HALT       → Veto dari guardian (freeze swarm)
  RESUME     → Resume swarm dari halt state
  RESEARCH   → Hasil research untuk knowledge graph
  CONTENT    → Output writer untuk publish
  OPS        → CI/CD status dari ops
  EVOLVE     → Request evolusi dari architect
  HEARTBEAT  → Ping dari setiap agent
"""

import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from threading import Lock


@dataclass
class MeshMessage:
    id: str
    sender: str
    target: Optional[str]
    msg_type: str
    payload: Dict[str, Any]
    timestamp: float
    ttl: int = 10  # hop limit / time-to-live
    priority: int = 5  # 1=urgent, 10=low


class MeshMessagingBus:
    """Shared message bus untuk swarm communication."""

    PRIORITY_URGENT = 1
    PRIORITY_HIGH = 3
    PRIORITY_NORMAL = 5
    PRIORITY_LOW = 10

    def __init__(self, max_queue_per_agent: int = 1000):
        self.queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_queue_per_agent))
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.history: deque = deque(maxlen=5000)
        self._global_callbacks: List[Callable] = []
        self._lock = Lock()
        self._msg_counter = 0

    def _next_id(self) -> str:
        with self._lock:
            self._msg_counter += 1
            return f"msg-{int(time.time()*1000)}-{self._msg_counter}"

    def send(self, sender: str, msg_type: str, payload: Dict[str, Any], target: Optional[str] = None, priority: int = 5, ttl: int = 10) -> MeshMessage:
        """Kirim pesan ke mesh. Jika target=None, broadcast ke semua subscriber."""
        msg = MeshMessage(
            id=self._next_id(),
            sender=sender,
            target=target,
            msg_type=msg_type,
            payload=payload,
            timestamp=time.time(),
            ttl=ttl,
            priority=priority,
        )

        with self._lock:
            self.history.append(msg)

            if target:
                # Directed message
                self.queues[target].append(msg)
                # Notify target subscribers
                for cb in self.subscribers.get(target, []):
                    try:
                        cb(msg)
                    except Exception:
                        pass
            else:
                # Broadcast — masuk ke semua queue kecuali sender
                for agent_id, queue in self.queues.items():
                    if agent_id != sender:
                        queue.append(msg)

            # Notify global subscribers
            for cb in self._global_callbacks:
                try:
                    cb(msg)
                except Exception:
                    pass

        return msg

    def recv(self, agent_id: str, max_items: int = 10, msg_type: Optional[str] = None, block: bool = False, timeout: Optional[float] = None) -> List[MeshMessage]:
        """Ambil pesan dari queue agent. Non-blocking by default."""
        if block:
            start = time.time()
            while True:
                items = self._peek_and_take(agent_id, max_items, msg_type)
                if items:
                    return items
                if timeout and (time.time() - start) > timeout:
                    return []
                time.sleep(0.1)
        else:
            return self._peek_and_take(agent_id, max_items, msg_type)

    def _peek_and_take(self, agent_id: str, max_items: int, msg_type: Optional[str]) -> List[MeshMessage]:
        with self._lock:
            queue = self.queues.get(agent_id, deque())
            taken = []
            remaining = deque(maxlen=queue.maxlen)

            for msg in queue:
                if len(taken) < max_items and (msg_type is None or msg.msg_type == msg_type):
                    taken.append(msg)
                else:
                    remaining.append(msg)

            self.queues[agent_id] = remaining
            return taken

    def subscribe(self, agent_id: str, callback: Callable) -> None:
        """Subscribe callback untuk menerima pesan real-time."""
        self.subscribers[agent_id].append(callback)

    def subscribe_global(self, callback: Callable) -> None:
        """Subscribe ke semua pesan di mesh."""
        self._global_callbacks.append(callback)

    def get_history(self, msg_type: Optional[str] = None, sender: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Ambil history pesan dengan filter."""
        results = []
        for msg in reversed(self.history):
            if msg_type and msg.msg_type != msg_type:
                continue
            if sender and msg.sender != sender:
                continue
            results.append({
                "id": msg.id,
                "sender": msg.sender,
                "target": msg.target,
                "type": msg.msg_type,
                "payload": msg.payload,
                "timestamp": msg.timestamp,
                "priority": msg.priority,
            })
            if len(results) >= limit:
                break
        return results

    def get_queue_depth(self, agent_id: Optional[str] = None) -> Dict[str, int]:
        """Cek queue depth per agent."""
        if agent_id:
            return {agent_id: len(self.queues.get(agent_id, deque()))}
        return {k: len(v) for k, v in self.queues.items()}

    def register_agent(self, agent_id: str) -> None:
        """Daftarkan agent ke mesh (create queue)."""
        with self._lock:
            if agent_id not in self.queues:
                self.queues[agent_id] = deque(maxlen=1000)

    def unregister_agent(self, agent_id: str) -> None:
        """Hapus agent dari mesh."""
        with self._lock:
            self.queues.pop(agent_id, None)
            self.subscribers.pop(agent_id, None)

    def get_status(self) -> Dict[str, Any]:
        return {
            "agents_registered": len(self.queues),
            "total_messages_history": len(self.history),
            "queue_depths": self.get_queue_depth(),
            "subscribers_count": {k: len(v) for k, v in self.subscribers.items()},
        }


# ===================================================================
# Demo
# ===================================================================
if __name__ == "__main__":
    import json

    print("=" * 60)
    print("MAGNATRIX Mesh Messaging Bus — STOA Adaptation")
    print("=" * 60)

    bus = MeshMessagingBus()

    # Register agents
    for agent in ["scout", "analyst", "executor", "guardian"]:
        bus.register_agent(agent)

    print("\n[1] Agents registered:", list(bus.queues.keys()))

    # Simulate scout sending signal
    print("\n[2] Scout sends SIGNAL:")
    bus.send(
        sender="scout",
        msg_type="SIGNAL",
        payload={"symbol": "SOL", "price": 145.2, "change_24h": 0.05, "volume_spike": True},
        priority=bus.PRIORITY_HIGH,
    )

    # Analyst reads
    msgs = bus.recv("analyst", max_items=5)
    print(f"  Analyst received {len(msgs)} message(s)")
    for m in msgs:
        print(f"    → {m.msg_type} from {m.sender}: {m.payload}")

    # Analyst sends analysis to executor
    print("\n[3] Analyst sends ANALYSIS to executor:")
    bus.send(
        sender="analyst",
        msg_type="ANALYSIS",
        payload={"symbol": "SOL", "confidence": 0.82, "thesis": "breakout confirmed"},
        target="executor",
        priority=bus.PRIORITY_URGENT,
    )

    exec_msgs = bus.recv("executor", max_items=5)
    print(f"  Executor received {len(exec_msgs)} message(s)")

    # Guardian HALT test
    print("\n[4] Guardian HALT broadcast:")
    bus.send(
        sender="guardian",
        msg_type="HALT",
        payload={"reason": "drawdown 18%", "timestamp": time.time()},
        priority=bus.PRIORITY_URGENT,
    )

    for agent in ["scout", "analyst", "executor"]:
        halt_msgs = bus.recv(agent, msg_type="HALT", max_items=5)
        if halt_msgs:
            print(f"  {agent} received HALT: {halt_msgs[0].payload['reason']}")

    # History query
    print("\n[5] History (last 3 messages):")
    history = bus.get_history(limit=3)
    for h in history:
        print(f"  [{h['type']:10s}] {h['sender']} → {h['target'] or 'ALL'}")

    print("\n[6] Bus status:")
    print(json.dumps(bus.get_status(), indent=2, default=str))

    print("\n" + "=" * 60)
    print("Mesh Messaging Bus ready.")
    print("=" * 60)
