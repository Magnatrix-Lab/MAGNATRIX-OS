#!/usr/bin/env python3
"""
ai/gguf_loader_native.py
==========================
Layer 10 Extension — GGUF Model Loader

Pure-Python GGUF format reader (version 3 compatible).
Can load metadata and tensor info from .gguf files.
Integration point for llama.cpp / llama-cpp-python.

Usage:
  from ai.gguf_loader_native import GGUFLader
  model = GGUFLoader("/var/lib/magnatrix/models/llama-3-8b.gguf")
  model.load_tensors()  # Read tensor shapes and offsets
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import BinaryIO, Dict, List, Optional, Tuple, Any


GGUF_MAGIC = b"GGUF"
GGUF_VERSION = 3

GGML_TYPES: Dict[int, str] = {
    0: "GGML_TYPE_F32",
    1: "GGML_TYPE_F16",
    2: "GGML_TYPE_Q4_0",
    3: "GGML_TYPE_Q4_1",
    6: "GGML_TYPE_Q5_0",
    7: "GGML_TYPE_Q5_1",
    8: "GGML_TYPE_Q8_0",
    9: "GGML_TYPE_Q8_1",
    10: "GGML_TYPE_Q2_K",
    11: "GGML_TYPE_Q3_K",
    12: "GGML_TYPE_Q4_K",
    13: "GGML_TYPE_Q5_K",
    14: "GGML_TYPE_Q6_K",
    15: "GGML_TYPE_Q8_K",
    16: "GGML_TYPE_IQ2_XXS",
    17: "GGML_TYPE_IQ2_XS",
    18: "GGML_TYPE_IQ3_XXS",
    19: "GGML_TYPE_IQ3_S",
    20: "GGML_TYPE_IQ4_NL",
    21: "GGML_TYPE_IQ4_XS",
    22: "GGML_TYPE_I8",
    23: "GGML_TYPE_I16",
    24: "GGML_TYPE_I32",
    25: "GGML_TYPE_I64",
    26: "GGML_TYPE_F64",
    27: "GGML_TYPE_IQ1_M",
}


@dataclass
class GGUFMetadata:
    architecture: str = "unknown"
    context_length: int = 4096
    embedding_length: int = 4096
    block_count: int = 32
    feed_forward_length: int = 14336
    attention_head_count: int = 32
    attention_head_count_kv: int = 8
    rope_freq_base: float = 500000.0
    vocabulary_size: int = 128256
    quantization_version: int = 2
    file_type: str = "unknown"
    raw: Dict[str, Any] = None

    def __post_init__(self):
        if self.raw is None:
            self.raw = {}


@dataclass
class GGUFTensor:
    name: str
    n_dims: int
    dimensions: Tuple[int, ...]
    ggml_type: int
    offset: int
    size: int
    type_name: str


class GGUFLoader:
    """Read GGUF file format (llama.cpp model weights)."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.metadata = GGUFMetadata()
        self.tensors: List[GGUFTensor] = []
        self._file: Optional[BinaryIO] = None
        self._tensor_data_offset: int = 0

    def _read_val(self, f: BinaryIO, val_type: int) -> Any:
        """Read a single GGUF value."""
        if val_type == 0:   # UINT8
            return struct.unpack("<B", f.read(1))[0]
        elif val_type == 1: # INT8
            return struct.unpack("<b", f.read(1))[0]
        elif val_type == 2: # UINT16
            return struct.unpack("<H", f.read(2))[0]
        elif val_type == 3: # INT16
            return struct.unpack("<h", f.read(2))[0]
        elif val_type == 4: # UINT32
            return struct.unpack("<I", f.read(4))[0]
        elif val_type == 5: # INT32
            return struct.unpack("<i", f.read(4))[0]
        elif val_type == 6: # FLOAT32
            return struct.unpack("<f", f.read(4))[0]
        elif val_type == 7: # BOOL
            return struct.unpack("<?", f.read(1))[0]
        elif val_type == 8: # STRING
            length = struct.unpack("<I", f.read(4))[0]
            return f.read(length).decode("utf-8")
        elif val_type == 9: # ARRAY
            elem_type = struct.unpack("<I", f.read(4))[0]
            length = struct.unpack("<I", f.read(4))[0]
            return [self._read_val(f, elem_type) for _ in range(length)]
        elif val_type == 10: # UINT64
            return struct.unpack("<Q", f.read(8))[0]
        elif val_type == 11: # INT64
            return struct.unpack("<q", f.read(8))[0]
        elif val_type == 12: # FLOAT64
            return struct.unpack("<d", f.read(8))[0]
        else:
            raise ValueError(f"Unknown GGUF value type: {val_type}")

    def load_metadata(self) -> GGUFMetadata:
        """Read GGUF header and metadata."""
        with open(self.filepath, "rb") as f:
            magic = f.read(4)
            if magic != GGUF_MAGIC:
                raise ValueError(f"Invalid GGUF magic: {magic}")
            version = struct.unpack("<I", f.read(4))[0]
            if version > GGUF_VERSION:
                raise ValueError(f"Unsupported GGUF version: {version}")
            tensor_count = struct.unpack("<Q", f.read(8))[0]
            metadata_kv_count = struct.unpack("<Q", f.read(8))[0]

            raw_meta: Dict[str, Any] = {}
            for _ in range(metadata_kv_count):
                key_len = struct.unpack("<I", f.read(4))[0]
                key = f.read(key_len).decode("utf-8")
                val_type = struct.unpack("<I", f.read(4))[0]
                value = self._read_val(f, val_type)
                raw_meta[key] = value

            self.metadata = GGUFMetadata(
                architecture=raw_meta.get("general.architecture", "unknown"),
                context_length=raw_meta.get(f"{raw_meta.get('general.architecture', 'llama')}.context_length", 4096),
                embedding_length=raw_meta.get(f"{raw_meta.get('general.architecture', 'llama')}.embedding_length", 4096),
                block_count=raw_meta.get(f"{raw_meta.get('general.architecture', 'llama')}.block_count", 32),
                feed_forward_length=raw_meta.get(f"{raw_meta.get('general.architecture', 'llama')}.feed_forward_length", 14336),
                attention_head_count=raw_meta.get(f"{raw_meta.get('general.architecture', 'llama')}.attention.head_count", 32),
                attention_head_count_kv=raw_meta.get(f"{raw_meta.get('general.architecture', 'llama')}.attention.head_count_kv", 8),
                rope_freq_base=raw_meta.get(f"{raw_meta.get('general.architecture', 'llama')}.rope.freq_base", 500000.0),
                vocabulary_size=raw_meta.get("tokenizer.ggml.tokens", [])
                if isinstance(raw_meta.get("tokenizer.ggml.tokens"), list)
                else raw_meta.get(f"{raw_meta.get('general.architecture', 'llama')}.vocab_size", 128256),
                quantization_version=raw_meta.get("general.quantization_version", 2),
                file_type=GGML_TYPES.get(raw_meta.get("general.file_type", 0), "unknown"),
                raw=raw_meta,
            )
            self._tensor_data_offset = f.tell()
        return self.metadata

    def load_tensors(self) -> List[GGUFTensor]:
        """Read tensor info (shapes, offsets, types)."""
        with open(self.filepath, "rb") as f:
            # Re-read header to get to tensor section
            f.read(4)  # magic
            f.read(4)  # version
            tensor_count = struct.unpack("<Q", f.read(8))[0]
            metadata_kv_count = struct.unpack("<Q", f.read(8))[0]
            # Skip metadata
            for _ in range(metadata_kv_count):
                key_len = struct.unpack("<I", f.read(4))[0]
                f.seek(key_len, os.SEEK_CUR)
                val_type = struct.unpack("<I", f.read(4))[0]
                self._skip_val(f, val_type)

            tensor_offset = f.tell()
            for _ in range(tensor_count):
                name_len = struct.unpack("<I", f.read(4))[0]
                name = f.read(name_len).decode("utf-8")
                n_dims = struct.unpack("<I", f.read(4))[0]
                dimensions = struct.unpack(f"<{n_dims}Q", f.read(n_dims * 8))
                ggml_type = struct.unpack("<I", f.read(4))[0]
                offset = struct.unpack("<Q", f.read(8))[0]
                # Calculate size (approximate)
                nelements = 1
                for d in dimensions:
                    nelements *= d
                type_name = GGML_TYPES.get(ggml_type, "UNKNOWN")
                size = nelements * 4  # Approximate, real size depends on quantization
                self.tensors.append(GGUFTensor(
                    name=name, n_dims=n_dims, dimensions=dimensions,
                    ggml_type=ggml_type, offset=tensor_offset + offset,
                    size=size, type_name=type_name,
                ))
        return self.tensors

    def _skip_val(self, f: BinaryIO, val_type: int) -> None:
        """Skip a value without reading it."""
        if val_type == 0:   f.read(1)
        elif val_type == 1: f.read(1)
        elif val_type == 2: f.read(2)
        elif val_type == 3: f.read(2)
        elif val_type == 4: f.read(4)
        elif val_type == 5: f.read(4)
        elif val_type == 6: f.read(4)
        elif val_type == 7: f.read(1)
        elif val_type == 8:
            length = struct.unpack("<I", f.read(4))[0]
            f.seek(length, os.SEEK_CUR)
        elif val_type == 9:
            elem_type = struct.unpack("<I", f.read(4))[0]
            length = struct.unpack("<I", f.read(4))[0]
            for _ in range(length):
                self._skip_val(f, elem_type)
        elif val_type == 10: f.read(8)
        elif val_type == 11: f.read(8)
        elif val_type == 12: f.read(8)

    def summary(self) -> str:
        m = self.metadata
        lines = [
            f"Architecture: {m.architecture}",
            f"Context Length: {m.context_length}",
            f"Embedding Length: {m.embedding_length}",
            f"Block Count: {m.block_count}",
            f"FF Length: {m.feed_forward_length}",
            f"Attention Heads: {m.attention_head_count} (KV: {m.attention_head_count_kv})",
            f"RoPE Base: {m.rope_freq_base}",
            f"Vocab Size: {m.vocabulary_size if isinstance(m.vocabulary_size, int) else len(m.vocabulary_size)}",
            f"Quantization: {m.file_type}",
            f"Tensors: {len(self.tensors)}",
        ]
        return "\n".join(lines)


import os


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  GGUF LOADER")
    print("=" * 60)
    print("GGUF format reader ready. Usage:")
    print("  model = GGUFLoader('/path/to/model.gguf')")
    print("  meta = model.load_metadata()")
    print("  tensors = model.load_tensors()")
    print("=" * 60)


if __name__ == "__main__":
    demo()
