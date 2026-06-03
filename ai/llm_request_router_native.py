"""LLM Request Router — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class RequestType(Enum):
    CHAT = auto()
    COMPLETION = auto()
    EMBEDDING = auto()
    CLASSIFICATION = auto()
    SUMMARIZATION = auto()

@dataclass
class Request:
    id: str
    request_type: RequestType
    payload: Dict[str, Any]
    priority: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)

class RequestRouter:
    def __init__(self) -> None:
        self._handlers: Dict[RequestType, Callable[[Request], Any]] = {}
        self._fallback: Optional[Callable[[Request], Any]] = None

    def register(self, request_type: RequestType, handler: Callable[[Request], Any]) -> None:
        self._handlers[request_type] = handler

    def set_fallback(self, handler: Callable[[Request], Any]) -> None:
        self._fallback = handler

    def route(self, request: Request) -> Any:
        handler = self._handlers.get(request.request_type)
        if handler:
            return handler(request)
        if self._fallback:
            return self._fallback(request)
        raise ValueError("No handler for request type: " + request.request_type.name)

    def get_stats(self) -> Dict[str, Any]:
        return {"handlers": len(self._handlers), "has_fallback": self._fallback is not None}

def run() -> None:
    print("Request Router test")
    e = RequestRouter()
    e.register(RequestType.CHAT, lambda r: "Chat response for " + r.id)
    e.register(RequestType.COMPLETION, lambda r: "Completion for " + r.id)
    e.register(RequestType.EMBEDDING, lambda r: [0.1, 0.2, 0.3])
    e.set_fallback(lambda r: "Generic response for " + r.id)
    requests = [
        Request("r1", RequestType.CHAT, {"message": "Hello"}),
        Request("r2", RequestType.COMPLETION, {"prompt": "Once upon"}),
        Request("r3", RequestType.SUMMARIZATION, {"text": "Long text..."}),
    ]
    for req in requests:
        print("  " + req.id + " (" + req.request_type.name + ") -> " + str(e.route(req)))
    print("Request Router test complete.")

if __name__ == "__main__":
    run()
