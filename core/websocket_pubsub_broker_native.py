"""WebSocket Pub/Sub Broker — Topic routing, message dispatch."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class PubSubMessage:
    topic: str = ""
    payload: str = ""
    timestamp: float = 0.0
    msg_id: str = ""
    qos: int = 0  # 0 = at most once, 1 = at least once

@dataclass
class Subscription:
    conn_id: str = ""
    topic: str = ""
    qos: int = 0

class WebSocketPubSubBroker:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._subscriptions: list[Subscription] = []
        self._messages: list[PubSubMessage] = []
        self._topics: set[str] = set()
        self._persist_path = self.root / "websocket_pubsub.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._subscriptions = [Subscription(**s) for s in data.get("subscriptions", [])]
            self._messages = [PubSubMessage(**m) for m in data.get("messages", [])]
            self._topics = set(data.get("topics", []))

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "subscriptions": [s.__dict__ for s in self._subscriptions],
            "messages": [m.__dict__ for m in self._messages],
            "topics": list(self._topics)
        }, indent=2))

    def subscribe(self, conn_id: str, topic: str, qos: int = 0) -> Subscription:
        sub = Subscription(conn_id=conn_id, topic=topic, qos=qos)
        self._subscriptions.append(sub)
        self._topics.add(topic)
        self._save()
        return sub

    def unsubscribe(self, conn_id: str, topic: str) -> bool:
        for i, sub in enumerate(self._subscriptions):
            if sub.conn_id == conn_id and sub.topic == topic:
                self._subscriptions.pop(i)
                self._save()
                return True
        return False

    def publish(self, topic: str, payload: str, qos: int = 0) -> list[str]:
        msg = PubSubMessage(topic=topic, payload=payload, timestamp=time.time(), msg_id=f"msg_{len(self._messages)}", qos=qos)
        self._messages.append(msg)
        self._topics.add(topic)
        # Dispatch to subscribers
        recipients = [s.conn_id for s in self._subscriptions if s.topic == topic or s.topic == "#"]
        self._save()
        return recipients

    def get_subscribers(self, topic: str) -> list[str]:
        return [s.conn_id for s in self._subscriptions if s.topic == topic or s.topic == "#"]

    def list_topics(self) -> list[str]:
        return list(self._topics)

    def to_dict(self) -> dict:
        return {"subscription_count": len(self._subscriptions), "message_count": len(self._messages), "topic_count": len(self._topics)}

    def get_stats(self) -> dict:
        by_topic = {}
        for s in self._subscriptions:
            by_topic[s.topic] = by_topic.get(s.topic, 0) + 1
        return {"subscriptions": len(self._subscriptions), "messages": len(self._messages), "topics": len(self._topics), "by_topic": by_topic}

__all__ = ["WebSocketPubSubBroker", "PubSubMessage", "Subscription"]
