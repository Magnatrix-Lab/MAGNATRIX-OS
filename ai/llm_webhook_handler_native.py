"""LLM Webhook Handler — Native Python (stdlib only)."""
from __future__ import annotations
import hashlib, hmac, json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class WebhookEventType(Enum):
    PUSH = auto()
    PULL_REQUEST = auto()
    ISSUE = auto()
    DEPLOYMENT = auto()
    CUSTOM = auto()

@dataclass
class WebhookPayload:
    id: str
    event_type: WebhookEventType
    payload: Dict[str, Any]
    signature: Optional[str] = None
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class WebhookHandler:
    def __init__(self, secret: Optional[str] = None) -> None:
        self._secret = secret
        self._handlers: Dict[WebhookEventType, List[Callable[[WebhookPayload], None]]] = {}
        self._history: List[WebhookPayload] = []

    def on(self, event_type: WebhookEventType, handler: Callable[[WebhookPayload], None]) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def verify_signature(self, payload: WebhookPayload) -> bool:
        if not self._secret or not payload.signature:
            return True
        expected = hmac.new(self._secret.encode(), json.dumps(payload.payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, payload.signature)

    def process(self, payload: WebhookPayload) -> bool:
        if not self.verify_signature(payload):
            return False
        self._history.append(payload)
        handlers = self._handlers.get(payload.event_type, [])
        for handler in handlers:
            handler(payload)
        return True

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for p in self._history:
            counts[p.event_type.name] = counts.get(p.event_type.name, 0) + 1
        return {"total": len(self._history), "by_type": counts, "handlers": sum(len(h) for h in self._handlers.values())}

def run() -> None:
    print("Webhook Handler test")
    e = WebhookHandler(secret="mysecret")
    e.on(WebhookEventType.PUSH, lambda p: print("  Push received: " + p.id))
    e.on(WebhookEventType.ISSUE, lambda p: print("  Issue received: " + p.id))
    payload = WebhookPayload("w1", WebhookEventType.PUSH, {"ref": "main", "commits": 3})
    e.process(payload)
    print("  Stats: " + str(e.get_stats()))
    print("Webhook Handler test complete.")

if __name__ == "__main__":
    run()
