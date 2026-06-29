"""Speech Noise Suppressor - Noise suppression and audio enhancement."""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class NoiseProfile:
    profile_id: str
    noise_type: str = "white"
    estimated_snr_db: float = 0.0
    suppression_gain: float = 0.5
    noise_floor: float = 0.01

    def to_dict(self) -> Dict:
        return {
            "profile_id": self.profile_id,
            "noise_type": self.noise_type,
            "estimated_snr_db": self.estimated_snr_db,
            "suppression_gain": self.suppression_gain,
            "noise_floor": self.noise_floor,
        }


class SpeechNoiseSuppressor:
    """Noise suppression using spectral subtraction and adaptive filtering."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "speech_noise"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, NoiseProfile] = {}
        self.processed_count = 0
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                self.processed_count = data.get("processed_count", 0)
                for p in data.get("profiles", []):
                    self.profiles[p["profile_id"]] = NoiseProfile(**p)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "processed_count": self.processed_count,
            "profiles": [p.to_dict() for p in self.profiles.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def _estimate_noise_floor(self, samples: List[float]) -> float:
        """Estimate noise floor from lowest energy frames."""
        if not samples:
            return 0.01
        frame_size = 256
        energies = []
        for i in range(0, len(samples) - frame_size, frame_size):
            frame = samples[i:i + frame_size]
            energy = sum(x * x for x in frame) / len(frame)
            energies.append(energy)
        if not energies:
            return 0.01
        energies.sort()
        return math.sqrt(energies[len(energies) // 10])  # 10th percentile

    def _spectral_subtract(self, samples: List[float], noise_floor: float, over_subtraction: float = 1.0) -> List[float]:
        """Apply spectral subtraction filtering."""
        if not samples:
            return []
        threshold = noise_floor * over_subtraction
        output = []
        for sample in samples:
            mag = abs(sample)
            if mag > threshold:
                factor = max(0.0, (mag - threshold) / mag)
                output.append(sample * factor)
            else:
                output.append(0.0)
        return output

    def suppress(self, samples: List[float], noise_type: str = "adaptive") -> Tuple[List[float], NoiseProfile]:
        """Suppress noise from audio samples."""
        noise_floor = self._estimate_noise_floor(samples)
        snr_input = self._estimate_snr(samples, noise_floor)
        cleaned = self._spectral_subtract(samples, noise_floor, over_subtraction=1.2)
        snr_output = self._estimate_snr(cleaned, noise_floor * 0.5)

        profile = NoiseProfile(
            profile_id=f"ns_{int(time.time())}_{len(samples)}",
            noise_type=noise_type,
            estimated_snr_db=round(snr_output, 2),
            suppression_gain=round(max(0.0, snr_output - snr_input) / max(1.0, abs(snr_input)), 3),
            noise_floor=round(noise_floor, 6),
        )
        self.profiles[profile.profile_id] = profile
        self.processed_count += 1
        self._save_state()
        return cleaned, profile

    def _estimate_snr(self, samples: List[float], noise_floor: float) -> float:
        """Estimate SNR in dB."""
        if not samples:
            return 0.0
        signal_power = sum(x * x for x in samples) / len(samples)
        noise_power = noise_floor * noise_floor
        if noise_power <= 0:
            return 60.0
        snr = 10 * math.log10(signal_power / noise_power)
        return round(snr, 2)

    def create_profile(self, noise_type: str, noise_floor: float) -> NoiseProfile:
        """Create a manual noise profile."""
        profile = NoiseProfile(
            profile_id=f"profile_{noise_type}_{int(time.time())}",
            noise_type=noise_type,
            noise_floor=noise_floor,
        )
        self.profiles[profile.profile_id] = profile
        self._save_state()
        return profile

    def get_stats(self) -> Dict:
        avg_snr = sum(p.estimated_snr_db for p in self.profiles.values()) / max(1, len(self.profiles))
        return {
            "processed_count": self.processed_count,
            "profiles_total": len(self.profiles),
            "avg_snr_db": round(avg_snr, 2),
        }

    def to_dict(self) -> Dict:
        return {
            "profiles": [p.to_dict() for p in self.profiles.values()],
            "stats": self.get_stats(),
        }


__all__ = ["SpeechNoiseSuppressor", "NoiseProfile"]
