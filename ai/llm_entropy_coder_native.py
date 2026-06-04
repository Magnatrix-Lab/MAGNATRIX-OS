"""Entropy Coder - Arithmetic coding for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
from collections import Counter

@dataclass
class EntropyCoder:

    def build_cdf(self, data: str) -> Dict[str, Tuple[float, float]]:
        freq = Counter(data)
        total = sum(freq.values())
        cdf = {}
        low = 0.0
        for c in sorted(freq.keys()):
            prob = freq[c] / total
            cdf[c] = (low, low + prob)
            low += prob
        return cdf

    def encode(self, data: str) -> float:
        cdf = self.build_cdf(data)
        low, high = 0.0, 1.0
        for c in data:
            l, h = cdf[c]
            range_ = high - low
            high = low + range_ * h
            low = low + range_ * l
        return (low + high) / 2

    def decode(self, code: float, length: int, cdf: Dict[str, Tuple[float, float]]) -> str:
        result = ""
        for _ in range(length):
            for c, (l, h) in cdf.items():
                if l <= code < h:
                    result += c
                    range_ = h - l
                    code = (code - l) / range_
                    break
        return result

    def stats(self, data: str) -> dict:
        cdf = self.build_cdf(data)
        encoded = self.encode(data)
        decoded = self.decode(encoded, len(data), cdf)
        return {"original": len(data), "code": round(encoded, 8), "match": data == decoded}

def run():
    ec = EntropyCoder()
    data = "aabbc"
    print("Stats:", ec.stats(data))

if __name__ == "__main__": run()
