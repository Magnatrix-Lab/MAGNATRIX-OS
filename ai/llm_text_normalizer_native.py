"""
llm_text_normalizer_native.py
MAGNATRIX-OS Text Normalizer Engine
Native Python, stdlib only.
Provides text normalization: lowercasing, accent removal, punctuation cleaning, whitespace fixing.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional


class TextNormalizerEngine:
    def __init__(self) -> None:
        self._rules: List[str] = []

    def lowercase(self, text: str) -> str:
        return text.lower()

    def remove_accents(self, text: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))

    def clean_punctuation(self, text: str) -> str:
        return re.sub(r"[^\w\s]", "", text)

    def fix_whitespace(self, text: str) -> str:
        return " ".join(text.split())

    def remove_urls(self, text: str) -> str:
        return re.sub(r"https?://\S+|www\.\S+", "", text)

    def remove_emails(self, text: str) -> str:
        return re.sub(r"\S+@\S+", "", text)

    def normalize(self, text: str, steps: Optional[List[str]] = None) -> str:
        steps = steps or ["lowercase", "remove_accents", "clean_punctuation", "fix_whitespace"]
        for step in steps:
            text = getattr(self, step)(text)
        return text.strip()


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Text Normalizer")
    print("=" * 60)
    e = TextNormalizerEngine()
    text = "  Hello, World! Visit https://example.com or email test@example.com\n\n"
    print(f"  Original: '{text}'")
    print(f"  Normalized: '{e.normalize(text)}'")
    print("\nText Normalizer test complete.")


if __name__ == "__main__":
    run()
