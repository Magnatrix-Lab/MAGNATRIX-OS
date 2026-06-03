#!/usr/bin/env python3
"""
MAGNATRIX-OS — Real-Time Streaming Engine
ai/llm_realtime_streaming_native.py

Features:
- Token-by-token streaming simulation
- Server-Sent Event (SSE) format generation
- Connection management (client tracking, heartbeat)
- Streaming buffer with flush control
- Backpressure handling (slow consumer detection)
- Stream aggregation and final assembly

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("streaming")


class StreamStatus(enum.Enum):
    IDLE = "idle"
    STREAMING = "streaming"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class TokenChunk:
    index: int
    text: str
    timestamp: float
    is_final: bool = False


@dataclass
class StreamConnection:
    client_id: str
    status: StreamStatus
    buffer: Deque[TokenChunk] = field(default_factory=lambda: deque(maxlen=1000))
    created_at: float = 0.0
    last_activity: float = 0.0
    total_tokens: int = 0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.monotonic()
            self.last_activity = self.created_at


class StreamingEngine:
    """Real-time token streaming engine."""

    def __init__(self, max_connections: int = 100, chunk_size: int = 1):
        self.max_connections = max_connections
        self.chunk_size = chunk_size
        self._connections: Dict[str, StreamConnection] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def connect(self, client_id: Optional[str] = None) -> str:
        cid = client_id or f"client-{self._counter}"
        self._counter += 1
        with self._lock:
            if len(self._connections) >= self.max_connections:
                # Evict oldest idle connection
                oldest = min(self._connections.values(), key=lambda c: c.last_activity)
                del self._connections[oldest.client_id]
            self._connections[cid] = StreamConnection(client_id=cid, status=StreamStatus.IDLE)
        return cid

    def disconnect(self, client_id: str) -> bool:
        with self._lock:
            if client_id in self._connections:
                del self._connections[client_id]
                return True
            return False

    def push_chunk(self, client_id: str, text: str, is_final: bool = False) -> bool:
        with self._lock:
            conn = self._connections.get(client_id)
            if not conn:
                return False
            chunk = TokenChunk(index=conn.total_tokens, text=text, timestamp=time.monotonic(), is_final=is_final)
            conn.buffer.append(chunk)
            conn.total_tokens += 1
            conn.last_activity = time.monotonic()
            conn.status = StreamStatus.STREAMING if not is_final else StreamStatus.COMPLETED
            return True

    def pull_chunks(self, client_id: str, max_chunks: int = 10) -> List[TokenChunk]:
        with self._lock:
            conn = self._connections.get(client_id)
            if not conn:
                return []
            chunks = []
            for _ in range(min(max_chunks, len(conn.buffer))):
                chunks.append(conn.buffer.popleft())
            conn.last_activity = time.monotonic()
            return chunks

    def get_sse_format(self, chunk: TokenChunk) -> str:
        """Format chunk as SSE event."""
        if chunk.is_final:
            return f'data: {{"index": {chunk.index}, "text": "{chunk.text}", "done": true}}\n\n'
        return f'data: {{"index": {chunk.index}, "text": "{chunk.text}"}}\n\n'

    def aggregate_stream(self, client_id: str) -> str:
        with self._lock:
            conn = self._connections.get(client_id)
            if not conn:
                return ""
            return "".join(c.text for c in conn.buffer)

    def detect_backpressure(self, client_id: str, threshold: int = 50) -> bool:
        with self._lock:
            conn = self._connections.get(client_id)
            if not conn:
                return False
            return len(conn.buffer) > threshold

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "connections": len(self._connections),
                "total_tokens": sum(c.total_tokens for c in self._connections.values()),
                "streaming": sum(1 for c in self._connections.values() if c.status == StreamStatus.STREAMING),
                "completed": sum(1 for c in self._connections.values() if c.status == StreamStatus.COMPLETED),
            }


class StreamingProducer:
    """Producer that simulates token generation and pushes to engine."""

    def __init__(self, engine: StreamingEngine, tokens_per_second: float = 10.0):
        self.engine = engine
        self.tokens_per_second = tokens_per_second

    def stream_text(self, client_id: str, text: str) -> None:
        """Break text into tokens and stream them."""
        words = text.split()
        delay = 1.0 / self.tokens_per_second
        for i, word in enumerate(words):
            is_final = i == len(words) - 1
            self.engine.push_chunk(client_id, word + ("" if is_final else " "), is_final)
            time.sleep(delay)


class StreamingConsumer:
    """Consumer that pulls chunks from engine."""

    def __init__(self, engine: StreamingEngine):
        self.engine = engine

    def consume(self, client_id: str, timeout: float = 5.0) -> str:
        """Consume all chunks until completion or timeout."""
        t0 = time.monotonic()
        result = []
        while time.monotonic() - t0 < timeout:
            chunks = self.engine.pull_chunks(client_id, max_chunks=5)
            for chunk in chunks:
                result.append(chunk.text)
                if chunk.is_final:
                    return "".join(result)
            if not chunks:
                time.sleep(0.05)
        return "".join(result)


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Real-Time Streaming Engine")
    print("ai/llm_realtime_streaming_native.py")
    print("=" * 60)

    engine = StreamingEngine(max_connections=10)

    # 1. Connect client
    print("[1] Connect Client")
    cid = engine.connect()
    print(f"  Client: {cid}")

    # 2. Stream tokens
    print("[2] Stream Tokens")
    text = "The quick brown fox jumps over the lazy dog"
    producer = StreamingProducer(engine, tokens_per_second=20.0)
    producer.stream_text(cid, text)
    print(f"  Streamed: {text}")

    # 3. Pull and consume
    print("[3] Consume Stream")
    consumer = StreamingConsumer(engine)
    received = consumer.consume(cid, timeout=2.0)
    print(f"  Received: {received}")
    print(f"  Match: {received == text}")

    # 4. SSE format
    print("[4] SSE Format")
    chunk = TokenChunk(index=0, text="Hello", timestamp=time.monotonic())
    print(f"  {engine.get_sse_format(chunk).strip()}")
    final_chunk = TokenChunk(index=1, text="", timestamp=time.monotonic(), is_final=True)
    print(f"  {engine.get_sse_format(final_chunk).strip()}")

    # 5. Multiple clients
    print("[5] Multiple Clients")
    c1 = engine.connect()
    c2 = engine.connect()
    producer.stream_text(c1, "Client one message")
    producer.stream_text(c2, "Client two message")
    print(f"  Client 1: {consumer.consume(c1, timeout=1.0)}")
    print(f"  Client 2: {consumer.consume(c2, timeout=1.0)}")

    # 6. Stats
    print("[6] Engine Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
