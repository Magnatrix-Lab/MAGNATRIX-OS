"""WebSocket Message Queue — In-memory queue, priority, TTL, dead letter."""
from dataclasses import dataclass
from pathlib import Path
import json, time, heapq

@dataclass
class QueuedMessage:
    msg_id: str = ""
    topic: str = ""
    payload: str = ""
    priority: int = 0  # lower = higher priority
    ttl: float = 0.0
    enqueued_at: float = 0.0

class WebSocketMessageQueue:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._queue: list[tuple[int, float, QueuedMessage]] = []
        self._dead_letter: list[QueuedMessage] = []
        self._delivered: list[str] = []
        self._persist_path = self.root / "websocket_queue.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._queue = [(q.get("priority", 0), q.get("enqueued_at", 0.0), QueuedMessage(**q.get("msg", {}))) for q in data.get("queue", [])]
            self._dead_letter = [QueuedMessage(**m) for m in data.get("dead_letter", [])]
            self._delivered = data.get("delivered", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "queue": [{"priority": q[0], "enqueued_at": q[1], "msg": q[2].__dict__} for q in self._queue],
            "dead_letter": [m.__dict__ for m in self._dead_letter],
            "delivered": self._delivered
        }, indent=2))

    def enqueue(self, msg_id: str, topic: str, payload: str, priority: int = 0, ttl: float = 60.0) -> QueuedMessage:
        msg = QueuedMessage(msg_id=msg_id, topic=topic, payload=payload, priority=priority, ttl=ttl, enqueued_at=time.time())
        heapq.heappush(self._queue, (priority, msg.enqueued_at, msg))
        self._save()
        return msg

    def dequeue(self, topic: str | None = None) -> QueuedMessage | None:
        self._expire()
        for i, (prio, ts, msg) in enumerate(self._queue):
            if topic is None or msg.topic == topic:
                self._queue.pop(i)
                self._delivered.append(msg.msg_id)
                self._save()
                return msg
        return None

    def _expire(self) -> None:
        now = time.time()
        expired = [i for i, (prio, ts, msg) in enumerate(self._queue) if msg.ttl > 0 and (now - ts) > msg.ttl]
        for i in reversed(expired):
            self._dead_letter.append(self._queue.pop(i)[2])
        self._save()

    def peek(self, topic: str | None = None) -> QueuedMessage | None:
        for prio, ts, msg in self._queue:
            if topic is None or msg.topic == topic:
                return msg
        return None

    def to_dict(self) -> dict:
        return {"queue_size": len(self._queue), "dead_letter_size": len(self._dead_letter), "delivered": len(self._delivered)}

    def get_stats(self) -> dict:
        return {"queued": len(self._queue), "dead_letter": len(self._dead_letter), "delivered": len(self._delivered)}

__all__ = ["WebSocketMessageQueue", "QueuedMessage"]
