#!/usr/bin/env python3
"""
MAGNATRIX-OS — Translation Engine
ai/llm_translation_engine_native.py

Features:
- Language pair mapping (lang codes, names)
- Translation quality scoring (BLEU-like simulation)
- Language detection simulation (keyword-based)
- Batch translation support
- Translation memory (cache previous translations)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("translation_engine")


@dataclass
class TranslationPair:
    source_lang: str
    target_lang: str
    source_text: str
    target_text: str
    quality_score: float = 0.0


class TranslationEngine:
    """Translation with language detection, quality scoring, and memory."""

    VOCABULARIES = {
        "en": {"hello": "hello", "world": "world", "good": "good", "morning": "morning"},
        "fr": {"hello": "bonjour", "world": "monde", "good": "bon", "morning": "matin"},
        "es": {"hello": "hola", "world": "mundo", "good": "bueno", "morning": "mañana"},
        "de": {"hello": "hallo", "world": "welt", "good": "gut", "morning": "morgen"},
        "id": {"hello": "halo", "world": "dunia", "good": "baik", "morning": "pagi"},
    }

    LANGUAGE_PATTERNS = {
        "fr": ["bonjour", "monde", "merci", "oui"],
        "es": ["hola", "mundo", "gracias", "si"],
        "de": ["hallo", "welt", "danke", "ja"],
        "id": ["halo", "dunia", "terima", "kasih", "pagi"],
    }

    def __init__(self):
        self._memory: Dict[Tuple[str, str, str], str] = {}
        self._history: List[TranslationPair] = []

    def detect_language(self, text: str) -> str:
        text_lower = text.lower()
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            if any(p in text_lower for p in patterns):
                return lang
        return "en"

    def translate(self, text: str, source_lang: str, target_lang: str) -> Tuple[str, float]:
        key = (source_lang, target_lang, text.lower())
        if key in self._memory:
            return self._memory[key], 0.95
        source_vocab = self.VOCABULARIES.get(source_lang, {})
        target_vocab = self.VOCABULARIES.get(target_lang, {})
        words = text.lower().split()
        translated = []
        matched = 0
        for word in words:
            clean = re.sub(r'[^\w]', '', word)
            if clean in source_vocab and clean in target_vocab:
                translated.append(target_vocab[clean])
                matched += 1
            else:
                translated.append(word)
        score = matched / max(len(words), 1) if words else 0.0
        result = " ".join(translated)
        self._memory[key] = result
        self._history.append(TranslationPair(source_lang, target_lang, text, result, score))
        return result, score

    def batch_translate(self, texts: List[str], source_lang: str, target_lang: str) -> List[Tuple[str, float]]:
        return [self.translate(t, source_lang, target_lang) for t in texts]

    def get_memory(self) -> Dict[str, str]:
        return {f"{k[0]}→{k[1]}: {k[2]}": v for k, v in self._memory.items()}

    def get_stats(self) -> Dict[str, Any]:
        return {"memory_entries": len(self._memory), "translations": len(self._history)}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Translation Engine")
    print("ai/llm_translation_engine_native.py")
    print("=" * 60)

    engine = TranslationEngine()

    # 1. Language detection
    print("\n[1] Language Detection")
    for text in ["Hello world", "Bonjour monde", "Hola mundo", "Halo dunia"]:
        lang = engine.detect_language(text)
        print(f"  '{text}': {lang}")

    # 2. Translation
    print("\n[2] Translation")
    pairs = [
        ("hello world", "en", "fr"),
        ("good morning", "en", "es"),
        ("hello world", "en", "id"),
        ("bonjour monde", "fr", "en"),
    ]
    for text, src, tgt in pairs:
        result, score = engine.translate(text, src, tgt)
        print(f"  [{src}→{tgt}] '{text}' → '{result}' (score={score:.2f})")

    # 3. Memory
    print("\n[3] Translation Memory")
    for key, val in engine.get_memory().items():
        print(f"  {key}: {val}")

    # 4. Batch
    print("\n[4] Batch Translation")
    results = engine.batch_translate(["hello", "world", "good"], "en", "de")
    for r, s in results:
        print(f"  {r} (score={s:.2f})")

    # 5. Stats
    print(f"\n[5] Stats: {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
