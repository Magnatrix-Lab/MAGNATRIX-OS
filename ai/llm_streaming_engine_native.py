"""Streaming Engine — Real-time response streaming, buffering, and SSE formatting.

Modul ini menyediakan:
- StreamBuffer untuk buffering chunks dengan watermarking
- StreamFormatter untuk format SSE, JSON stream, dan plain text
- StreamMerger untuk merge multiple streams
- StreamThrottle untuk rate limiting streaming
- StreamingEngine untuk end-to-end streaming management
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Iterator, Tuple
from enum import Enum, auto


class StreamFormat(Enum):
    SSE = "sse"  # Server-Sent Events
    JSON = "json"  # JSON lines
    PLAIN = "plain"  # Plain text
    NDJSON = "ndjson"  # Newline-delimited JSON


@dataclass
class StreamChunk:
    """Single chunk in a stream."""
    chunk_id: str
    data: str
    index: int
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_final: bool = False


class StreamBuffer:
    """Buffer streaming chunks with watermark control."""

    def __init__(self, max_size: int = 1000, watermark: int = 100):
        self.max_size = max_size
        self.watermark = watermark
        self._chunks: List[StreamChunk] = []
        self._total_chars = 0

    def add(self, chunk: StreamChunk) -> bool:
        if len(self._chunks) >= self.max_size:
            return False
        self._chunks.append(chunk)
        self._total_chars += len(chunk.data)
        return True

    def get_full_text(self) -> str:
        return "".join(c.data for c in self._chunks)

    def get_since(self, index: int) -> List[StreamChunk]:
        return [c for c in self._chunks if c.index >= index]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "chunks": len(self._chunks),
            "total_chars": self._total_chars,
            "at_watermark": len(self._chunks) >= self.watermark,
        }

    def clear(self) -> None:
        self._chunks = []
        self._total_chars = 0


class StreamFormatter:
    """Format stream chunks for different output types."""

    def format_sse(self, chunk: StreamChunk) -> str:
        lines = chunk.data.split("\n")
        formatted = []
        for line in lines:
            formatted.append(f"data: {line}")
        formatted.append(f"id: {chunk.chunk_id}")
        if chunk.is_final:
            formatted.append("event: done")
        formatted.append("")
        return "\n".join(formatted)

    def format_json(self, chunk: StreamChunk) -> str:
        return json.dumps({
            "id": chunk.chunk_id,
            "index": chunk.index,
            "data": chunk.data,
            "metadata": chunk.metadata,
            "final": chunk.is_final,
        }) + "\n"

    def format_plain(self, chunk: StreamChunk) -> str:
        return chunk.data

    def format(self, chunk: StreamChunk, fmt: StreamFormat) -> str:
        if fmt == StreamFormat.SSE:
            return self.format_sse(chunk)
        elif fmt == StreamFormat.JSON or fmt == StreamFormat.NDJSON:
            return self.format_json(chunk)
        return self.format_plain(chunk)


class StreamMerger:
    """Merge multiple streams into one."""

    def __init__(self, strategy: str = "interleave"):
        self.strategy = strategy  # interleave, concat, priority

    def merge(self, streams: List[Iterator[StreamChunk]]) -> Iterator[StreamChunk]:
        if self.strategy == "concat":
            for stream in streams:
                yield from stream
        elif self.strategy == "interleave":
            iterators = [iter(s) for s in streams]
            idx = 0
            while iterators:
                try:
                    chunk = next(iterators[idx % len(iterators)])
                    yield chunk
                except StopIteration:
                    del iterators[idx % len(iterators)]
                    if not iterators:
                        break
                idx += 1
        else:
            for stream in streams:
                yield from stream

    def merge_ordered(self, streams: List[Tuple[int, Iterator[StreamChunk]]]) -> Iterator[StreamChunk]:
        """Merge by priority."""
        sorted_streams = sorted(streams, key=lambda x: x[0])
        for _, stream in sorted_streams:
            yield from stream


class StreamThrottle:
    """Rate limit stream output."""

    def __init__(self, max_chunks_per_second: float = 10.0, max_chars_per_second: float = 1000.0):
        self.max_cps = max_chunks_per_second
        self.max_chars_ps = max_chars_per_second
        self._last_time = 0.0
        self._chunk_count = 0
        self._char_count = 0
        self._window_start = 0.0

    def can_send(self, chunk_size: int) -> bool:
        now = time.time()
        if now - self._window_start >= 1.0:
            self._window_start = now
            self._chunk_count = 0
            self._char_count = 0
        if self._chunk_count >= self.max_cps:
            return False
        if self._char_count + chunk_size > self.max_chars_ps:
            return False
        return True

    def record(self, chunk_size: int) -> None:
        self._chunk_count += 1
        self._char_count += chunk_size

    def wait_time(self) -> float:
        now = time.time()
        if now - self._window_start >= 1.0:
            return 0.0
        return max(0.0, 1.0 - (now - self._window_start))


class StreamingEngine:
    """End-to-end streaming management."""

    def __init__(self, fmt: StreamFormat = StreamFormat.SSE, buffer_size: int = 1000):
        self.format = fmt
        self.buffer = StreamBuffer(max_size=buffer_size)
        self.formatter = StreamFormatter()
        self.throttle = StreamThrottle()
        self._chunks_emitted = 0
        self._start_time = 0.0

    def start(self) -> None:
        self._start_time = time.time()
        self._chunks_emitted = 0

    def emit(self, data: str, metadata: Optional[Dict[str, Any]] = None, is_final: bool = False) -> Optional[str]:
        chunk = StreamChunk(
            chunk_id=str(uuid.uuid4())[:8],
            data=data,
            index=self._chunks_emitted,
            timestamp=time.time(),
            metadata=metadata or {},
            is_final=is_final,
        )
        if not self.buffer.add(chunk):
            return None
        self._chunks_emitted += 1
        return self.formatter.format(chunk, self.format)

    def get_full_text(self) -> str:
        return self.buffer.get_full_text()

    def get_stats(self) -> Dict[str, Any]:
        duration = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "chunks_emitted": self._chunks_emitted,
            "duration": round(duration, 3),
            "chars_per_second": round(self.buffer._total_chars / max(duration, 0.001), 1),
            "buffer_stats": self.buffer.get_stats(),
            "format": self.format.value,
        }

    def create_iterator(self, data_source: Callable[[], Optional[str]], interval: float = 0.1) -> Iterator[str]:
        """Create iterator from data source."""
        self.start()
        idx = 0
        while True:
            data = data_source()
            if data is None:
                # Emit final
                chunk = StreamChunk(
                    chunk_id="final",
                    data="",
                    index=idx,
                    timestamp=time.time(),
                    is_final=True,
                )
                yield self.formatter.format(chunk, self.format)
                break
            formatted = self.emit(data, is_final=False)
            if formatted:
                yield formatted
            idx += 1
            time.sleep(interval)

    def export_transcript(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.get_full_text())


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("STREAMING ENGINE DEMO")
    print("=" * 70)

    # 1. Basic streaming
    print("\n[1] Basic Streaming (SSE format)")
    engine = StreamingEngine(fmt=StreamFormat.SSE)
    engine.start()
    for i, word in enumerate(["Hello", "world", "this", "is", "a", "stream"]):
        out = engine.emit(f"{word} ", metadata={"word_index": i})
        print(f"  Chunk {i}: {out[:50]}...")
    final = engine.emit("", is_final=True)
    print(f"  Final: {final}")
    print(f"  Full text: '{engine.get_full_text()}'")
    print(f"  Stats: {engine.get_stats()}")

    # 2. JSON streaming
    print("\n[2] JSON Streaming")
    engine2 = StreamingEngine(fmt=StreamFormat.JSON)
    engine2.start()
    for i in range(3):
        out = engine2.emit(f"Message {i}", metadata={"seq": i})
        print(f"  {out.strip()}")

    # 3. Buffer watermark
    print("\n[3] Buffer Watermark")
    buf = StreamBuffer(max_size=5, watermark=3)
    for i in range(5):
        chunk = StreamChunk(str(i), f"data{i}", i, time.time())
        buf.add(chunk)
    print(f"  Buffer stats: {buf.get_stats()}")

    # 4. Stream merger
    print("\n[4] Stream Merger")
    def make_stream(words):
        for w in words:
            yield StreamChunk(str(uuid.uuid4())[:4], w, 0, time.time())

    merger = StreamMerger(strategy="interleave")
    stream1 = make_stream(["A1", "A2", "A3"])
    stream2 = make_stream(["B1", "B2", "B3"])
    merged = merger.merge([stream1, stream2])
    result = [c.data for c in merged]
    print(f"  Interleaved: {result}")

    # 5. Throttle
    print("\n[5] Stream Throttle")
    throttle = StreamThrottle(max_chunks_per_second=2, max_chars_per_second=50)
    for i in range(5):
        can = throttle.can_send(10)
        if can:
            throttle.record(10)
        print(f"  Chunk {i}: {'SENT' if can else 'BLOCKED'}")
        time.sleep(0.3)

    # 6. Iterator
    print("\n[6] Stream Iterator")
    words = ["The", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"]
    idx = 0
    def word_source():
        nonlocal idx
        if idx < len(words):
            w = words[idx]
            idx += 1
            return w + " "
        return None

    engine3 = StreamingEngine(fmt=StreamFormat.PLAIN)
    for formatted in engine3.create_iterator(word_source, interval=0.05):
        print(f"  Received: '{formatted.strip()}'")
        if "final" in formatted.lower() or "done" in formatted.lower():
            break

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
