"""Delta Encoder - Delta encoding for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto

@dataclass
class DeltaEncoder:

    def encode(self, data: List[float]) -> List[float]:
        if not data: return []
        result = [data[0]]
        for i in range(1, len(data)):
            result.append(data[i] - data[i-1])
        return result

    def decode(self, encoded: List[float]) -> List[float]:
        if not encoded: return []
        result = [encoded[0]]
        for i in range(1, len(encoded)):
            result.append(result[-1] + encoded[i])
        return result

    def stats(self, data: List[float]) -> dict:
        encoded = self.encode(data)
        avg_delta = sum(abs(e) for e in encoded[1:]) / max(1, len(encoded)-1)
        return {"original": len(data), "avg_delta": round(avg_delta, 4)}

def run():
    de = DeltaEncoder()
    data = [10, 12, 15, 13, 16, 18, 17, 19, 21, 20]
    encoded = de.encode(data)
    decoded = de.decode(encoded)
    print("Encoded:", encoded)
    print("Decoded:", decoded)
    print("Stats:", de.stats(data))

if __name__ == "__main__": run()
