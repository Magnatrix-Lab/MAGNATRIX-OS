"""LLM Data Merger — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class MergeStrategy(Enum):
    UNION = auto()
    INTERSECTION = auto()
    CONCAT = auto()
    DEEP = auto()

class DataMerger:
    def __init__(self) -> None:
        self._strategy = MergeStrategy.UNION

    def set_strategy(self, strategy: MergeStrategy) -> None:
        self._strategy = strategy

    def merge_dicts(self, dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not dicts:
            return {}
        if self._strategy == MergeStrategy.UNION:
            result = {}
            for d in dicts:
                result.update(d)
            return result
        elif self._strategy == MergeStrategy.INTERSECTION:
            keys = set(dicts[0].keys())
            for d in dicts[1:]:
                keys &= set(d.keys())
            return {k: dicts[0][k] for k in keys}
        elif self._strategy == MergeStrategy.DEEP:
            result = {}
            for d in dicts:
                for k, v in d.items():
                    if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                        result[k] = self.merge_dicts([result[k], v])
                    else:
                        result[k] = v
            return result
        else:
            return {}

    def merge_lists(self, lists: List[List[Any]]) -> List[Any]:
        if self._strategy == MergeStrategy.CONCAT:
            result = []
            for l in lists:
                result.extend(l)
            return result
        elif self._strategy == MergeStrategy.UNION:
            result = []
            seen = set()
            for l in lists:
                for item in l:
                    key = str(item)
                    if key not in seen:
                        seen.add(key)
                        result.append(item)
            return result
        return []

    def get_stats(self, sources: List[Any]) -> Dict[str, Any]:
        return {"sources": len(sources), "strategy": self._strategy.name}

def run() -> None:
    print("Data Merger test")
    e = DataMerger()
    e.set_strategy(MergeStrategy.UNION)
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 3, "c": 4}
    print("  Union: " + str(e.merge_dicts([d1, d2])))
    e.set_strategy(MergeStrategy.INTERSECTION)
    print("  Intersection: " + str(e.merge_dicts([d1, d2])))
    e.set_strategy(MergeStrategy.DEEP)
    d3 = {"x": {"y": 1}}
    d4 = {"x": {"z": 2}}
    print("  Deep: " + str(e.merge_dicts([d3, d4])))
    print("Data Merger test complete.")

if __name__ == "__main__":
    run()
