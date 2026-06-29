"""Speech TTS Engine - Text-to-speech with phoneme synthesis."""
from __future__ import annotations

import json
import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class Phoneme:
    symbol: str
    duration_ms: float = 80.0
    pitch_hz: float = 120.0
    amplitude: float = 0.8

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "duration_ms": self.duration_ms,
            "pitch_hz": self.pitch_hz,
            "amplitude": self.amplitude,
        }


@dataclass
class TTSUtterance:
    text: str
    phonemes: List[Phoneme] = field(default_factory=list)
    speed: float = 1.0
    pitch_shift: float = 0.0
    utterance_id: str = ""

    def __post_init__(self):
        if not self.utterance_id:
            self.utterance_id = hashlib.md5(self.text.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "phonemes": [p.to_dict() for p in self.phonemes],
            "speed": self.speed,
            "pitch_shift": self.pitch_shift,
            "utterance_id": self.utterance_id,
        }


@dataclass
class TTSVoice:
    voice_id: str
    name: str
    language: str = "en"
    gender: str = "neutral"
    sample_rate: int = 22050
    base_pitch: float = 120.0

    def to_dict(self) -> Dict:
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "language": self.language,
            "gender": self.gender,
            "sample_rate": self.sample_rate,
            "base_pitch": self.base_pitch,
        }


class SpeechTTSEngine:
    """Text-to-speech engine with rule-based phoneme synthesis."""

    PHONEME_MAP: Dict[str, str] = {
        "a": "ah", "b": "b", "c": "k", "d": "d", "e": "eh",
        "f": "f", "g": "g", "h": "hh", "i": "ih", "j": "jh",
        "k": "k", "l": "l", "m": "m", "n": "n", "o": "ow",
        "p": "p", "q": "k", "r": "r", "s": "s", "t": "t",
        "u": "uh", "v": "v", "w": "w", "x": "ks", "y": "y",
        "z": "z", "th": "th", "sh": "sh", "ch": "ch", "ph": "f",
        "ou": "ow", "ee": "iy", "ea": "iy", "oo": "uw", "ai": "ey",
        "ay": "ey", "oa": "ow", "ie": "iy", "igh": "ay", "ei": "ey",
    }

    VOWELS = set("aeiou")

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "speech_tts"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.voices: Dict[str, TTSVoice] = {}
        self.utterances: Dict[str, TTSUtterance] = {}
        self._default_voice = TTSVoice("default", "Default Voice")
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for v in data.get("voices", []):
                    self.voices[v["voice_id"]] = TTSVoice(**v)
                for u in data.get("utterances", []):
                    phs = [Phoneme(**p) for p in u.pop("phonemes", [])]
                    self.utterances[u["utterance_id"]] = TTSUtterance(phonemes=phs, **u)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "voices": [v.to_dict() for v in self.voices.values()],
            "utterances": [u.to_dict() for u in self.utterances.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def text_to_phonemes(self, text: str) -> List[Phoneme]:
        """Convert text to phoneme sequence using rule-based mapping."""
        text = text.lower().strip()
        phonemes: List[Phoneme] = []
        i = 0
        while i < len(text):
            if text[i].isalpha():
                # Try 2-letter match first
                if i + 1 < len(text) and text[i:i+2] in self.PHONEME_MAP:
                    sym = self.PHONEME_MAP[text[i:i+2]]
                    dur = 120.0 if text[i] in self.VOWELS else 80.0
                    phonemes.append(Phoneme(sym, duration_ms=dur))
                    i += 2
                    continue
                # Single letter
                sym = self.PHONEME_MAP.get(text[i], text[i])
                dur = 120.0 if text[i] in self.VOWELS else 80.0
                phonemes.append(Phoneme(sym, duration_ms=dur))
                i += 1
            else:
                i += 1
        if not phonemes:
            phonemes = [Phoneme("sil")]
        return phonemes

    def synthesize(self, text: str, voice_id: str = "default", speed: float = 1.0, pitch_shift: float = 0.0) -> TTSUtterance:
        """Synthesize text into utterance with phonemes."""
        phonemes = self.text_to_phonemes(text)
        utterance = TTSUtterance(
            text=text,
            phonemes=phonemes,
            speed=speed,
            pitch_shift=pitch_shift,
        )
        self.utterances[utterance.utterance_id] = utterance
        self._save_state()
        return utterance

    def estimate_duration_ms(self, text: str, speed: float = 1.0) -> float:
        """Estimate audio duration in milliseconds."""
        phonemes = self.text_to_phonemes(text)
        total = sum(p.duration_ms for p in phonemes)
        return total / speed

    def create_voice(self, voice_id: str, name: str, language: str = "en", gender: str = "neutral") -> TTSVoice:
        """Create a new voice profile."""
        voice = TTSVoice(voice_id=voice_id, name=name, language=language, gender=gender)
        self.voices[voice_id] = voice
        self._save_state()
        return voice

    def get_voice(self, voice_id: str) -> Optional[TTSVoice]:
        return self.voices.get(voice_id)

    def list_voices(self) -> List[Dict]:
        return [v.to_dict() for v in self.voices.values()]

    def get_stats(self) -> Dict:
        total_phonemes = sum(len(u.phonemes) for u in self.utterances.values())
        total_text = sum(len(u.text) for u in self.utterances.values())
        return {
            "voices_registered": len(self.voices),
            "utterances_synthesized": len(self.utterances),
            "total_phonemes": total_phonemes,
            "total_text_chars": total_text,
            "phoneme_coverage": len(self.PHONEME_MAP),
        }

    def to_dict(self) -> Dict:
        return {
            "voices": self.list_voices(),
            "utterances": [u.to_dict() for u in self.utterances.values()],
            "stats": self.get_stats(),
        }


__all__ = ["SpeechTTSEngine", "TTSVoice", "TTSUtterance", "Phoneme"]
