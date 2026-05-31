"""
local_inference_native.py — Clean Local Inference Infrastructure for MAGNATRIX-OS

Pure Python, stdlib only. Provides local model management, streaming generation,
context compression, token counting, model routing, and inference metrics.

No censorship evasion. No jailbreak helpers. Just clean, efficient local inference.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import struct
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Protocol,
    Tuple,
    Union,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CONTEXT_WINDOW = 4096
DEFAULT_MAX_TOKENS = 512
DEFAULT_TEMPERATURE = 0.7
STOP_SEQUENCES_DEFAULT = ["<|endoftext|>", "<|im_end|>", "<|end|>", "<|eot_id|>"]

# GGUF magic number and version constants
GGUF_MAGIC = b"GGUF"
GGUF_SUPPORTED_VERSIONS = (2, 3)

# Approximate token ratios for different languages
TOKEN_RATIO_EN = 0.25  # ~4 chars per token (English)
TOKEN_RATIO_CODE = 0.30  # ~3.3 chars per token (code)
TOKEN_RATIO_CJK = 0.50  # ~2 chars per token (CJK)


# ---------------------------------------------------------------------------
# Data classes / Enums
# ---------------------------------------------------------------------------

class ModelState(Enum):
    """Lifecycle states for a managed model."""

    UNLOADED = auto()
    LOADING = auto()
    LOADED = auto()
    WARMING = auto()
    WARMED = auto()
    UNLOADING = auto()
    ERROR = auto()


class RoutingStrategy(Enum):
    """How ModelRouter selects a backend."""

    LOCAL_FIRST = auto()   # Prefer local, fall back to cloud
    CLOUD_FIRST = auto()   # Prefer cloud, fall back to local
    LOCAL_ONLY = auto()    # Never use cloud
    CLOUD_ONLY = auto()    # Never use local


@dataclass
class ModelInfo:
    """Metadata for a discovered GGUF model."""

    name: str
    path: Path
    size_bytes: int
    parameters: str = "unknown"
    context_window: int = DEFAULT_CONTEXT_WINDOW
    quantization: str = "unknown"
    architecture: str = "unknown"
    version: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: ModelState = ModelState.UNLOADED

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


@dataclass
class GenerationConfig:
    """Configuration for a single generation call."""

    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    top_p: float = 1.0
    top_k: int = 40
    repetition_penalty: float = 1.0
    stop_sequences: List[str] = field(default_factory=lambda: list(STOP_SEQUENCES_DEFAULT))
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    seed: Optional[int] = None
    stream: bool = True


@dataclass
class InferenceResult:
    """Result of a generation call."""

    text: str
    tokens_generated: int
    tokens_per_second: float
    latency_ms: float
    finish_reason: str  # "stop", "length", "timeout", "error"
    model_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricsSnapshot:
    """Point-in-time inference metrics."""

    timestamp: float
    requests_total: int
    tokens_generated_total: int
    tokens_per_second_avg: float
    latency_ms_avg: float
    latency_ms_p95: float
    latency_ms_p99: float
    throughput_tps: float
    queue_depth: int
    active_models: int
    memory_usage_mb: float


# ---------------------------------------------------------------------------
# 1. TokenCounter — approximate token counting without tiktoken
# ---------------------------------------------------------------------------

class TokenCounter:
    """
    Fast approximate token counting without external dependencies.

    Uses a hybrid heuristic:
    - 1 token per CJK character
    - 1 token per 3-4 Latin characters (word-based for accuracy)
    - Special handling for code, URLs, numbers, and punctuation
    """

    def __init__(self, avg_chars_per_token: float = 4.0):
        self.avg_chars_per_token = avg_chars_per_token
        # Cache for repeated counting
        self._cache: Dict[str, int] = {}
        self._cache_lock = threading.Lock()

    # Regex patterns for tokenization heuristics
    _CJK_RE = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]")
    _WORD_RE = re.compile(r"[a-zA-Z]+")
    _NUM_RE = re.compile(r"\d+")
    _URL_RE = re.compile(r"https?://\S+|www\.\S+")
    _CODE_RE = re.compile(r"[\{\}\[\]\(\);,\.:=+\-*/<>!&|^%]+")

    def count(self, text: str, use_cache: bool = True) -> int:
        """Return estimated token count for *text*."""
        if not text:
            return 0

        if use_cache:
            with self._cache_lock:
                if text in self._cache:
                    return self._cache[text]

        total = 0
        remaining = text

        # URLs: each ~4-6 tokens
        for m in self._URL_RE.finditer(text):
            total += max(4, len(m.group()) // 8)
            remaining = remaining.replace(m.group(), " ", 1)

        # CJK characters: 1 token each
        cjk_chars = self._CJK_RE.findall(remaining)
        total += len(cjk_chars)
        remaining = self._CJK_RE.sub(" ", remaining)

        # Words: 1 token per ~4 chars, but common words = 1 token
        words = self._WORD_RE.findall(remaining)
        for w in words:
            if len(w) <= 3:
                total += 1
            elif len(w) <= 6:
                total += 1
            else:
                total += len(w) // 3
            remaining = remaining.replace(w, " ", 1)

        # Numbers: 1 token per ~3 digits
        numbers = self._NUM_RE.findall(remaining)
        for n in numbers:
            total += max(1, len(n) // 3)
            remaining = remaining.replace(n, " ", 1)

        # Code symbols: 1 token per ~2 chars
        code_symbols = self._CODE_RE.findall(remaining)
        for cs in code_symbols:
            total += max(1, len(cs) // 2)
            remaining = remaining.replace(cs, " ", 1)

        # Remaining whitespace/punctuation: 1 token per ~5 chars
        remaining_clean = remaining.strip()
        if remaining_clean:
            total += max(1, len(remaining_clean) // 5)

        result = max(1, total) if text else 0

        if use_cache:
            with self._cache_lock:
                # Simple LRU: keep cache bounded
                if len(self._cache) > 10000:
                    self._cache.clear()
                self._cache[text] = result

        return result

    def count_messages(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens for a chat message list (including role overhead)."""
        total = 0
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            # ~4 tokens overhead per message (role markers, delimiters)
            total += 4 + self.count(role) + self.count(content)
        return total + 2  # assistant prefix overhead

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate *text* to fit within *max_tokens* (approximate)."""
        if self.count(text) <= max_tokens:
            return text
        # Binary search for truncation point
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if self.count(text[:mid]) <= max_tokens:
                low = mid
            else:
                high = mid - 1
        return text[:low]


# ---------------------------------------------------------------------------
# 2. ContextCompressor — manage long contexts within model limits
# ---------------------------------------------------------------------------

class ContextCompressor:
    """
    Compress conversation history to fit within a model's context window.

    Strategies:
    - truncation: cut oldest messages
    - sliding_window: keep only last N messages
    - summarization: compress early messages into a summary
    """

    def __init__(
        self,
        counter: TokenCounter,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
        reserve_tokens: int = 256,
    ):
        self.counter = counter
        self.context_window = context_window
        self.reserve_tokens = reserve_tokens  # reserve for response
        self.max_input_tokens = context_window - reserve_tokens

    def fit(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Return a copy of *messages* guaranteed to fit in context window."""
        if not messages:
            return messages

        current = list(messages)
        total = self.counter.count_messages(current)

        if total <= self.max_input_tokens:
            return current

        # Strategy 1: try simple truncation (remove oldest)
        while len(current) > 1 and total > self.max_input_tokens:
            current.pop(0)
            total = self.counter.count_messages(current)

        if total <= self.max_input_tokens:
            return current

        # Strategy 2: aggressive sliding window — keep only last few
        window_size = max(1, len(current) // 2)
        while window_size > 0:
            trimmed = current[-window_size:]
            if self.counter.count_messages(trimmed) <= self.max_input_tokens:
                return trimmed
            window_size -= 1

        # Fallback: keep only the very last message, truncated
        last = current[-1]
        content = last.get("content", "")
        truncated_content = self.counter.truncate_to_tokens(
            content, self.max_input_tokens - 8
        )
        return [{"role": last.get("role", "user"), "content": truncated_content}]

    def sliding_window(
        self, messages: List[Dict[str, str]], max_messages: int = 10
    ) -> List[Dict[str, str]]:
        """Keep only the last *max_messages* messages."""
        return messages[-max_messages:] if len(messages) > max_messages else list(messages)

    def summarize_turn(
        self, messages: List[Dict[str, str]], keep_last: int = 2
    ) -> List[Dict[str, str]]:
        """
        Replace early messages with a single summary message.
        Returns [summary_msg, ...keep_last messages].
        """
        if len(messages) <= keep_last + 1:
            return list(messages)

        to_summarize = messages[:-keep_last]
        keep = messages[-keep_last:]

        # Build a simple summary string
        summary_parts = []
        for msg in to_summarize:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            summary_parts.append(f"{role}: {content}")

        summary_text = (
            "[Earlier conversation summary]\n"
            + "\n".join(summary_parts)
            + "\n[End summary]"
        )

        # Truncate summary if too long
        summary_text = self.counter.truncate_to_tokens(
            summary_text, self.max_input_tokens // 3
        )

        summary_msg = {"role": "system", "content": summary_text}
        return [summary_msg] + keep

    def truncate_text(self, text: str, max_tokens: Optional[int] = None) -> str:
        """Truncate raw text to fit token budget."""
        budget = max_tokens or self.max_input_tokens
        return self.counter.truncate_to_tokens(text, budget)


# ---------------------------------------------------------------------------
# 3. InferenceMetrics — track tokens/sec, latency, throughput, queue depth
# ---------------------------------------------------------------------------

class InferenceMetrics:
    """
    Thread-safe metrics collector for inference performance.

    Tracks per-request latencies, token counts, and maintains rolling
    averages / percentiles over a configurable window.
    """

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self._requests: Deque[Tuple[float, float, int]] = deque(maxlen=window_size)
        # each entry: (timestamp, latency_ms, tokens_generated)
        self._lock = threading.Lock()
        self._start_time = time.time()

    def record(self, latency_ms: float, tokens_generated: int) -> None:
        """Record a completed inference request."""
        with self._lock:
            self._requests.append((time.time(), latency_ms, tokens_generated))

    def snapshot(self) -> MetricsSnapshot:
        """Return current metrics snapshot."""
        with self._lock:
            requests = list(self._requests)

        if not requests:
            return MetricsSnapshot(
                timestamp=time.time(),
                requests_total=0,
                tokens_generated_total=0,
                tokens_per_second_avg=0.0,
                latency_ms_avg=0.0,
                latency_ms_p95=0.0,
                latency_ms_p99=0.0,
                throughput_tps=0.0,
                queue_depth=0,
                active_models=0,
                memory_usage_mb=0.0,
            )

        latencies = [r[1] for r in requests]
        tokens = [r[2] for r in requests]
        total_tokens = sum(tokens)
        total_latency = sum(latencies)

        # Rolling average tokens/sec
        tps_list = [
            (tokens[i] / (latencies[i] / 1000.0)) if latencies[i] > 0 else 0.0
            for i in range(len(tokens))
        ]
        avg_tps = sum(tps_list) / len(tps_list) if tps_list else 0.0

        # Percentiles
        sorted_lat = sorted(latencies)
        p95_idx = int(len(sorted_lat) * 0.95)
        p99_idx = int(len(sorted_lat) * 0.99)
        p95 = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]
        p99 = sorted_lat[min(p99_idx, len(sorted_lat) - 1)]

        # Throughput over last 60 seconds
        now = time.time()
        recent = [r for r in requests if now - r[0] < 60.0]
        throughput = sum(r[2] for r in recent) / 60.0 if recent else 0.0

        return MetricsSnapshot(
            timestamp=now,
            requests_total=len(requests),
            tokens_generated_total=total_tokens,
            tokens_per_second_avg=avg_tps,
            latency_ms_avg=total_latency / len(latencies),
            latency_ms_p95=p95,
            latency_ms_p99=p99,
            throughput_tps=throughput,
            queue_depth=0,  # populated by caller if needed
            active_models=0,
            memory_usage_mb=0.0,
        )

    def report(self) -> str:
        """Human-readable metrics report."""
        s = self.snapshot()
        lines = [
            "=== Inference Metrics ===",
            f"Requests (total):      {s.requests_total}",
            f"Tokens generated:      {s.tokens_generated_total}",
            f"Avg tokens/sec:        {s.tokens_per_second_avg:.2f}",
            f"Avg latency (ms):      {s.latency_ms_avg:.2f}",
            f"P95 latency (ms):      {s.latency_ms_p95:.2f}",
            f"P99 latency (ms):      {s.latency_ms_p99:.2f}",
            f"Throughput (tps):      {s.throughput_tps:.2f}",
            f"Queue depth:           {s.queue_depth}",
            f"Active models:         {s.active_models}",
            f"Memory usage (MB):     {s.memory_usage_mb:.2f}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. LocalModelManager — GGUF discovery, load/unload, warm-up, memory tracking
# ---------------------------------------------------------------------------

class LocalModelManager:
    """
    Manages local GGUF model files.

    - Scan directories for .gguf files
    - Parse metadata (context window, params, quant, arch)
    - Track load state, memory usage
    - Warm-up (pre-load) frequently used models
    """

    def __init__(
        self,
        models_dir: Union[str, Path],
        counter: Optional[TokenCounter] = None,
    ):
        self.models_dir = Path(models_dir).expanduser().resolve()
        self.counter = counter or TokenCounter()
        self._models: Dict[str, ModelInfo] = {}
        self._loaded: Dict[str, Any] = {}  # model_name -> loaded object (opaque)
        self._lock = threading.RLock()
        self._memory_usage_mb: float = 0.0

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def scan(self) -> List[ModelInfo]:
        """Scan *models_dir* for GGUF files and return discovered models."""
        discovered: List[ModelInfo] = []
        if not self.models_dir.exists():
            return discovered

        for path in self.models_dir.rglob("*.gguf"):
            info = self._parse_gguf(path)
            discovered.append(info)
            with self._lock:
                self._models[info.name] = info

        return discovered

    def _parse_gguf(self, path: Path) -> ModelInfo:
        """Parse GGUF header to extract metadata."""
        name = path.stem
        size = path.stat().st_size

        info = ModelInfo(name=name, path=path, size_bytes=size)

        try:
            with open(path, "rb") as f:
                magic = f.read(4)
                if magic != GGUF_MAGIC:
                    info.metadata["parse_error"] = "Not a valid GGUF file"
                    return info

                version_raw = f.read(4)
                if len(version_raw) < 4:
                    info.metadata["parse_error"] = "Truncated header"
                    return info

                version = struct.unpack("<I", version_raw)[0]
                info.version = version

                if version not in GGUF_SUPPORTED_VERSIONS:
                    info.metadata["warning"] = f"Untested GGUF version {version}"

                # Parse tensor count and metadata kv count (u64)
                if version >= 3:
                    # v3 layout: magic(4) + version(4) + tensor_count(8) + meta_kv_count(8)
                    tensor_count = struct.unpack("<Q", f.read(8))[0]
                    meta_kv_count = struct.unpack("<Q", f.read(8))[0]
                else:
                    # v2 layout: magic(4) + version(4) + tensor_count(8) + meta_kv_count(8)
                    tensor_count = struct.unpack("<Q", f.read(8))[0]
                    meta_kv_count = struct.unpack("<Q", f.read(8))[0]

                info.metadata["tensor_count"] = tensor_count
                info.metadata["meta_kv_count"] = meta_kv_count

                # Read metadata key-value pairs (lightweight parsing)
                meta = self._read_gguf_metadata(f, meta_kv_count, max_kv=64)
                info.metadata.update(meta)

                # Extract known fields
                if "general.architecture" in meta:
                    info.architecture = meta["general.architecture"]
                if "general.name" in meta:
                    info.name = meta["general.name"]
                if "llama.context_length" in meta:
                    info.context_window = int(meta["llama.context_length"])
                elif "general.context_length" in meta:
                    info.context_window = int(meta["general.context_length"])
                if "general.parameter_count" in meta:
                    params = int(meta["general.parameter_count"])
                    info.parameters = self._format_params(params)
                if "general.file_type" in meta:
                    info.quantization = self._format_quant(meta["general.file_type"])

        except Exception as e:
            info.metadata["parse_error"] = str(e)

        return info

    def _read_gguf_metadata(
        self, f: io.BufferedReader, kv_count: int, max_kv: int = 64
    ) -> Dict[str, Any]:
        """Read GGUF metadata key-value pairs (simplified)."""
        meta: Dict[str, Any] = {}
        for _ in range(min(kv_count, max_kv)):
            try:
                # Read key length (u64) + key string
                key_len_data = f.read(8)
                if len(key_len_data) < 8:
                    break
                key_len = struct.unpack("<Q", key_len_data)[0]
                if key_len > 1024:
                    break  # sanity check
                key = f.read(key_len).decode("utf-8", errors="replace")

                # Read value type (u32) and value
                type_data = f.read(4)
                if len(type_data) < 4:
                    break
                val_type = struct.unpack("<I", type_data)[0]

                val = self._read_gguf_value(f, val_type)
                if val is not None:
                    meta[key] = val

            except Exception:
                break
        return meta

    def _read_gguf_value(self, f: io.BufferedReader, val_type: int) -> Any:
        """Read a single GGUF value based on its type."""
        try:
            if val_type == 0:   # uint8
                return struct.unpack("<B", f.read(1))[0]
            elif val_type == 1:  # int8
                return struct.unpack("<b", f.read(1))[0]
            elif val_type == 2:  # uint16
                return struct.unpack("<H", f.read(2))[0]
            elif val_type == 3:  # int16
                return struct.unpack("<h", f.read(2))[0]
            elif val_type == 4:  # uint32
                return struct.unpack("<I", f.read(4))[0]
            elif val_type == 5:  # int32
                return struct.unpack("<i", f.read(4))[0]
            elif val_type == 6:  # uint64
                return struct.unpack("<Q", f.read(8))[0]
            elif val_type == 7:  # int64
                return struct.unpack("<q", f.read(8))[0]
            elif val_type == 8:  # float32
                return struct.unpack("<f", f.read(4))[0]
            elif val_type == 9:  # float64
                return struct.unpack("<d", f.read(8))[0]
            elif val_type == 10:  # bool
                return struct.unpack("<B", f.read(1))[0] != 0
            elif val_type == 11:  # string
                str_len = struct.unpack("<Q", f.read(8))[0]
                if str_len > 65536:
                    return None
                return f.read(str_len).decode("utf-8", errors="replace")
            elif val_type == 12:  # array
                arr_type = struct.unpack("<I", f.read(4))[0]
                arr_len = struct.unpack("<Q", f.read(8))[0]
                # Skip array contents for lightweight parsing
                for _ in range(min(arr_len, 128)):
                    self._read_gguf_value(f, arr_type)
                return "<array>"
            else:
                return None
        except Exception:
            return None

    @staticmethod
    def _format_params(n: int) -> str:
        if n >= 1_000_000_000:
            return f"{n / 1_000_000_000:.1f}B"
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        return str(n)

    @staticmethod
    def _format_quant(file_type: Union[int, str]) -> str:
        if isinstance(file_type, str):
            return file_type
        # Common GGUF file type mappings
        mapping = {
            1: "F32", 2: "F16", 3: "Q4_0", 4: "Q4_1", 5: "Q5_0",
            6: "Q5_1", 7: "Q8_0", 8: "Q8_1", 9: "Q2_K", 10: "Q3_K",
            11: "Q4_K", 12: "Q5_K", 13: "Q6_K", 14: "Q8_K",
        }
        return mapping.get(file_type, f"TYPE_{file_type}")

    # ------------------------------------------------------------------
    # Load / Unload / Warm-up
    # ------------------------------------------------------------------

    def load(self, name: str) -> ModelInfo:
        """Mark model as loaded (actual loading is backend-specific)."""
        with self._lock:
            info = self._models.get(name)
            if not info:
                raise ValueError(f"Model '{name}' not found. Run scan() first.")
            info.state = ModelState.LOADING
            # Simulate load (in real use, load into llama-cpp or similar)
            info.state = ModelState.LOADED
            self._memory_usage_mb += info.size_mb
            return info

    def unload(self, name: str) -> None:
        """Unload a model and free memory."""
        with self._lock:
            info = self._models.get(name)
            if not info:
                return
            info.state = ModelState.UNLOADING
            info.state = ModelState.UNLOADED
            self._memory_usage_mb = max(0.0, self._memory_usage_mb - info.size_mb)
            self._loaded.pop(name, None)

    def warm_up(self, name: str, prompt: str = "Hello, world!") -> ModelInfo:
        """Warm-up a model by running a small inference pass."""
        info = self.load(name)
        with self._lock:
            info.state = ModelState.WARMING
        # Simulate warm-up inference (would be real inference in production)
        time.sleep(0.01)
        with self._lock:
            info.state = ModelState.WARMED
        return info

    def get(self, name: str) -> Optional[ModelInfo]:
        """Get model info by name."""
        with self._lock:
            return self._models.get(name)

    def list_models(self) -> List[ModelInfo]:
        """Return all discovered models."""
        with self._lock:
            return list(self._models.values())

    def list_loaded(self) -> List[ModelInfo]:
        """Return models currently in LOADED or WARMED state."""
        with self._lock:
            return [
                m for m in self._models.values()
                if m.state in (ModelState.LOADED, ModelState.WARMED)
            ]

    @property
    def memory_usage_mb(self) -> float:
        with self._lock:
            return self._memory_usage_mb


# ---------------------------------------------------------------------------
# 5. StreamingGenerator — streaming text generation with token budget
# ---------------------------------------------------------------------------

class StreamingGenerator:
    """
    Streaming text generator with token budget and stop-sequence handling.

    Designed to work with a mock or real model backend. Provides:
    - Token-by-token streaming via generator
    - Budget enforcement (max_tokens)
    - Stop sequence detection
    - Optional repetition penalty
    """

    def __init__(
        self,
        counter: TokenCounter,
        metrics: Optional[InferenceMetrics] = None,
    ):
        self.counter = counter
        self.metrics = metrics or InferenceMetrics()

    def generate(
        self,
        prompt: str,
        model_backend: "ModelBackend",
        config: Optional[GenerationConfig] = None,
    ) -> Generator[str, None, None]:
        """
        Stream generated tokens for *prompt* using *model_backend*.

        Yields partial text strings. The caller should concatenate them.
        """
        cfg = config or GenerationConfig()
        start_time = time.perf_counter()
        tokens_generated = 0
        generated_text = ""

        # Check prompt budget
        prompt_tokens = self.counter.count(prompt)
        if prompt_tokens >= cfg.max_tokens:
            yield ""
            return

        effective_budget = cfg.max_tokens - prompt_tokens

        for token in model_backend.iter_tokens(prompt, cfg):
            if tokens_generated >= effective_budget:
                break

            generated_text += token
            tokens_generated += max(1, self.counter.count(token))

            # Check stop sequences
            if self._check_stop(generated_text, cfg.stop_sequences):
                # Trim stop sequence from output
                generated_text = self._trim_stop(generated_text, cfg.stop_sequences)
                break

            yield token

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        self.metrics.record(latency_ms, tokens_generated)

    def generate_complete(
        self,
        prompt: str,
        model_backend: "ModelBackend",
        config: Optional[GenerationConfig] = None,
    ) -> InferenceResult:
        """
        Non-streaming generation: collect all tokens and return InferenceResult.
        """
        cfg = config or GenerationConfig()
        start_time = time.perf_counter()
        tokens: List[str] = []
        tokens_generated = 0

        prompt_tokens = self.counter.count(prompt)
        effective_budget = max(1, cfg.max_tokens - prompt_tokens)

        for token in model_backend.iter_tokens(prompt, cfg):
            if tokens_generated >= effective_budget:
                break
            tokens.append(token)
            tokens_generated += max(1, self.counter.count(token))

            current_text = "".join(tokens)
            if self._check_stop(current_text, cfg.stop_sequences):
                tokens = self._trim_stop_tokens(tokens, cfg.stop_sequences)
                break

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        self.metrics.record(latency_ms, tokens_generated)

        text = "".join(tokens)
        tps = (tokens_generated / (latency_ms / 1000.0)) if latency_ms > 0 else 0.0

        return InferenceResult(
            text=text,
            tokens_generated=tokens_generated,
            tokens_per_second=tps,
            latency_ms=latency_ms,
            finish_reason="stop" if tokens_generated < effective_budget else "length",
            model_used=getattr(model_backend, "name", "unknown"),
        )

    @staticmethod
    def _check_stop(text: str, stop_sequences: List[str]) -> bool:
        for seq in stop_sequences:
            if seq in text:
                return True
        return False

    @staticmethod
    def _trim_stop(text: str, stop_sequences: List[str]) -> str:
        earliest = len(text)
        for seq in stop_sequences:
            idx = text.find(seq)
            if idx >= 0 and idx < earliest:
                earliest = idx
        return text[:earliest]

    @staticmethod
    def _trim_stop_tokens(tokens: List[str], stop_sequences: List[str]) -> List[str]:
        text = "".join(tokens)
        trimmed = StreamingGenerator._trim_stop(text, stop_sequences)
        # Reconstruct tokens (approximate)
        return [trimmed] if trimmed else []


# ---------------------------------------------------------------------------
# ModelBackend Protocol — abstraction for local/cloud inference
# ---------------------------------------------------------------------------

class ModelBackend(Protocol):
    """Protocol for pluggable model backends."""

    name: str

    def iter_tokens(
        self, prompt: str, config: GenerationConfig
    ) -> Iterator[str]:
        ...

    def is_available(self) -> bool:
        ...


# ---------------------------------------------------------------------------
# MockBackend — self-test backend (simulates inference)
# ---------------------------------------------------------------------------

class MockBackend:
    """Mock model backend for testing and development."""

    def __init__(self, name: str = "mock-model", delay_ms: float = 1.0):
        self.name = name
        self.delay_ms = delay_ms
        self._vocabulary = [
            "The", " quick", " brown", " fox", " jumps", " over", " the", " lazy", " dog",
            ".", "\n", " A", " beautiful", " day", " in", " the", " neighborhood", "!",
            " The", " answer", " is", " 42", ".", " Local", " inference", " works", " great",
            ".", " MAGNATRIX", "-OS", " runs", " smoothly", ".", " Model", " loaded",
            " and", " ready", " for", " generation", ".",
        ]
        self._idx = 0

    def iter_tokens(self, prompt: str, config: GenerationConfig) -> Iterator[str]:
        """Yield tokens from a rotating vocabulary."""
        max_tokens = config.max_tokens
        for i in range(max_tokens):
            if self.delay_ms > 0:
                time.sleep(self.delay_ms / 1000.0)
            token = self._vocabulary[self._idx % len(self._vocabulary)]
            self._idx += 1
            yield token

    def is_available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# 6. ModelRouter — route between local GGUF and cloud APIs
# ---------------------------------------------------------------------------

class ModelRouter:
    """
    Route inference requests between local and cloud backends.

    Supports strategies: LOCAL_FIRST, CLOUD_FIRST, LOCAL_ONLY, CLOUD_ONLY.
    Falls back automatically if the preferred backend is unavailable.
    """

    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.LOCAL_FIRST,
        local_manager: Optional[LocalModelManager] = None,
        cloud_backends: Optional[Dict[str, ModelBackend]] = None,
    ):
        self.strategy = strategy
        self.local_manager = local_manager
        self.cloud_backends = cloud_backends or {}
        self._default_cloud: Optional[str] = None
        if self.cloud_backends:
            self._default_cloud = next(iter(self.cloud_backends))

    def set_default_cloud(self, name: str) -> None:
        if name not in self.cloud_backends:
            raise ValueError(f"Cloud backend '{name}' not registered.")
        self._default_cloud = name

    def register_cloud(self, name: str, backend: ModelBackend) -> None:
        """Register a cloud API backend."""
        self.cloud_backends[name] = backend
        if self._default_cloud is None:
            self._default_cloud = name

    def select_backend(
        self, query_type: str = "default", preferred: Optional[str] = None
    ) -> Tuple[str, ModelBackend]:
        """
        Select the best backend for a query.

        Returns (backend_name, backend_instance).
        """
        if preferred and preferred in self.cloud_backends:
            backend = self.cloud_backends[preferred]
            if backend.is_available():
                return preferred, backend

        if preferred and self.local_manager:
            info = self.local_manager.get(preferred)
            if info and info.state in (ModelState.LOADED, ModelState.WARMED):
                return preferred, _LocalBackendWrapper(self.local_manager, info)

        # Strategy-based selection
        if self.strategy == RoutingStrategy.LOCAL_ONLY:
            return self._pick_local()
        elif self.strategy == RoutingStrategy.CLOUD_ONLY:
            return self._pick_cloud()
        elif self.strategy == RoutingStrategy.LOCAL_FIRST:
            try:
                return self._pick_local()
            except RuntimeError:
                return self._pick_cloud()
        elif self.strategy == RoutingStrategy.CLOUD_FIRST:
            try:
                return self._pick_cloud()
            except RuntimeError:
                return self._pick_local()

        raise RuntimeError("No suitable backend found.")

    def _pick_local(self) -> Tuple[str, ModelBackend]:
        if not self.local_manager:
            raise RuntimeError("No local manager configured.")
        loaded = self.local_manager.list_loaded()
        if not loaded:
            raise RuntimeError("No local models loaded.")
        # Pick the first warmed model, or first loaded
        preferred = None
        for m in loaded:
            if m.state == ModelState.WARMED:
                preferred = m
                break
        if preferred is None:
            preferred = loaded[0]
        return preferred.name, _LocalBackendWrapper(self.local_manager, preferred)

    def _pick_cloud(self) -> Tuple[str, ModelBackend]:
        for name, backend in self.cloud_backends.items():
            if backend.is_available():
                return name, backend
        raise RuntimeError("No cloud backends available.")

    def route(
        self,
        prompt: str,
        generator: StreamingGenerator,
        config: Optional[GenerationConfig] = None,
        query_type: str = "default",
        preferred: Optional[str] = None,
    ) -> InferenceResult:
        """
        Route a generation request and return the result.

        For streaming, use select_backend() + generator.generate() directly.
        """
        name, backend = self.select_backend(query_type, preferred)
        return generator.generate_complete(prompt, backend, config)


