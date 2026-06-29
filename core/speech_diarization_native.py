"""Speech Diarization - Speaker diarization engine."""
from __future__ import annotations

import json
import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class SpeakerSegment:
    segment_id: str
    speaker_id: str
    start_ms: float
    end_ms: float
    confidence: float = 0.0

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms

    def to_dict(self) -> Dict:
        return {
            "segment_id": self.segment_id,
            "speaker_id": self.speaker_id,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
            "confidence": self.confidence,
        }


@dataclass
class SpeakerProfile:
    speaker_id: str
    name: str = ""
    voiceprint: List[float] = field(default_factory=list)
    segment_count: int = 0
    total_duration_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "speaker_id": self.speaker_id,
            "name": self.name,
            "voiceprint_dim": len(self.voiceprint),
            "segment_count": self.segment_count,
            "total_duration_ms": self.total_duration_ms,
        }


class SpeechDiarization:
    """Speaker diarization using simulated voiceprint clustering."""

    def __init__(self, workspace: str = ".", num_speakers: int = 0):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "speech_diarization"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.num_speakers = num_speakers
        self.segments: List[SpeakerSegment] = []
        self.profiles: Dict[str, SpeakerProfile] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for s in data.get("segments", []):
                    self.segments.append(SpeakerSegment(**s))
                for p in data.get("profiles", []):
                    self.profiles[p["speaker_id"]] = SpeakerProfile(**p)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "segments": [s.to_dict() for s in self.segments],
            "profiles": [p.to_dict() for p in self.profiles.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def _extract_voiceprint(self, samples: List[float]) -> List[float]:
        """Extract a simulated voiceprint from audio samples."""
        if not samples:
            return [0.0] * 16
        n = len(samples)
        energy = sum(x * x for x in samples) / n
        mean = sum(samples) / n
        variance = sum((x - mean) ** 2 for x in samples) / n
        voiceprint = [energy, mean, variance, math.sqrt(variance)]
        for i in range(12):
            voiceprint.append(math.sin(energy + i * 0.7) * 0.5 + 0.5)
        return voiceprint

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _assign_speaker(self, voiceprint: List[float]) -> str:
        """Assign voiceprint to closest known speaker or create new."""
        best_id = None
        best_score = 0.6
        for sid, profile in self.profiles.items():
            if profile.voiceprint:
                score = self._cosine_similarity(voiceprint, profile.voiceprint)
                if score > best_score:
                    best_score = score
                    best_id = sid
        if best_id is None:
            best_id = f"speaker_{len(self.profiles) + 1}_{hashlib.md5(str(voiceprint[:4]).encode()).hexdigest()[:6]}"
            self.profiles[best_id] = SpeakerProfile(speaker_id=best_id, voiceprint=voiceprint)
        return best_id

    def diarize(self, segments: List[Tuple[float, float, List[float]]], audio_id: str = "") -> List[SpeakerSegment]:
        """Diarize audio segments into speakers."""
        results: List[SpeakerSegment] = []
        for i, (start_ms, end_ms, samples) in enumerate(segments):
            voiceprint = self._extract_voiceprint(samples)
            speaker_id = self._assign_speaker(voiceprint)
            seg = SpeakerSegment(
                segment_id=f"{audio_id}_seg_{i}",
                speaker_id=speaker_id,
                start_ms=start_ms,
                end_ms=end_ms,
                confidence=round(min(1.0, self._cosine_similarity(voiceprint, self.profiles[speaker_id].voiceprint) + 0.2), 3),
            )
            results.append(seg)
            self.profiles[speaker_id].segment_count += 1
            self.profiles[speaker_id].total_duration_ms += seg.duration_ms
            self.profiles[speaker_id].voiceprint = [
                (a + b) / 2 for a, b in zip(self.profiles[speaker_id].voiceprint, voiceprint)
            ]

        self.segments.extend(results)
        self._save_state()
        return results

    def get_speaker_timeline(self, speaker_id: str) -> List[SpeakerSegment]:
        return [s for s in self.segments if s.speaker_id == speaker_id]

    def get_speaker_stats(self) -> Dict[str, Dict]:
        return {sid: p.to_dict() for sid, p in self.profiles.items()}

    def get_stats(self) -> Dict:
        return {
            "segments_total": len(self.segments),
            "speakers_detected": len(self.profiles),
            "speaker_stats": self.get_speaker_stats(),
        }

    def to_dict(self) -> Dict:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "profiles": [p.to_dict() for p in self.profiles.values()],
            "stats": self.get_stats(),
        }


__all__ = ["SpeechDiarization", "SpeakerSegment", "SpeakerProfile"]
