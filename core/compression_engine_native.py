#!/usr/bin/env python3
"""Compression Engine for MAGNATRIX-OS — Data compression."""
from __future__ import annotations
import zlib, json
from typing import Any, Dict

class CompressionEngine:
    def compress(self, data: bytes, level: int = 6) -> bytes:
        return zlib.compress(data, level)

    def decompress(self, data: bytes) -> bytes:
        return zlib.decompress(data)

    def compress_string(self, text: str, level: int = 6) -> bytes:
        return self.compress(text.encode("utf-8"), level)

    def decompress_string(self, data: bytes) -> str:
        return self.decompress(data).decode("utf-8")

    def stats(self, data: bytes) -> Dict[str, Any]:
        compressed = self.compress(data)
        return {"original": len(data), "compressed": len(compressed), "ratio": len(compressed) / len(data) if data else 0}
