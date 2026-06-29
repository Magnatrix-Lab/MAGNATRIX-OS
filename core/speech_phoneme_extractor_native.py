"""Speech Phoneme Extractor - Phoneme extraction from text/audio."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class PhonemeToken:
    token_id: str
    symbol: str
    ipa_symbol: str = ""
    features: Dict[str, str] = field(default_factory=dict)
    position: int = 0

    def to_dict(self) -> Dict:
        return {
            "token_id": self.token_id,
            "symbol": self.symbol,
            "ipa_symbol": self.ipa_symbol,
            "features": self.features,
            "position": self.position,
        }


@dataclass
class PhonemeSequence:
    sequence_id: str
    source_text: str = ""
    tokens: List[PhonemeToken] = field(default_factory=list)
    language: str = "en"

    def to_dict(self) -> Dict:
        return {
            "sequence_id": self.sequence_id,
            "source_text": self.source_text,
            "tokens": [t.to_dict() for t in self.tokens],
            "language": self.language,
        }


class SpeechPhonemeExtractor:
    """Phoneme extraction with IPA mapping and feature tagging."""

    IPA_MAP: Dict[str, str] = {
        "ah": "ɑ", "aa": "ɑ", "eh": "ɛ", "ih": "ɪ", "iy": "i",
        "uh": "ʊ", "uw": "u", "ow": "oʊ", "ay": "aɪ", "ey": "eɪ",
        "oy": "ɔɪ", "b": "b", "d": "d", "f": "f", "g": "g", "h": "h",
        "k": "k", "l": "l", "m": "m", "n": "n", "p": "p", "r": "r", "s": "s",
        "t": "t", "v": "v", "w": "w", "y": "j", "z": "z", "th": "θ", "sh": "ʃ",
        "ch": "tʃ", "jh": "dʒ", "ng": "ŋ", "dh": "ð", "sil": "sil",
    }

    FEATURES: Dict[str, Dict[str, str]] = {
        "ah": {"type": "vowel", "height": "low", "backness": "back"},
        "eh": {"type": "vowel", "height": "mid", "backness": "front"},
        "ih": {"type": "vowel", "height": "high", "backness": "front"},
        "iy": {"type": "vowel", "height": "high", "backness": "front"},
        "uh": {"type": "vowel", "height": "high", "backness": "back"},
        "uw": {"type": "vowel", "height": "high", "backness": "back"},
        "ow": {"type": "vowel", "height": "mid", "backness": "back"},
        "ay": {"type": "vowel", "height": "low", "backness": "front"},
        "b": {"type": "consonant", "manner": "plosive", "place": "bilabial", "voiced": "yes"},
        "d": {"type": "consonant", "manner": "plosive", "place": "alveolar", "voiced": "yes"},
        "f": {"type": "consonant", "manner": "fricative", "place": "labiodental", "voiced": "no"},
        "k": {"type": "consonant", "manner": "plosive", "place": "velar", "voiced": "no"},
        "l": {"type": "consonant", "manner": "approximant", "place": "alveolar", "voiced": "yes"},
        "m": {"type": "consonant", "manner": "nasal", "place": "bilabial", "voiced": "yes"},
        "n": {"type": "consonant", "manner": "nasal", "place": "alveolar", "voiced": "yes"},
        "p": {"type": "consonant", "manner": "plosive", "place": "bilabial", "voiced": "no"},
        "s": {"type": "consonant", "manner": "fricative", "place": "alveolar", "voiced": "no"},
        "t": {"type": "consonant", "manner": "plosive", "place": "alveolar", "voiced": "no"},
        "th": {"type": "consonant", "manner": "fricative", "place": "dental", "voiced": "no"},
        "sh": {"type": "consonant", "manner": "fricative", "place": "postalveolar", "voiced": "no"},
        "ch": {"type": "consonant", "manner": "affricate", "place": "postalveolar", "voiced": "no"},
        "ng": {"type": "consonant", "manner": "nasal", "place": "velar", "voiced": "yes"},
        "sil": {"type": "silence", "manner": "none", "place": "none"},
    }

    ARPABET_RULES: Dict[str, str] = {
        "a": "ah", "e": "eh", "i": "ih", "o": "ow", "u": "uh",
        "th": "th", "sh": "sh", "ch": "ch", "ph": "f", "gh": "",
        "ck": "k", "ng": "ng", "wh": "w", "wr": "r", "kn": "n",
        "qu": "k", "x": "ks", "y": "y", "c": "k", "g": "g",
        "ee": "iy", "ea": "iy", "oo": "uw", "ou": "ow", "oi": "oy",
        "ai": "ay", "ay": "ey", "ie": "iy", "igh": "ay", "oa": "ow",
    }

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "speech_phonemes"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sequences: Dict[str, PhonemeSequence] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for s in data.get("sequences", []):
                    tokens = [PhonemeToken(**t) for t in s.pop("tokens", [])]
                    self.sequences[s["sequence_id"]] = PhonemeSequence(tokens=tokens, **s)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {"sequences": [s.to_dict() for s in self.sequences.values()]}
        state_file.write_text(json.dumps(state, indent=2))

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into grapheme chunks."""
        text = text.lower().strip()
        tokens = []
        i = 0
        while i < len(text):
            if text[i].isalpha():
                if i + 2 < len(text) and text[i:i+3] in self.ARPABET_RULES:
                    tokens.append(text[i:i+3])
                    i += 3
                elif i + 1 < len(text) and text[i:i+2] in self.ARPABET_RULES:
                    tokens.append(text[i:i+2])
                    i += 2
                else:
                    tokens.append(text[i])
                    i += 1
            else:
                i += 1
        return tokens

    def extract(self, text: str, sequence_id: str = "", language: str = "en") -> PhonemeSequence:
        """Extract phoneme sequence from text."""
        tokens = self._tokenize(text)
        phoneme_tokens = []
        for pos, token in enumerate(tokens):
            symbol = self.ARPABET_RULES.get(token, token if token in self.IPA_MAP else "")
            if not symbol:
                continue
            ipa = self.IPA_MAP.get(symbol, symbol)
            features = self.FEATURES.get(symbol, {"type": "unknown"})
            phoneme_tokens.append(PhonemeToken(
                token_id=f"tok_{pos}_{symbol}",
                symbol=symbol,
                ipa_symbol=ipa,
                features=features,
                position=pos,
            ))
        if not sequence_id:
            sequence_id = f"seq_{hash(text) % 100000}_{len(tokens)}"
        seq = PhonemeSequence(
            sequence_id=sequence_id,
            source_text=text,
            tokens=phoneme_tokens,
            language=language,
        )
        self.sequences[sequence_id] = seq
        self._save_state()
        return seq

    def get_phoneme_count(self, text: str) -> int:
        """Count phonemes in text."""
        return len(self._tokenize(text))

    def get_vowel_ratio(self, text: str) -> float:
        """Get ratio of vowels to total phonemes."""
        seq = self.extract(text)
        vowels = sum(1 for t in seq.tokens if t.features.get("type") == "vowel")
        return round(vowels / max(1, len(seq.tokens)), 3)

    def get_consonant_clusters(self, text: str) -> List[List[str]]:
        """Extract consonant clusters from text."""
        seq = self.extract(text)
        clusters = []
        current = []
        for t in seq.tokens:
            if t.features.get("type") == "consonant":
                current.append(t.symbol)
            else:
                if len(current) >= 2:
                    clusters.append(current[:])
                current = []
        if len(current) >= 2:
            clusters.append(current)
        return clusters

    def get_stats(self) -> Dict:
        total_tokens = sum(len(s.tokens) for s in self.sequences.values())
        return {
            "sequences_total": len(self.sequences),
            "total_tokens": total_tokens,
            "ipa_coverage": len(self.IPA_MAP),
            "feature_tags": len(self.FEATURES),
        }

    def to_dict(self) -> Dict:
        return {
            "sequences": [s.to_dict() for s in self.sequences.values()],
            "stats": self.get_stats(),
        }


__all__ = ["SpeechPhonemeExtractor", "PhonemeToken", "PhonemeSequence"]
