#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Inference Backend (Layer 10 Extension)
GGUF Model Loader + Quantized Tensor Operations + Distributed Inference Stub
================================================================================
Zero-dependency pure-Python inference backend with mmap-style tensor views,
Q4/Q8 quantization stubs, and exo-style device mesh partitioning.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import math
import mmap
import os
import struct
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union


# =============================================================================
# Constants
# =============================================================================
GGUF_MAGIC = b"GGUF"
GGUF_VERSION = 3
DEFAULT_MAX_SEQ_LEN = 4096
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.9
DEFAULT_TOP_K = 40


# =============================================================================
# Quantization Types
# =============================================================================
class QuantType(Enum):
    F32 = 0
    F16 = 1
    Q4_0 = 2
    Q4_1 = 3
    Q5_0 = 6
    Q5_1 = 7
    Q8_0 = 8
    Q8_1 = 9


# =============================================================================
# Tensor Views
# =============================================================================
@dataclass
class TensorShape:
    dims: Tuple[int, ...]

    @property
    def numel(self) -> int:
        n = 1
        for d in self.dims:
            n *= d
        return n

    @property
    def nbytes(self, dtype: QuantType = QuantType.F32) -> int:
        el_size = {QuantType.F32: 4, QuantType.F16: 2, QuantType.Q4_0: 2, QuantType.Q8_0: 1}.get(dtype, 4)
        return self.numel * el_size


@dataclass
class TensorView:
    """Memory-mapped tensor slice — no copy until dequantize."""
    name: str
    shape: TensorShape
    dtype: QuantType
    offset: int
    length: int
    data: Optional[bytes] = None  # Populated on read

    def dequantize_to_f32(self) -> List[float]:
        if self.data is None:
            return []
        if self.dtype == QuantType.F32:
            count = len(self.data) // 4
            return list(struct.unpack(f"<{count}f", self.data))
        elif self.dtype == QuantType.F16:
            count = len(self.data) // 2
            # Convert f16 to f32 via simple scaling (real impl uses numpy)
            half_words = struct.unpack(f"<{count}H", self.data)
            return [self._half_to_float(h) for h in half_words]
        elif self.dtype == QuantType.Q4_0:
            return self._deq_q4_0()
        elif self.dtype == QuantType.Q8_0:
            return self._deq_q8_0()
        return [0.0] * self.shape.numel

    def _half_to_float(self, h: int) -> float:
        # Very rough approximation for pure-python
        if h == 0:
            return 0.0
        sign = -1.0 if (h >> 15) else 1.0
        exp = ((h >> 10) & 0x1F) - 15
        frac = (h & 0x3FF) / 1024.0 + 1.0
        return sign * frac * (2.0 ** exp)

    def _deq_q4_0(self) -> List[float]:
        # Q4_0: each block of 32 has 1 f16 scale + 32 nibbles
        out: List[float] = []
        i = 0
        while i < len(self.data):
            scale = self._half_to_float(struct.unpack("<H", self.data[i:i+2])[0])
            i += 2
            qs = self.data[i:i+16]
            i += 16
            for b in qs:
                out.append(scale * ((b & 0x0F) - 8))
                out.append(scale * ((b >> 4) - 8))
        return out

    def _deq_q8_0(self) -> List[float]:
        # Q8_0: each block of 32 has 1 f16 scale + 32 int8 values
        out: List[float] = []
        i = 0
        while i < len(self.data):
            scale = self._half_to_float(struct.unpack("<H", self.data[i:i+2])[0])
            i += 2
            for b in self.data[i:i+32]:
                out.append(scale * (b - 128) / 127.0)
            i += 32
        return out