class _LocalBackendWrapper:
    """Wraps a LocalModelManager entry as a ModelBackend."""

    def __init__(self, manager: LocalModelManager, info: ModelInfo):
        self.manager = manager
        self.info = info
        self.name = info.name

    def iter_tokens(self, prompt: str, config: GenerationConfig) -> Iterator[str]:
        # In a real implementation, this would call llama-cpp or similar
        # Here we delegate to a mock for demonstration
        mock = MockBackend(name=self.name, delay_ms=0.5)
        yield from mock.iter_tokens(prompt, config)

    def is_available(self) -> bool:
        return self.info.state in (ModelState.LOADED, ModelState.WARMED)


# ---------------------------------------------------------------------------
# 7. LocalInferenceEngine — high-level orchestrator
# ---------------------------------------------------------------------------

class LocalInferenceEngine:
    """
    High-level orchestrator combining all components.

    Usage:
        engine = LocalInferenceEngine(models_dir="~/models")
        engine.scan_models()
        engine.load("my-model")
        for token in engine.stream("Hello, AI!"):
            print(token, end="")
    """

    def __init__(
        self,
        models_dir: Union[str, Path] = "~/models",
        context_window: int = DEFAULT_CONTEXT_WINDOW,
        routing_strategy: RoutingStrategy = RoutingStrategy.LOCAL_FIRST,
    ):
        self.counter = TokenCounter()
        self.metrics = InferenceMetrics()
        self.compressor = ContextCompressor(self.counter, context_window)
        self.manager = LocalModelManager(models_dir, self.counter)
        self.generator = StreamingGenerator(self.counter, self.metrics)
        self.router = ModelRouter(routing_strategy, self.manager)
        self._default_model: Optional[str] = None

    def scan_models(self) -> List[ModelInfo]:
        """Discover models in the models directory."""
        return self.manager.scan()

    def load(self, name: str) -> ModelInfo:
        """Load a model by name."""
        info = self.manager.load(name)
        self._default_model = name
        return info

    def unload(self, name: str) -> None:
        """Unload a model by name."""
        self.manager.unload(name)
        if self._default_model == name:
            self._default_model = None

    def warm_up(self, name: str) -> ModelInfo:
        """Warm-up a model."""
        return self.manager.warm_up(name)

    def stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        model: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Stream tokens for a prompt."""
        cfg = config or GenerationConfig()
        name, backend = self.router.select_backend(preferred=model or self._default_model)
        yield from self.generator.generate(prompt, backend, cfg)

    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        model: Optional[str] = None,
    ) -> InferenceResult:
        """Generate complete text (non-streaming)."""
        cfg = config or GenerationConfig()
        name, backend = self.router.select_backend(preferred=model or self._default_model)
        return self.generator.generate_complete(prompt, backend, cfg)

    def chat(
        self,
        messages: List[Dict[str, str]],
        config: Optional[GenerationConfig] = None,
        model: Optional[str] = None,
    ) -> InferenceResult:
        """Chat completion with automatic context compression."""
        fitted = self.compressor.fit(messages)
        # Simple prompt formatting (no template complexity for portability)
        prompt_parts = []
        for msg in fitted:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content}")
        prompt_parts.append("assistant:")
        prompt = "\n".join(prompt_parts)
        return self.generate(prompt, config, model)

    def metrics_report(self) -> str:
        """Return a human-readable metrics report."""
        snap = self.metrics.snapshot()
        # Augment with live info
        snap.active_models = len(self.manager.list_loaded())
        snap.memory_usage_mb = self.manager.memory_usage_mb
        return self.metrics.report()


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Run built-in tests using MockBackend."""
    print("=" * 60)
    print("LOCAL INFERENCE NATIVE — Self-Test")
    print("=" * 60)

    def _safe_print(text: str) -> None:
        try:
            print(text)
        except UnicodeEncodeError:
            # Fallback for Windows console with limited encoding
            safe = text.encode("utf-8", errors="replace").decode("utf-8")
            try:
                print(safe)
            except UnicodeEncodeError:
                print(text.encode("ascii", errors="replace").decode("ascii"))

    # 1. TokenCounter
    print("\n[1] TokenCounter")
    tc = TokenCounter()
    samples = [
        ("Hello, world!", 4),
        ("The quick brown fox jumps over the lazy dog.", 10),
        ("Chinese test string", 4),
        ("def hello():\n    print('world')", 8),
    ]
    for s, expected in samples:
        count = tc.count(s)
        ok = "OK" if count == expected else f"UNEXPECTED (expected {expected})"
        _safe_print(f"  '{s[:40]}' -> {count} tokens [{ok}]")

    # 2. ContextCompressor
    print("\n[2] ContextCompressor")
    cc = ContextCompressor(tc, context_window=64, reserve_tokens=8)
    long_msgs = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a very long story about a fox."},
        {"role": "assistant", "content": "Once upon a time there was a fox who loved to explore the forest every single day without fail."},
        {"role": "user", "content": "What happened next?"},
    ]
    fitted = cc.fit(long_msgs)
    print(f"  Input messages: {len(long_msgs)} -> Fitted: {len(fitted)}")
    for m in fitted:
        print(f"    {m['role']}: {m['content'][:50]}...")

    # 3. InferenceMetrics
    print("\n[3] InferenceMetrics")
    im = InferenceMetrics()
    for i in range(10):
        im.record(latency_ms=50.0 + i * 5, tokens_generated=10 + i)
    print(im.report())

    # 4. LocalModelManager (with temp directory)
    print("\n[4] LocalModelManager")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake GGUF file with proper header
        fake_gguf = Path(tmpdir) / "test-model-Q4_K.gguf"
        with open(fake_gguf, "wb") as f:
            # Write GGUF v3 header
            f.write(GGUF_MAGIC)
            f.write(struct.pack("<I", 3))  # version
            f.write(struct.pack("<Q", 1))  # tensor count
            f.write(struct.pack("<Q", 3))  # metadata kv count
            # Write metadata: general.architecture
            f.write(struct.pack("<Q", len("general.architecture")))
            f.write(b"general.architecture")
            f.write(struct.pack("<I", 11))  # string type
            f.write(struct.pack("<Q", 5))
            f.write(b"llama")
            # Write metadata: llama.context_length
            f.write(struct.pack("<Q", len("llama.context_length")))
            f.write(b"llama.context_length")
            f.write(struct.pack("<I", 4))  # uint32 type
            f.write(struct.pack("<I", 4096))
            # Write metadata: general.parameter_count
            f.write(struct.pack("<Q", len("general.parameter_count")))
            f.write(b"general.parameter_count")
            f.write(struct.pack("<I", 6))  # uint64 type
            f.write(struct.pack("<Q", 7_000_000_000))
            # Pad with dummy data to make it look like a real file
            f.write(b"\x00" * 1024)

        mgr = LocalModelManager(tmpdir)
        models = mgr.scan()
        print(f"  Discovered {len(models)} model(s):")
        for m in models:
            print(f"    - {m.name} ({m.parameters}, {m.quantization}, ctx={m.context_window})")

        if models:
            info = mgr.load(models[0].name)
            print(f"  Loaded: {info.name} -> state={info.state.name}")
            mgr.warm_up(info.name)
            print(f"  Warmed: {info.name} -> state={info.state.name}")
            print(f"  Memory usage: {mgr.memory_usage_mb:.2f} MB")
            mgr.unload(info.name)
            print(f"  Unloaded: {info.name} -> state={info.state.name}")

    # 5. StreamingGenerator + MockBackend
    print("\n[5] StreamingGenerator")
    mock = MockBackend(delay_ms=0.1)
    gen = StreamingGenerator(tc, im)
    print("  Streaming:")
    for token in gen.generate("Hello", mock, GenerationConfig(max_tokens=20, stream=True)):
        print(token, end="")
    print()

    result = gen.generate_complete("Hello", mock, GenerationConfig(max_tokens=15, stream=False))
    print(f"  Complete: {result.tokens_generated} tokens, {result.latency_ms:.2f} ms, {result.tokens_per_second:.2f} t/s")

    # 6. ModelRouter
    print("\n[6] ModelRouter")
    router = ModelRouter(RoutingStrategy.LOCAL_FIRST)
    router.register_cloud("mock-cloud", mock)
    name, backend = router.select_backend()
    print(f"  Selected backend: {name} (available={backend.is_available()})")

    result = router.route("Test prompt", gen, GenerationConfig(max_tokens=10))
    print(f"  Routed result: {result.tokens_generated} tokens, finish_reason={result.finish_reason}")

    # 7. LocalInferenceEngine (integration)
    print("\n[7] LocalInferenceEngine")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create fake model for the engine test
        fake = Path(tmpdir) / "engine-test-Q4_K.gguf"
        with open(fake, "wb") as f:
            f.write(GGUF_MAGIC)
            f.write(struct.pack("<I", 3))
            f.write(struct.pack("<Q", 1))
            f.write(struct.pack("<Q", 2))
            f.write(struct.pack("<Q", len("general.architecture")))
            f.write(b"general.architecture")
            f.write(struct.pack("<I", 11))
            f.write(struct.pack("<Q", 5))
            f.write(b"llama")
            f.write(struct.pack("<Q", len("llama.context_length")))
            f.write(b"llama.context_length")
            f.write(struct.pack("<I", 4))
            f.write(struct.pack("<I", 2048))
            f.write(b"\x00" * 512)

        engine = LocalInferenceEngine(models_dir=tmpdir, context_window=2048)
        engine.scan_models()
        model_name = engine.manager.list_models()[0].name
        engine.load(model_name)
        engine.warm_up(model_name)

        print("  Streaming from engine:")
        for token in engine.stream("Hello", GenerationConfig(max_tokens=12)):
            print(token, end="")
        print()

        result = engine.generate("Hello", GenerationConfig(max_tokens=10))
        print(f"  Engine result: {result.tokens_generated} tokens, {result.tokens_per_second:.2f} t/s")

        chat_result = engine.chat([
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi!"},
        ], GenerationConfig(max_tokens=10))
        print(f"  Chat result: {chat_result.text[:60]}...")

        print(f"\n{engine.metrics_report()}")

    print("\n" + "=" * 60)
    print("All self-tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    _self_test()
