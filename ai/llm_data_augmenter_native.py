"""
llm_data_augmenter_native.py
MAGNATRIX-OS Data Augmenter Engine
Native Python, stdlib only.
Provides text augmentation with synonym replacement, random insertion/deletion, and swapping.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class DataAugmenterEngine:
    def __init__(self, seed: int = 42) -> None:
        random.seed(seed)
        self._synonyms: Dict[str, List[str]] = {
            "good": ["great", "excellent", "fine"],
            "bad": ["poor", "terrible", "awful"],
            "happy": ["joyful", "cheerful", "glad"],
            "sad": ["unhappy", "sorrowful", "gloomy"],
            "big": ["large", "huge", "enormous"],
            "small": ["tiny", "little", "miniature"],
        }

    def synonym_replace(self, text: str, n: int = 1) -> str:
        words = text.split()
        candidates = [(i, w) for i, w in enumerate(words) if w.lower() in self._synonyms]
        if not candidates:
            return text
        chosen = random.sample(candidates, min(n, len(candidates)))
        for i, w in chosen:
            words[i] = random.choice(self._synonyms[w.lower()])
        return " ".join(words)

    def random_delete(self, text: str, p: float = 0.1) -> str:
        words = text.split()
        return " ".join([w for w in words if random.random() > p])

    def random_insert(self, text: str, n: int = 1) -> str:
        words = text.split()
        for _ in range(n):
            pos = random.randint(0, len(words))
            words.insert(pos, random.choice(["very", "really", "quite", "extremely"]))
        return " ".join(words)

    def random_swap(self, text: str, n: int = 1) -> str:
        words = text.split()
        for _ in range(n):
            if len(words) >= 2:
                i, j = random.sample(range(len(words)), 2)
                words[i], words[j] = words[j], words[i]
        return " ".join(words)

    def augment(self, text: str, techniques: Optional[List[str]] = None) -> List[str]:
        techniques = techniques or ["synonym", "delete", "insert", "swap"]
        results = [text]
        if "synonym" in techniques:
            results.append(self.synonym_replace(text))
        if "delete" in techniques:
            results.append(self.random_delete(text))
        if "insert" in techniques:
            results.append(self.random_insert(text))
        if "swap" in techniques:
            results.append(self.random_swap(text))
        return results


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Data Augmenter")
    print("=" * 60)
    e = DataAugmenterEngine()
    text = "The big dog is happy and good"
    for r in e.augment(text):
        print(f"  {r}")
    print("\nData Augmenter test complete.")


if __name__ == "__main__":
    run()