# =============================================================================
# GGUF Reader
# =============================================================================
class GGUFReader:
    """Parse GGUF metadata and tensor info without loading data."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.metadata: Dict[str, Any] = {}
        self.tensors: Dict[str, TensorView] = {}
        self._header_parsed = False

    def parse_header(self) -> bool:
        with open(self.path, "rb") as f:
            magic = f.read(4)
            if magic != GGUF_MAGIC:
                return False
            version = struct.unpack("<I", f.read(4))[0]
            if version > GGUF_VERSION:
                return False
            tensor_count = struct.unpack("<Q", f.read(8))[0]
            metadata_kv_count = struct.unpack("<Q", f.read(8))[0]
            # Read metadata KV pairs
            for _ in range(metadata_kv_count):
                key_len = struct.unpack("<Q", f.read(8))[0]
                key = f.read(key_len).decode("utf-8")
                val_type = struct.unpack("<I", f.read(4))[0]
                val = self._read_value(f, val_type)
                self.metadata[key] = val
            # Read tensor info
            for _ in range(tensor_count):
                name_len = struct.unpack("<Q", f.read(8))[0]
                name = f.read(name_len).decode("utf-8")
                n_dims = struct.unpack("<I", f.read(4))[0]
                dims = struct.unpack(f"<{n_dims}Q", f.read(8 * n_dims))
                dtype = struct.unpack("<I", f.read(4))[0]
                offset = struct.unpack("<Q", f.read(8))[0]
                # Align offset to 32
                data_offset = (offset + 31) & ~31
                shape = TensorShape(dims=dims)
                self.tensors[name] = TensorView(
                    name=name,
                    shape=shape,
                    dtype=QuantType(dtype),
                    offset=data_offset,
                    length=shape.nbytes(QuantType(dtype)),
                )
            self._data_start = f.tell()
            self._header_parsed = True
        return True

    def _read_value(self, f, val_type: int) -> Any:
        # Simplified: only handle basic types
        if val_type == 0:  # UINT8
            return struct.unpack("<B", f.read(1))[0]
        elif val_type == 1:  # INT8
            return struct.unpack("<b", f.read(1))[0]
        elif val_type == 2:  # UINT16
            return struct.unpack("<H", f.read(2))[0]
        elif val_type == 3:  # INT16
            return struct.unpack("<h", f.read(2))[0]
        elif val_type == 4:  # UINT32
            return struct.unpack("<I", f.read(4))[0]
        elif val_type == 5:  # INT32
            return struct.unpack("<i", f.read(4))[0]
        elif val_type == 6:  # FLOAT32
            return struct.unpack("<f", f.read(4))[0]
        elif val_type == 7:  # UINT64
            return struct.unpack("<Q", f.read(8))[0]
        elif val_type == 8:  # INT64
            return struct.unpack("<q", f.read(8))[0]
        elif val_type == 9:  # FLOAT64
            return struct.unpack("<d", f.read(8))[0]
        elif val_type == 10:  # BOOL
            return struct.unpack("<B", f.read(1))[0] != 0
        elif val_type == 11:  # STRING
            slen = struct.unpack("<Q", f.read(8))[0]
            return f.read(slen).decode("utf-8")
        elif val_type == 12:  # ARRAY
            arr_type = struct.unpack("<I", f.read(4))[0]
            arr_len = struct.unpack("<Q", f.read(8))[0]
            return [self._read_value(f, arr_type) for _ in range(arr_len)]
        return None

    def load_tensor_data(self, name: str) -> Optional[TensorView]:
        tv = self.tensors.get(name)
        if tv is None or not self._header_parsed:
            return None
        with open(self.path, "rb") as f:
            f.seek(self._data_start + tv.offset)
            tv.data = f.read(tv.length)
        return tv


# =============================================================================
# KV Cache Manager (PagedAttention-style)
# =============================================================================
class KVCacheBlock:
    def __init__(self, block_size: int, head_dim: int, num_heads: int) -> None:
        self.block_size = block_size
        self.head_dim = head_dim
        self.num_heads = num_heads
        # Flat: [block_size, num_heads, head_dim]
        self.k = [[[0.0] * head_dim for _ in range(num_heads)] for _ in range(block_size)]
        self.v = [[[0.0] * head_dim for _ in range(num_heads)] for _ in range(block_size)]
        self.ref_count = 0


class PagedKVCache:
    """vLLM-style paged KV cache for efficient attention."""

    def __init__(self, num_blocks: int = 256, block_size: int = 16, num_heads: int = 32, head_dim: int = 128) -> None:
        self.num_blocks = num_blocks
        self.block_size = block_size
        self.num_heads = num_heads
        self.head_dim = head_dim
        self._free_blocks: List[int] = list(range(num_blocks))
        self._blocks: Dict[int, KVCacheBlock] = {}
        self._seq_blocks: Dict[str, List[int]] = {}
        self._lock = threading.Lock()

    def allocate(self, seq_id: str, num_tokens: int) -> List[int]:
        needed = (num_tokens + self.block_size - 1) // self.block_size
        with self._lock:
            if len(self._free_blocks) < needed:
                return []
            assigned = self._free_blocks[:needed]
            self._free_blocks = self._free_blocks[needed:]
            for b in assigned:
                self._blocks[b] = KVCacheBlock(self.block_size, self.head_dim, self.num_heads)
                self._blocks[b].ref_count = 1
            self._seq_blocks[seq_id] = assigned
            return assigned

    def get_block(self, block_id: int) -> Optional[KVCacheBlock]:
        return self._blocks.get(block_id)

    def free(self, seq_id: str) -> None:
        with self._lock:
            for b in self._seq_blocks.get(seq_id, []):
                if b in self._blocks:
                    self._blocks[b].ref_count -= 1
                    if self._blocks[b].ref_count <= 0:
                        del self._blocks[b]
                        self._free_blocks.append(b)
            self._seq_blocks.pop(seq_id, None)

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "total_blocks": self.num_blocks,
                "free_blocks": len(self._free_blocks),
                "used_blocks": len(self._blocks),
                "seqs": len(self._seq_blocks),
            }


# =============================================================================
# Sampler
# =============================================================================
class Sampler:
    """Top-k / top-p / temperature sampling in pure Python."""

    @staticmethod
    def softmax(logits: List[float], temperature: float = 1.0) -> List[float]:
        if temperature == 0:
            temperature = 1e-8
        scaled = [z / temperature for z in logits]
        max_z = max(scaled)
        exps = [math.exp(z - max_z) for z in scaled]
        s = sum(exps)
        return [e / s for e in exps]

    @staticmethod
    def top_k(probs: List[float], k: int) -> List[Tuple[int, float]]:
        indexed = sorted(enumerate(probs), key=lambda x: x[1], reverse=True)
        return indexed[:k]

    @staticmethod
    def top_p(probs: List[float], p: float) -> List[Tuple[int, float]]:
        indexed = sorted(enumerate(probs), key=lambda x: x[1], reverse=True)
        cumsum = 0.0
        out = []
        for idx, pr in indexed:
            cumsum += pr
            out.append((idx, pr))
            if cumsum >= p:
                break
        return out

    @staticmethod
    def sample(logits: List[float], temperature: float = 0.7, top_k: int = 40, top_p: float = 0.9) -> int:
        probs = Sampler.softmax(logits, temperature)
        candidates = Sampler.top_k(probs, top_k)
        p_sum = sum(p for _, p in candidates)
        if p_sum < 0.99:
            candidates = Sampler.top_p(probs, top_p)
        # Weighted random choice
        total = sum(p for _, p in candidates)
        r = total * (hashlib.sha256(str(time.time()).encode()).hexdigest()[:8])
        # Use time-based pseudo-random
        import random
        r = random.random() * total
        cum = 0.0
        for idx, pr in candidates:
            cum += pr
            if r <= cum:
                return idx
        return candidates[-1][0] if candidates else 0


# =============================================================================
# Tokenizer (BPE stub)
# =============================================================================
class BPETokenizerStub:
    """Placeholder BPE tokenizer — real one needs vocab file."""

    def __init__(self, vocab_path: Optional[str] = None) -> None:
        self.vocab: Dict[str, int] = {}
        self.inv_vocab: Dict[int, str] = {}
        if vocab_path and os.path.exists(vocab_path):
            self._load(vocab_path)
        else:
            self._init_default()

    def _init_default(self) -> None:
        # Minimal fallback vocab
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !?.,;:-_'\"()[]{}\n"
        for i, c in enumerate(chars):
            self.vocab[c] = i
            self.inv_vocab[i] = c
        self.vocab["<|endoftext|>"] = len(chars)
        self.inv_vocab[len(chars)] = "<|endoftext|>"
        self.vocab["<|padding|>"] = len(chars) + 1
        self.inv_vocab[len(chars) + 1] = "<|padding|>"

    def _load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                tok = line.strip()
                if tok:
                    self.vocab[tok] = i
                    self.inv_vocab[i] = tok

    def encode(self, text: str) -> List[int]:
        # Naive character-level encoding
        return [self.vocab.get(c, self.vocab.get("<|endoftext|>", 0)) for c in text]

    def decode(self, tokens: List[int]) -> str:
        return "".join(self.inv_vocab.get(t, "?") for t in tokens)

    @property
    def vocab_size(self) -> int:
        return len(self.vocab)

    @property
    def eos_token_id(self) -> int:
        return self.vocab.get("<|endoftext|>", 0)


# =============================================================================
# Device Mesh (exo-style distributed)
# =============================================================================
class DeviceMesh:
    """Partition model layers across multiple devices/nodes."""

    def __init__(self, devices: List[Tuple[str, int]]) -> None:
        """devices: list of (host, port) for each worker node."""
        self.devices = devices
        self._layers_per_device: Dict[str, List[int]] = {}

    def partition(self, num_layers: int) -> Dict[str, List[int]]:
        n = len(self.devices)
        base = num_layers // n
        extra = num_layers % n
        assigned = 0
        mapping: Dict[str, List[int]] = {}
        for dev in self.devices:
            count = base + (1 if extra > 0 else 0)
            mapping[f"{dev[0]}:{dev[1]}"] = list(range(assigned, assigned + count))
            assigned += count
            extra -= 1
        self._layers_per_device = mapping
        return mapping

    def get_device_for_layer(self, layer_idx: int) -> str:
        for dev, layers in self._layers_per_device.items():
            if layer_idx in layers:
                return dev
        return "localhost:0"


# =============================================================================
# Model State
# =============================================================================
@dataclass
class ModelState:
    name: str
    path: str
    num_layers: int
    num_heads: int
    head_dim: int
    hidden_dim: int
    vocab_size: int
    max_seq_len: int
    quant_type: QuantType
    reader: Optional[GGUFReader] = None
    kv_cache: Optional[PagedKVCache] = None
    tokenizer: Optional[BPETokenizerStub] = None


# =============================================================================
# Inference Engine
# =============================================================================
class InferenceEngine:
    """End-to-end inference with model loading, caching, and generation."""

    def __init__(self) -> None:
        self.models: Dict[str, ModelState] = {}
        self._lock = threading.Lock()
        self._running = False

    def load(self, name: str, path: str, tokenizer_path: Optional[str] = None) -> bool:
        reader = GGUFReader(path)
        if not reader.parse_header():
            return False
        state = ModelState(
            name=name,
            path=path,
            num_layers=reader.metadata.get("llama.block_count", reader.metadata.get("general.architecture.block_count", 32)),
            num_heads=reader.metadata.get("llama.attention.head_count", 32),
            head_dim=reader.metadata.get("llama.attention.head_count_k", 128),
            hidden_dim=reader.metadata.get("llama.embedding_length", 4096),
            vocab_size=reader.metadata.get("llama.vocab_size", 32000),
            max_seq_len=reader.metadata.get("llama.context_length", DEFAULT_MAX_SEQ_LEN),
            quant_type=QuantType.Q4_0,
            reader=reader,
            kv_cache=PagedKVCache(num_blocks=512),
            tokenizer=BPETokenizerStub(tokenizer_path),
        )
        with self._lock:
            self.models[name] = state
        return True

    def unload(self, name: str) -> bool:
        with self._lock:
            return self.models.pop(name, None) is not None

    def generate(self, model_name: str, prompt: str, max_tokens: int = 64, **kwargs: Any) -> Iterator[str]:
        model = self.models.get(model_name)
        if not model or not model.tokenizer:
            yield "[ERROR: model not loaded]"
            return
        tokens = model.tokenizer.encode(prompt)
        temp = kwargs.get("temperature", DEFAULT_TEMPERATURE)
        top_k = kwargs.get("top_k", DEFAULT_TOP_K)
        top_p = kwargs.get("top_p", DEFAULT_TOP_P)
        cache_ids = model.kv_cache.allocate(model_name, len(tokens)) if model.kv_cache else []
        generated: List[int] = []
        for i in range(max_tokens):
            # Stub: random logits from token history hash
            seed = hashlib.sha256(bytes(tokens + generated)).hexdigest()
            logits = [(int(seed[j:j+2], 16) / 255.0 - 0.5) * 2.0 for j in range(0, 64, 2)]
            if len(logits) < model.vocab_size:
                logits += [0.0] * (model.vocab_size - len(logits))
            next_tok = Sampler.sample(logits[:model.vocab_size], temp, top_k, top_p)
            if next_tok == model.tokenizer.eos_token_id:
                break
            generated.append(next_tok)
            yield model.tokenizer.decode([next_tok])
        if model.kv_cache:
            model.kv_cache.free(model_name)

    def benchmark(self, model_name: str, prompt: str, max_tokens: int = 128) -> Dict[str, Any]:
        t0 = time.perf_counter()
        count = 0
        for _ in self.generate(model_name, prompt, max_tokens):
            count += 1
        dur = time.perf_counter() - t0
        return {
            "model": model_name,
            "tokens_generated": count,
            "duration_sec": dur,
            "tok_per_sec": count / dur if dur > 0 else 0,
        }

    def shutdown(self) -> None:
        self._running = False
        with self._lock:
            for m in self.models.values():
                if m.kv_cache:
                    m.kv_cache.free(m.name)
            self.models.clear()

    def __enter__(self) -> InferenceEngine:
        self._running = True
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown()


# =============================================================================
# Inference Kernel Bridge
# =============================================================================
class InferenceKernelBridge:
    def __init__(self, engine: InferenceEngine, event_bus: Any = None) -> None:
        self.engine = engine
        self.bus = event_bus

    def load_and_notify(self, name: str, path: str) -> bool:
        ok = self.engine.load(name, path)
        if ok and self.bus:
            self.bus.publish("llm.loaded", {"model": name, "path": path})
        return ok

    def generate_and_notify(self, model: str, prompt: str, **kwargs: Any) -> str:
        out = ""
        for chunk in self.engine.generate(model, prompt, **kwargs):
            out += chunk
            if self.bus:
                self.bus.publish("llm.token", {"model": model, "token": chunk})
        if self.bus:
            self.bus.publish("llm.completed", {"model": model, "output": out})
        return out


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Inference Backend Demo")
    print("=" * 60)
    engine = InferenceEngine()
    # Create a dummy GGUF file for demo
    dummy_path = "/tmp/magnatrix_dummy.gguf"
    _create_dummy_gguf(dummy_path)
    ok = engine.load("demo-model", dummy_path)
    print(f"Load dummy model: {ok}")
    if ok:
        print("Generating 10 tokens...")
        out = ""
        for tok in engine.generate("demo-model", "Hello world", max_tokens=10):
            out += tok
        print(f"Output: {out}")
        stats = engine.benchmark("demo-model", "Test", max_tokens=20)
        print(f"Benchmark: {stats}")
    engine.shutdown()
    print("Demo complete.")


def _create_dummy_gguf(path: str) -> None:
    with open(path, "wb") as f:
        f.write(GGUF_MAGIC)
        f.write(struct.pack("<I", GGUF_VERSION))
        f.write(struct.pack("<Q", 1))  # tensor_count
        f.write(struct.pack("<Q", 3))  # metadata_kv_count
        # KV 1: general.architecture
        _write_str(f, "general.architecture")
        f.write(struct.pack("<I", 11))  # string type
        _write_str(f, "llama")
        # KV 2: llama.block_count
        _write_str(f, "llama.block_count")
        f.write(struct.pack("<I", 5))  # int32 type
        f.write(struct.pack("<i", 32))
        # KV 3: llama.context_length
        _write_str(f, "llama.context_length")
        f.write(struct.pack("<I", 5))
        f.write(struct.pack("<i", 4096))
        # Tensor info
        _write_str(f, "token_embd.weight")
        f.write(struct.pack("<I", 2))  # n_dims
        f.write(struct.pack("<QQ", 32000, 4096))
        f.write(struct.pack("<I", QuantType.Q4_0.value))
        f.write(struct.pack("<Q", 0))  # offset
        # Pad to 32 alignment and write dummy data
        pos = f.tell()
        pad = (32 - pos % 32) % 32
        f.write(b"\x00" * pad)
        # Dummy Q4_0 block: 2 bytes scale + 16 bytes weights per 32 elements
        blocks = (32000 * 4096) // 32
        for _ in range(blocks):
            f.write(struct.pack("<H", 0x3C00))  # scale = 1.0 in half
            f.write(b"\x00" * 16)


def _write_str(f, s: str) -> None:
    b = s.encode("utf-8")
    f.write(struct.pack("<Q", len(b)))
    f.write(b)


if __name__ == "__main__":
    run_demo()
