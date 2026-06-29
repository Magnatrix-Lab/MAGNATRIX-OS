"""Speech Fingerprinting - Audio fingerprinting engine (Chromaprint-like)."""
from __future__ import annotations

import json
import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class AudioFingerprint:
    fingerprint_id: str
    audio_hash: str
    peaks: List[int] = field(default_factory=list)
    duration_ms: float = 0.0
    sample_rate: int = 16000

    def to_dict(self) -> Dict:
        return {
            "fingerprint_id": self.fingerprint_id,
            "audio_hash": self.audio_hash,
            "peaks_count": len(self.peaks),
            "duration_ms": self.duration_ms,
            "sample_rate": self.sample_rate,
        }


@dataclass
class FingerprintMatch:
    match_id: str
    query_hash: str
    matched_hash: str
    similarity: float = 0.0
    offset_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "match_id": self.match_id,
            "query_hash": self.query_hash,
            "matched_hash": self.matched_hash,
            "similarity": self.similarity,
            "offset_ms": self.offset_ms,
        }


class SpeechFingerprinting:
    """Audio fingerprinting using spectral peak extraction."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "speech_fingerprinting"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.fingerprints: Dict[str, AudioFingerprint] = {}
        self.matches: List[FingerprintMatch] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for f in data.get("fingerprints", []):
                    self.fingerprints[f["fingerprint_id"]] = AudioFingerprint(**f)
                for m in data.get("matches", []):
                    self.matches.append(FingerprintMatch(**m))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "fingerprints": [f.to_dict() for f in self.fingerprints.values()],
            "matches": [m.to_dict() for m in self.matches],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def _extract_spectral_peaks(self, samples: List[float], sample_rate: int = 16000) -> List[int]:
        """Extract spectral peaks from audio samples."""
        if not samples:
            return []
        frame_size = 1024
        hop_size = 512
        peaks = []
        for i in range(0, len(samples) - frame_size, hop_size):
            frame = samples[i:i + frame_size]
            energy = [x * x for x in frame]
            max_energy = max(energy) if energy else 0
            if max_energy > 0.001:
                peak_idx = energy.index(max_energy)
                freq = peak_idx * sample_rate / frame_size
                peaks.append(int(freq))
        return peaks[:64]

    def _hash_peaks(self, peaks: List[int]) -> str:
        """Hash peak sequence to compact fingerprint."""
        data = json.dumps(peaks)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def fingerprint(self, samples: List[float], fingerprint_id: str = "", duration_ms: float = 0.0, sample_rate: int = 16000) -> AudioFingerprint:
        """Generate fingerprint from audio samples."""
        peaks = self._extract_spectral_peaks(samples, sample_rate)
        audio_hash = self._hash_peaks(peaks)
        if not fingerprint_id:
            fingerprint_id = f"fp_{audio_hash}"
        fp = AudioFingerprint(
            fingerprint_id=fingerprint_id,
            audio_hash=audio_hash,
            peaks=peaks,
            duration_ms=duration_ms or len(samples) * 1000.0 / sample_rate,
            sample_rate=sample_rate,
        )
        self.fingerprints[fingerprint_id] = fp
        self._save_state()
        return fp

    def match(self, query_samples: List[float], sample_rate: int = 16000) -> List[FingerprintMatch]:
        """Match query audio against fingerprint database."""
        query_peaks = self._extract_spectral_peaks(query_samples, sample_rate)
        query_hash = self._hash_peaks(query_peaks)
        matches = []

        for fp in self.fingerprints.values():
            common = sum(1 for a, b in zip(query_peaks, fp.peaks) if a == b)
            similarity = common / max(1, len(query_peaks), len(fp.peaks))
            if similarity > 0.3:
                matches.append(FingerprintMatch(
                    match_id=f"match_{query_hash}_{fp.audio_hash}",
                    query_hash=query_hash,
                    matched_hash=fp.audio_hash,
                    similarity=round(similarity, 3),
                ))

        matches.sort(key=lambda x: x.similarity, reverse=True)
        self.matches.extend(matches)
        self._save_state()
        return matches

    def get_fingerprint(self, fingerprint_id: str) -> Optional[AudioFingerprint]:
        return self.fingerprints.get(fingerprint_id)

    def get_stats(self) -> Dict:
        return {
            "fingerprints_total": len(self.fingerprints),
            "matches_total": len(self.matches),
            "avg_similarity": round(sum(m.similarity for m in self.matches) / max(1, len(self.matches)), 3),
        }

    def to_dict(self) -> Dict:
        return {
            "fingerprints": [f.to_dict() for f in self.fingerprints.values()],
            "matches": [m.to_dict() for m in self.matches],
            "stats": self.get_stats(),
        }


__all__ = ["SpeechFingerprinting", "AudioFingerprint", "FingerprintMatch"]
