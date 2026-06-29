"""Speech VAD - Voice Activity Detection engine."""
from __future__ import annotations

import json
import time
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class VADSegment:
    segment_id: str
    start_ms: float
    end_ms: float
    is_speech: bool = True
    confidence: float = 0.0
    energy_rms: float = 0.0

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms

    def to_dict(self) -> Dict:
        return {
            "segment_id": self.segment_id,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
            "is_speech": self.is_speech,
            "confidence": self.confidence,
            "energy_rms": self.energy_rms,
        }


class SpeechVAD:
    """Voice Activity Detection using energy threshold and zero-crossing rate."""

    def __init__(self, workspace: str = ".", energy_threshold: float = 0.01, zcr_threshold: float = 0.15):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "speech_vad"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.energy_threshold = energy_threshold
        self.zcr_threshold = zcr_threshold
        self.segments: List[VADSegment] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for s in data.get("segments", []):
                    self.segments.append(VADSegment(**s))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {"segments": [s.to_dict() for s in self.segments]}
        state_file.write_text(json.dumps(state, indent=2))

    def _compute_energy(self, samples: List[float]) -> float:
        """Compute RMS energy."""
        if not samples:
            return 0.0
        return math.sqrt(sum(x * x for x in samples) / len(samples))

    def _compute_zcr(self, samples: List[float]) -> float:
        """Compute zero-crossing rate."""
        if len(samples) < 2:
            return 0.0
        crossings = sum(1 for i in range(1, len(samples)) if samples[i-1] * samples[i] < 0)
        return crossings / (len(samples) - 1)

    def detect(self, samples: List[float], frame_ms: float = 30.0, sample_rate: int = 16000) -> List[VADSegment]:
        """Detect speech segments in audio."""
        frame_samples = int(sample_rate * frame_ms / 1000.0)
        segments: List[VADSegment] = []
        current_start = 0.0
        in_speech = False
        segment_idx = 0

        for i in range(0, len(samples), frame_samples):
            frame = samples[i:i + frame_samples]
            if not frame:
                break
            energy = self._compute_energy(frame)
            zcr = self._compute_zcr(frame)
            timestamp_ms = i * 1000.0 / sample_rate

            is_speech_frame = energy > self.energy_threshold and zcr < self.zcr_threshold

            if is_speech_frame and not in_speech:
                current_start = timestamp_ms
                in_speech = True
            elif not is_speech_frame and in_speech:
                seg = VADSegment(
                    segment_id=f"seg_{segment_idx}_{int(time.time())}",
                    start_ms=current_start,
                    end_ms=timestamp_ms,
                    is_speech=True,
                    confidence=min(1.0, energy / (self.energy_threshold + 0.001)),
                    energy_rms=round(energy, 6),
                )
                segments.append(seg)
                in_speech = False
                segment_idx += 1

        if in_speech:
            seg = VADSegment(
                segment_id=f"seg_{segment_idx}_{int(time.time())}",
                start_ms=current_start,
                end_ms=len(samples) * 1000.0 / sample_rate,
                is_speech=True,
                confidence=min(1.0, self._compute_energy(samples) / (self.energy_threshold + 0.001)),
                energy_rms=round(self._compute_energy(samples), 6),
            )
            segments.append(seg)

        self.segments.extend(segments)
        self._save_state()
        return segments

    def filter_speech(self, samples: List[float], sample_rate: int = 16000) -> List[float]:
        """Extract only speech segments from audio."""
        segments = self.detect(samples, sample_rate=sample_rate)
        speech_samples = []
        frame_ms = 30.0
        frame_samples = int(sample_rate * frame_ms / 1000.0)
        for seg in segments:
            if seg.is_speech:
                start_sample = int(seg.start_ms * sample_rate / 1000.0)
                end_sample = int(seg.end_ms * sample_rate / 1000.0)
                speech_samples.extend(samples[start_sample:end_sample])
        return speech_samples

    def get_speech_ratio(self, samples: List[float], sample_rate: int = 16000) -> float:
        """Get ratio of speech to total audio duration."""
        segments = self.detect(samples, sample_rate=sample_rate)
        speech_duration = sum(s.duration_ms for s in segments if s.is_speech)
        total_duration = len(samples) * 1000.0 / sample_rate
        return round(speech_duration / max(1.0, total_duration), 3)

    def get_stats(self) -> Dict:
        total_speech = sum(s.duration_ms for s in self.segments if s.is_speech)
        total_duration = sum(s.duration_ms for s in self.segments)
        return {
            "segments_total": len(self.segments),
            "speech_duration_ms": round(total_speech, 1),
            "total_duration_ms": round(total_duration, 1),
            "energy_threshold": self.energy_threshold,
            "zcr_threshold": self.zcr_threshold,
        }

    def to_dict(self) -> Dict:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "stats": self.get_stats(),
        }


__all__ = ["SpeechVAD", "VADSegment"]
