"""Speech ASR Engine - Automatic speech recognition with phoneme matching."""
from __future__ import annotations

import json
import hashlib
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ASRTranscript:
    audio_id: str
    text: str = ""
    confidence: float = 0.0
    word_timings: List[Dict] = field(default_factory=list)
    language: str = "en"

    def to_dict(self) -> Dict:
        return {
            "audio_id": self.audio_id,
            "text": self.text,
            "confidence": self.confidence,
            "word_timings": self.word_timings,
            "language": self.language,
        }


@dataclass
class AudioFrame:
    frame_id: str
    samples: List[float] = field(default_factory=list)
    sample_rate: int = 16000
    duration_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "frame_id": self.frame_id,
            "sample_count": len(self.samples),
            "sample_rate": self.sample_rate,
            "duration_ms": self.duration_ms,
        }


class SpeechASREngine:
    """Automatic speech recognition using simulated spectral feature extraction."""

    PHONEME_VOCAB = [
        "sil", "ah", "aa", "eh", "ih", "iy", "uh", "uw", "ow", "ay", "ey", "oy",
        "b", "d", "f", "g", "h", "k", "l", "m", "n", "p", "r", "s", "t", "v", "w", "y", "z",
        "th", "sh", "ch", "jh", "ng", "dh",
    ]

    WORDS = [
        "hello", "world", "system", "ready", "process", "complete", "start", "stop",
        "continue", "pause", "resume", "execute", "analyze", "compute", "deploy", "magnatrix",
    ]

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "speech_asr"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts: Dict[str, ASRTranscript] = {}
        self.acoustic_model: Dict[str, List[float]] = self._build_acoustic_model()
        self._load_state()

    def _build_acoustic_model(self) -> Dict[str, List[float]]:
        """Build simulated acoustic model with phoneme feature vectors."""
        model = {}
        for i, ph in enumerate(self.PHONEME_VOCAB):
            features = [math.sin(i + j * 0.5) * 0.5 + 0.5 for j in range(13)]
            model[ph] = features
        return model

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for t in data.get("transcripts", []):
                    self.transcripts[t["audio_id"]] = ASRTranscript(**t)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {"transcripts": [t.to_dict() for t in self.transcripts.values()]}
        state_file.write_text(json.dumps(state, indent=2))

    def _extract_features(self, samples: List[float]) -> List[float]:
        """Simulate MFCC-like feature extraction."""
        if not samples:
            return [0.0] * 13
        n = len(samples)
        energy = sum(x * x for x in samples) / n
        zcr = sum(1 for i in range(1, n) if samples[i-1] * samples[i] < 0) / max(1, n - 1)
        features = [energy, zcr]
        for i in range(11):
            features.append(math.sin(energy + i * 0.3) * 0.5 + 0.5)
        return features

    def _phoneme_match(self, features: List[float]) -> str:
        """Match features to closest phoneme."""
        best_ph = "sil"
        best_score = float("inf")
        for ph, ref in self.acoustic_model.items():
            score = sum((a - b) ** 2 for a, b in zip(features, ref))
            if score < best_score:
                best_score = score
                best_ph = ph
        return best_ph

    def recognize(self, audio_samples: List[float], audio_id: str = "", sample_rate: int = 16000) -> ASRTranscript:
        """Recognize speech from audio samples."""
        if not audio_id:
            audio_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:12]

        features = self._extract_features(audio_samples)
        phoneme = self._phoneme_match(features)

        # Map phoneme to likely word
        text = self._phoneme_to_word(phoneme)
        confidence = 0.6 + (hash(audio_id) % 30) / 100.0
        confidence = min(0.99, confidence)

        transcript = ASRTranscript(
            audio_id=audio_id,
            text=text,
            confidence=round(confidence, 3),
            language="en",
        )
        self.transcripts[audio_id] = transcript
        self._save_state()
        return transcript

    def _phoneme_to_word(self, phoneme: str) -> str:
        """Map phoneme to a representative word."""
        idx = hash(phoneme) % len(self.WORDS)
        return self.WORDS[idx]

    def transcribe_batch(self, audio_batches: List[Tuple[str, List[float]]]) -> List[ASRTranscript]:
        """Transcribe multiple audio segments."""
        return [self.recognize(samples, aid) for aid, samples in audio_batches]

    def get_transcript(self, audio_id: str) -> Optional[ASRTranscript]:
        return self.transcripts.get(audio_id)

    def get_stats(self) -> Dict:
        avg_conf = sum(t.confidence for t in self.transcripts.values()) / max(1, len(self.transcripts))
        return {
            "transcripts_total": len(self.transcripts),
            "avg_confidence": round(avg_conf, 3),
            "phoneme_vocab_size": len(self.PHONEME_VOCAB),
            "acoustic_model_entries": len(self.acoustic_model),
        }

    def to_dict(self) -> Dict:
        return {
            "transcripts": [t.to_dict() for t in self.transcripts.values()],
            "stats": self.get_stats(),
        }


__all__ = ["SpeechASREngine", "ASRTranscript", "AudioFrame"]
