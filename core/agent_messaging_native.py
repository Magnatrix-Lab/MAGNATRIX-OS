#!/usr/bin/env python3
"""
agent_messaging_native.py
MAGNATRIX-OS — Native Agent Messaging Bus

Pub/sub message bus with topic routing, wildcard subscriptions, broadcast channels,
and at-least-once delivery queue. Modules publish("market.alert", data) and
subscribe("market.*", callback). Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import fnmatch
import json
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class Message:
    """A message on the bus."""
    topic: str
    payload: Any
    source: str = "unknown"
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    priority: int = 0  # 0 = highest


class AgentMessagingNative:
    """
    Native pub/sub messaging bus for inter-module communication.
    Supports exact topics, wildcards (*, **), broadcast, and persistent queue.
    """

    def __init__(self, workspace: str = "./messaging") -> None:
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._subscriptions: Dict[str, List[Callable[[Message], None]]] = {}
        self._wildcard_subs: List[Tuple[str, Callable[[Message], None]]] = []
        self._broadcast_handlers: List[Callable[[Message], None]] = []
        self._delivery_queue: queue.Queue = queue.Queue()
        self._lock = threading.RLock()
        self._running = False
        self._delivery_thread: Optional[threading.Thread] = None
        self._persist_path = self.workspace / "undelivered.json"
        self._load_undelivered()

    def _load_undelivered(self) -> None:
        if self._persist_path.exists():
            try:
                with open(self._persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for msg_dict in data:
                    self._delivery_queue.put(Message(**msg_dict))
            except Exception:
                pass

    def _save_undelivered(self) -> None:
        try:
            pending = []
            while not self._delivery_queue.empty():
                msg = self._delivery_queue.get_nowait()
                pending.append(asdict(msg))
                self._delivery_queue.put(msg)  # Put it back
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(pending, f, indent=2)
        except Exception:
            pass

    def start(self) -> None:
        """Start the delivery thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._delivery_thread = threading.Thread(target=self._delivery_loop, daemon=True)
            self._delivery_thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._save_undelivered()

    def _delivery_loop(self) -> None:
        while self._running:
            try:
                msg = self._delivery_queue.get(timeout=1.0)
                self._route(msg)
                self._delivery_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                pass

    def _route(self, msg: Message) -> None:
        """Route a message to all matching subscribers."""
        delivered = False
        # Exact topic subscriptions
        if msg.topic in self._subscriptions:
            for handler in self._subscriptions[msg.topic]:
                try:
                    handler(msg)
                    delivered = True
                except Exception:
                    pass
        # Wildcard subscriptions
        for pattern, handler in self._wildcard_subs:
            if fnmatch.fnmatch(msg.topic, pattern):
                try:
                    handler(msg)
                    delivered = True
                except Exception:
                    pass
        # Broadcast handlers
        for handler in self._broadcast_handlers:
            try:
                handler(msg)
                delivered = True
            except Exception:
                pass
        return delivered

    def publish(self, topic: str, payload: Any, source: str = "unknown", priority: int = 0) -> str:
        """Publish a message to a topic."""
        msg = Message(topic=topic, payload=payload, source=source, priority=priority)
        with self._lock:
            if self._running:
                self._delivery_queue.put(msg)
            else:
                self._route(msg)
        return msg.msg_id

    def subscribe(self, topic: str, handler: Callable[[Message], None]) -> str:
        """
        Subscribe to a topic. Supports wildcards:
        - "market.alert" — exact match
        - "market.*" — any single segment
        - "market.**" — any segments (not yet: fnmatch only supports *)
        """
        with self._lock:
            sub_id = str(uuid.uuid4())[:8]
            if "*" in topic or "?" in topic:
                self._wildcard_subs.append((topic, handler))
            else:
                self._subscriptions.setdefault(topic, []).append(handler)
            return sub_id

    def unsubscribe(self, topic: str, handler: Callable[[Message], None]) -> bool:
        with self._lock:
            if topic in self._subscriptions and handler in self._subscriptions[topic]:
                self._subscriptions[topic].remove(handler)
                return True
            for i, (pat, h) in enumerate(self._wildcard_subs):
                if pat == topic and h is handler:
                    self._wildcard_subs.pop(i)
                    return True
            return False

    def broadcast(self, payload: Any, source: str = "unknown") -> str:
        """Broadcast to all listeners."""
        return self.publish("__broadcast__", payload, source)

    def add_broadcast_handler(self, handler: Callable[[Message], None]) -> str:
        with self._lock:
            self._broadcast_handlers.append(handler)
            return str(uuid.uuid4())[:8]

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "exact_topics": len(self._subscriptions),
                "wildcard_subs": len(self._wildcard_subs),
                "broadcast_handlers": len(self._broadcast_handlers),
                "queue_size": self._delivery_queue.qsize(),
            }

    def list_topics(self) -> List[str]:
        with self._lock:
            return list(self._subscriptions.keys())
