"""Run Length Encoder - RLE for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto

@dataclass
class RunLengthEncoder:

    def encode(self, data: List[int]) -> List[Tuple[int, int]]:
        if not data: return []
        result = []
        count = 1
        prev = data[0]
        for i in range(1, len(data)):
            if data[i] == prev:
                count += 1
            else:
                result.append((prev, count))
                prev = data[i]
                count = 1
        result.append((prev, count))
        return result

    def decode(self, encoded: List[Tuple[int, int]]) -> List[int]:
        result = []
        for value, count in encoded:
            result.extend([value] * count)
        return result

    def stats(self, data: List[int]) -> dict:
        encoded = self.encode(data)
        return {"original": len(data), "encoded": len(encoded), "ratio": round(len(encoded)/len(data), 4)}

def run():
    rle = RunLengthEncoder()
    data = [1, 1, 1, 2, 2, 3, 3, 3, 3, 3, 1, 1]
    encoded = rle.encode(data)
    decoded = rle.decode(encoded)
    print("Encoded:", encoded)
    print("Decoded:", decoded)
    print("Stats:", rle.stats(data))

if __name__ == "__main__": run()
