#!/usr/bin/env python3
"""
MAGNATRIX-OS — Speech-to-Text / Text-to-Speech Bridge
ai/llm_speech_text_bridge_native.py

Features:
- Phoneme analysis (word → phoneme breakdown simulation)
- Pronunciation scoring (accuracy rating based on phoneme match)
- Audio metadata tracking (duration, sample rate, format)
- Text normalization for speech (number expansion, abbreviation handling)
- Transcript alignment (word-level timing simulation)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("speech_text_bridge")


@dataclass
class AudioSegment:
    word: str
    start_time: float
    end_time: float
    confidence: float
    phonemes: List[str] = field(default_factory=list)


@dataclass
class AudioMetadata:
    duration_sec: float
    sample_rate: int
    format: str
    channels: int
    word_count: int


class SpeechTextBridge:
    """Speech-to-text and text-to-speech bridge simulation."""

    PHONEME_MAP = {
        "hello": ["h", "eh", "l", "ow"],
        "world": ["w", "er", "l", "d"],
        "python": ["p", "ai", "th", "ah", "n"],
        "quick": ["k", "w", "ih", "k"],
        "brown": ["b", "r", "aw", "n"],
        "fox": ["f", "aa", "k", "s"],
        "jumps": ["jh", "ah", "m", "p", "s"],
        "over": ["ow", "v", "er"],
        "lazy": ["l", "ei", "z", "iy"],
        "dog": ["d", "aa", "g"],
    }

    ABBREVIATIONS = {
        "dr": "doctor", "mr": "mister", "mrs": "missus", "st": "street",
        "ave": "avenue", "etc": "et cetera", "e.g": "for example", "i.e": "that is",
        "vs": "versus", "vol": "volume", "no": "number",
    }

    def text_to_phonemes(self, text: str) -> Dict[str, List[str]]:
        words = re.findall(r'\w+', text.lower())
        result = {}
        for w in words:
            result[w] = self.PHONEME_MAP.get(w, [c for c in w])
        return result

    def score_pronunciation(self, expected: str, phonemes: List[str]) -> float:
        expected_phones = self.PHONEME_MAP.get(expected.lower(), [])
        if not expected_phones:
            return 0.5
        matches = sum(1 for a, b in zip(expected_phones, phonemes) if a == b)
        return matches / max(len(expected_phones), len(phonemes), 1)

    def normalize_text(self, text: str) -> str:
        words = text.split()
        result = []
        for w in words:
            lower = w.lower().strip(".,!?;")
            if lower in self.ABBREVIATIONS:
                result.append(self.ABBREVIATIONS[lower])
            elif lower.isdigit():
                result.append(self._number_to_words(int(lower)))
            else:
                result.append(w)
        return " ".join(result)

    def _number_to_words(self, n: int) -> str:
        if n == 0: return "zero"
        if n < 0: return "negative " + self._number_to_words(-n)
        if n < 20: return ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"][n-1]
        if n < 100:
            tens = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"][(n // 10) - 2]
            if n % 10 == 0:
                return tens
            return tens + " " + self._number_to_words(n % 10)
        return str(n)

    def align_transcript(self, text: str, duration_sec: float) -> List[AudioSegment]:
        words = text.split()
        if not words:
            return []
        word_duration = duration_sec / len(words)
        segments = []
        for i, w in enumerate(words):
            start = i * word_duration
            end = start + word_duration
            phones = self.PHONEME_MAP.get(w.lower().strip(".,!?;"), [])
            segments.append(AudioSegment(w, start, end, 0.95, phones))
        return segments

    def get_metadata(self, text: str, duration_sec: float) -> AudioMetadata:
        words = len(text.split())
        return AudioMetadata(duration_sec, 16000, "wav", 1, words)

    def tts_estimate_duration(self, text: str, words_per_min: float = 150.0) -> float:
        words = len(text.split())
        return (words / words_per_min) * 60

    def get_stats(self) -> Dict[str, Any]:
        return {"phoneme_map_size": len(self.PHONEME_MAP), "abbreviations": len(self.ABBREVIATIONS)}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Speech-to-Text / Text-to-Speech Bridge")
    print("ai/llm_speech_text_bridge_native.py")
    print("=" * 60)

    bridge = SpeechTextBridge()
    text = "Hello world. Dr. Smith lives at 42 St. Ave. Python is quick."

    # 1. Phonemes
    print("\n[1] Phoneme Analysis")
    phonemes = bridge.text_to_phonemes(text)
    for w, p in list(phonemes.items())[:5]:
        print(f"  {w}: {'-'.join(p)}")

    # 2. Pronunciation scoring
    print("\n[2] Pronunciation Scoring")
    score = bridge.score_pronunciation("hello", ["h", "eh", "l", "ow"])
    print(f"  'hello' perfect match: {score:.1%}")
    score = bridge.score_pronunciation("hello", ["h", "ah", "l", "oo"])
    print(f"  'hello' poor match: {score:.1%}")

    # 3. Text normalization
    print("\n[3] Text Normalization")
    normalized = bridge.normalize_text(text)
    print(f"  Original: {text}")
    print(f"  Normalized: {normalized}")

    # 4. Transcript alignment
    print("\n[4] Transcript Alignment")
    segments = bridge.align_transcript("The quick brown fox", 2.0)
    for seg in segments:
        print(f"  {seg.word}: [{seg.start_time:.2f}s - {seg.end_time:.2f}s] conf={seg.confidence}")

    # 5. Audio metadata
    print("\n[5] Audio Metadata")
    meta = bridge.get_metadata(text, 5.0)
    print(f"  Duration: {meta.duration_sec}s, SR: {meta.sample_rate}, Words: {meta.word_count}")

    # 6. TTS duration estimate
    print("\n[6] TTS Duration Estimate")
    est = bridge.tts_estimate_duration("The quick brown fox jumps over the lazy dog")
    print(f"  Estimated: {est:.1f}s")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
