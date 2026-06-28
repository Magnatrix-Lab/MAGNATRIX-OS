#!/usr/bin/env python3
"""Encrypted Channel Analyzer for MAGNATRIX-OS."""
from __future__ import annotations
import math, statistics
from typing import Any, Dict, List, Optional

class EncryptedChannelAnalyzer:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.baseline_entropy = 4.5
    def shannon_entropy(self, data: bytes) -> float:
        if not data: return 0.0
        freq = {}
        for b in data:
            freq[b] = freq.get(b, 0) + 1
        total = len(data)
        return -sum((c/total) * math.log2(c/total) for c in freq.values() if c > 0)
    def analyze_payload(self, payload: bytes) -> Dict[str, Any]:
        entropy = self.shannon_entropy(payload)
        is_encrypted = entropy > self.baseline_entropy
        return {"entropy": round(entropy, 3), "is_encrypted": is_encrypted, "size": len(payload)}
    def analyze_traffic(self, payloads: List[bytes]) -> Dict[str, Any]:
        results = [self.analyze_payload(p) for p in payloads]
        encrypted_count = sum(1 for r in results if r["is_encrypted"])
        return {"total": len(results), "encrypted": encrypted_count, "avg_entropy": round(statistics.mean([r["entropy"] for r in results]), 3) if results else 0}
    def to_dict(self): return {"baseline_entropy": self.baseline_entropy}
