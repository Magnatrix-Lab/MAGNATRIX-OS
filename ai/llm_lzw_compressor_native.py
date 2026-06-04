"""LZW Compressor - Lempel-Ziv-Welch for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto

@dataclass
class LZWCompressor:
    dict_size: int = 256

    def compress(self, data: str) -> List[int]:
        dictionary = {chr(i): i for i in range(self.dict_size)}
        w = ""
        result = []
        for c in data:
            wc = w + c
            if wc in dictionary:
                w = wc
            else:
                result.append(dictionary[w])
                dictionary[wc] = len(dictionary)
                w = c
        if w: result.append(dictionary[w])
        return result

    def decompress(self, compressed: List[int]) -> str:
        dictionary = {i: chr(i) for i in range(self.dict_size)}
        w = chr(compressed[0]) if compressed else ""
        result = [w]
        for k in compressed[1:]:
            if k in dictionary:
                entry = dictionary[k]
            elif k == len(dictionary):
                entry = w + w[0]
            else:
                raise ValueError("Bad compressed k")
            result.append(entry)
            dictionary[len(dictionary)] = w + entry[0]
            w = entry
        return "".join(result)

    def stats(self, data: str) -> dict:
        compressed = self.compress(data)
        return {"original": len(data), "compressed": len(compressed), "ratio": round(len(compressed)/len(data), 4)}

def run():
    lzw = LZWCompressor()
    data = "TOBEORNOTTOBEORTOBEORNOT"
    compressed = lzw.compress(data)
    decompressed = lzw.decompress(compressed)
    print("Compressed:", compressed)
    print("Decompressed:", decompressed)
    print("Match:", data == decompressed)
    print("Stats:", lzw.stats(data))

if __name__ == "__main__": run()
