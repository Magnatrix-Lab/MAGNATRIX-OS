"""Huffman Coder - Huffman encoding for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto
from collections import Counter
import heapq

@dataclass
class HuffmanNode:
    char: Optional[str] = None
    freq: int = 0
    left: Optional["HuffmanNode"] = None
    right: Optional["HuffmanNode"] = None

    def __lt__(self, other):
        return self.freq < other.freq

@dataclass
class HuffmanCoder:
    codes: Dict[str, str] = field(default_factory=dict)
    root: Optional[HuffmanNode] = None

    def build(self, text: str) -> None:
        freq = Counter(text)
        if not freq: return
        heap = [HuffmanNode(char=c, freq=f) for c, f in freq.items()]
        heapq.heapify(heap)
        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            node = HuffmanNode(freq=left.freq + right.freq, left=left, right=right)
            heapq.heappush(heap, node)
        self.root = heap[0]
        self.codes = {}
        self._build_codes(self.root, "")

    def _build_codes(self, node: HuffmanNode, code: str) -> None:
        if node.char is not None:
            self.codes[node.char] = code if code else "0"
            return
        if node.left: self._build_codes(node.left, code + "0")
        if node.right: self._build_codes(node.right, code + "1")

    def encode(self, text: str) -> str:
        if not self.codes: self.build(text)
        return "".join(self.codes.get(c, "") for c in text)

    def decode(self, encoded: str) -> str:
        if not self.root: return ""
        result = ""
        node = self.root
        for bit in encoded:
            if bit == "0": node = node.left
            else: node = node.right
            if node and node.char is not None:
                result += node.char
                node = self.root
        return result

    def stats(self, text: str) -> dict:
        encoded = self.encode(text)
        return {"original_bits": len(text) * 8, "encoded_bits": len(encoded), "compression": round(len(encoded)/(len(text)*8), 4)}

def run():
    hc = HuffmanCoder()
    text = "hello world"
    encoded = hc.encode(text)
    decoded = hc.decode(encoded)
    print("Encoded:", encoded)
    print("Decoded:", decoded)
    print("Stats:", hc.stats(text))

if __name__ == "__main__": run()
