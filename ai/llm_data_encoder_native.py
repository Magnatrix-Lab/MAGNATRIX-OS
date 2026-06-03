"""LLM Data Encoder — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class DataEncoder:
    def __init__(self) -> None:
        self._mappings: Dict[str, Dict[str, int]] = {}

    def label_encode(self, values: List[str]) -> List[int]:
        mapping = {}
        encoded = []
        for v in values:
            if v not in mapping:
                mapping[v] = len(mapping)
            encoded.append(mapping[v])
        self._mappings["label"] = mapping
        return encoded

    def one_hot_encode(self, values: List[str]) -> List[List[int]]:
        unique = sorted(set(values))
        mapping = {v: i for i, v in enumerate(unique)}
        encoded = []
        for v in values:
            row = [0] * len(unique)
            row[mapping[v]] = 1
            encoded.append(row)
        self._mappings["onehot"] = mapping
        return encoded

    def ordinal_encode(self, values: List[str], order: List[str]) -> List[int]:
        mapping = {v: i for i, v in enumerate(order)}
        return [mapping.get(v, -1) for v in values]

    def frequency_encode(self, values: List[str]) -> List[float]:
        counts = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1
        total = len(values)
        return [counts[v] / total for v in values]

    def get_stats(self) -> Dict[str, Any]:
        return {"encodings": len(self._mappings)}

def run() -> None:
    print("Data Encoder test")
    e = DataEncoder()
    values = ["a", "b", "a", "c", "b"]
    print("  Label: " + str(e.label_encode(values)))
    print("  One-hot: " + str(e.one_hot_encode(values)))
    print("  Ordinal: " + str(e.ordinal_encode(values, ["c", "a", "b"])))
    print("  Frequency: " + str(e.frequency_encode(values)))
    print("  Stats: " + str(e.get_stats()))
    print("Data Encoder test complete.")

if __name__ == "__main__":
    run()
