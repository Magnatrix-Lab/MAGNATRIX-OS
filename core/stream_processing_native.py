#!/usr/bin/env python3
"""Stream Processing for MAGNATRIX-OS — Kafka-style real-time stream processing."""
from __future__ import annotations
import queue, threading, time
from typing import Any, Callable, Dict, List, Optional

class StreamTopic:
    def __init__(self, name: str) -> None:
        self.name = name
        self._queue: queue.Queue = queue.Queue(maxsize=10000)
        self._consumers: List[Callable] = []
        self._lock = threading.Lock()

    def publish(self, message: Any) -> None:
        self._queue.put(message)
        with self._lock:
            for consumer in self._consumers:
                try:
                    consumer(message)
                except Exception:
                    pass

    def subscribe(self, consumer: Callable) -> None:
        with self._lock:
            self._consumers.append(consumer)

    def get(self, timeout: float = 1.0) -> Optional[Any]:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

class StreamProcessor:
    def __init__(self) -> None:
        self._topics: Dict[str, StreamTopic] = {}

    def create_topic(self, name: str) -> StreamTopic:
        if name not in self._topics:
            self._topics[name] = StreamTopic(name)
        return self._topics[name]

    def publish(self, topic: str, message: Any) -> None:
        t = self._topics.get(topic) or self.create_topic(topic)
        t.publish(message)

    def subscribe(self, topic: str, consumer: Callable) -> None:
        t = self._topics.get(topic) or self.create_topic(topic)
        t.subscribe(consumer)

    def stats(self) -> Dict[str, Any]:
        return {"topics": len(self._topics), "consumers": sum(len(t._consumers) for t in self._topics.values())}
