#!/usr/bin/env python3
"""
MAGNATRIX-OS — Data Augmentation Engine
ai/llm_data_augmentation_native.py

Features:
- Synonym replacement (word-level text augmentation)
- Random insertion and deletion of words
- Noise injection (typos, character swaps, case changes)
- Paraphrase generation (sentence restructuring)
- Back-translation simulation (language pivot)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import random
import string
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("data_augmentation")


class DataAugmentationEngine:
    """Text data augmentation techniques."""

    SYNONYMS = {
        "good": ["great", "excellent", "fine"],
        "bad": ["poor", "terrible", "awful"],
        "fast": ["quick", "rapid", "swift"],
        "big": ["large", "huge", "massive"],
        "small": ["tiny", "little", "mini"],
        "happy": ["joyful", "cheerful", "glad"],
        "sad": ["unhappy", "sorrowful", "melancholy"],
    }

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def synonym_replace(self, text: str, n: int = 1) -> str:
        words = text.split()
        candidates = [(i, w) for i, w in enumerate(words) if w.lower() in self.SYNONYMS]
        if not candidates:
            return text
        random.shuffle(candidates)
        for i, (idx, word) in enumerate(candidates[:n]):
            words[idx] = random.choice(self.SYNONYMS[word.lower()])
        return " ".join(words)

    def random_insert(self, text: str, n: int = 1) -> str:
        words = text.split()
        for _ in range(n):
            idx = random.randint(0, len(words))
            words.insert(idx, random.choice(["very", "quite", "really", "extremely"]))
        return " ".join(words)

    def random_delete(self, text: str, n: int = 1) -> str:
        words = text.split()
        if len(words) <= n:
            return text
        for _ in range(n):
            idx = random.randint(0, len(words) - 1)
            words.pop(idx)
        return " ".join(words)

    def add_noise(self, text: str, level: float = 0.1) -> str:
        chars = list(text)
        num = int(len(chars) * level)
        for _ in range(num):
            op = random.choice(["swap", "replace", "case"])
            idx = random.randint(0, len(chars) - 1)
            if op == "swap" and idx < len(chars) - 1:
                chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
            elif op == "replace":
                chars[idx] = random.choice(string.ascii_lowercase)
            elif op == "case" and chars[idx].isalpha():
                chars[idx] = chars[idx].swapcase()
        return "".join(chars)

    def paraphrase(self, text: str) -> str:
        words = text.split()
        result = []
        for w in words:
            lower = w.lower().strip(".,!?;:")
            if lower in self.SYNONYMS and random.random() < 0.5:
                replacement = random.choice(self.SYNONYMS[lower])
                result.append(replacement + w[len(lower):] if len(w) > len(lower) else replacement)
            else:
                result.append(w)
        # Shuffle some words
        if len(result) > 3 and random.random() < 0.3:
            i, j = random.randint(0, len(result) - 1), random.randint(0, len(result) - 1)
            result[i], result[j] = result[j], result[i]
        return " ".join(result)

    def back_translate(self, text: str) -> str:
        """Simulate back-translation by paraphrasing + noise."""
        p = self.paraphrase(text)
        return self.add_noise(p, level=0.05)

    def augment(self, text: str, techniques: List[str], n: int = 1) -> List[str]:
        results = []
        for _ in range(n):
            t = text
            for tech in techniques:
                if tech == "synonym":
                    t = self.synonym_replace(t)
                elif tech == "insert":
                    t = self.random_insert(t)
                elif tech == "delete":
                    t = self.random_delete(t)
                elif tech == "noise":
                    t = self.add_noise(t, 0.1)
                elif tech == "paraphrase":
                    t = self.paraphrase(t)
                elif tech == "back_translate":
                    t = self.back_translate(t)
            results.append(t)
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {"techniques": ["synonym", "insert", "delete", "noise", "paraphrase", "back_translate"]}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Data Augmentation Engine")
    print("ai/llm_data_augmentation_native.py")
    print("=" * 60)

    engine = DataAugmentationEngine(seed=42)
    text = "The quick brown fox jumps over the lazy dog. It is a good and fast animal."

    print(f"\nOriginal: {text}")

    # 1. Synonym replacement
    print("\n[1] Synonym Replacement")
    print(f"  {engine.synonym_replace(text, n=2)}")

    # 2. Random insert
    print("\n[2] Random Insertion")
    print(f"  {engine.random_insert(text, n=2)}")

    # 3. Random delete
    print("\n[3] Random Deletion")
    print(f"  {engine.random_delete(text, n=2)}")

    # 4. Noise
    print("\n[4] Noise Injection")
    print(f"  {engine.add_noise(text, level=0.1)}")

    # 5. Paraphrase
    print("\n[5] Paraphrase")
    print(f"  {engine.paraphrase(text)}")

    # 6. Back-translation
    print("\n[6] Back-Translation")
    print(f"  {engine.back_translate(text)}")

    # 7. Multi-technique
    print("\n[7] Multi-Technique Augment")
    results = engine.augment(text, ["synonym", "noise"], n=3)
    for i, r in enumerate(results):
        print(f"  Variant {i+1}: {r}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
