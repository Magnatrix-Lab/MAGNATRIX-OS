"""LLM Data Cleaner — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class CleanOperation(Enum):
    TRIM = auto()
    DEDUPLICATE = auto()
    NORMALIZE = auto()
    FILTER = auto()
    REPLACE = auto()

class DataCleaner:
    def __init__(self) -> None:
        self._operations: List[tuple] = []

    def add_operation(self, operation: CleanOperation, params: Dict[str, Any]) -> None:
        self._operations.append((operation, params))

    def clean(self, text: str) -> str:
        result = text
        for op, params in self._operations:
            if op == CleanOperation.TRIM:
                result = result.strip()
            elif op == CleanOperation.DEDUPLICATE:
                lines = result.splitlines()
                seen = set()
                unique = []
                for line in lines:
                    if line not in seen:
                        seen.add(line)
                        unique.append(line)
                result = "\n".join(unique)
            elif op == CleanOperation.NORMALIZE:
                result = re.sub(r"\s+", " ", result)
                result = result.lower()
            elif op == CleanOperation.FILTER:
                min_len = params.get("min_length", 0)
                lines = result.splitlines()
                lines = [l for l in lines if len(l.strip()) >= min_len]
                result = "\n".join(lines)
            elif op == CleanOperation.REPLACE:
                old = params.get("old", "")
                new = params.get("new", "")
                result = result.replace(old, new)
        return result

    def clean_batch(self, texts: List[str]) -> List[str]:
        return [self.clean(t) for t in texts]

    def get_stats(self, texts: List[str], cleaned: List[str]) -> Dict[str, Any]:
        original_chars = sum(len(t) for t in texts)
        cleaned_chars = sum(len(t) for t in cleaned)
        return {"original_chars": original_chars, "cleaned_chars": cleaned_chars, "reduction": original_chars - cleaned_chars}

def run() -> None:
    print("Data Cleaner test")
    e = DataCleaner()
    e.add_operation(CleanOperation.TRIM, {})
    e.add_operation(CleanOperation.NORMALIZE, {})
    e.add_operation(CleanOperation.REPLACE, {"old": "bad", "new": "good"})
    text = "  Hello   world.  \n\nHello world.  \nThis is bad.  "
    cleaned = e.clean(text)
    print("  Original: '" + text + "'")
    print("  Cleaned: '" + cleaned + "'")
    print("Data Cleaner test complete.")

if __name__ == "__main__":
    run()
