"""Speech Synthesis - Audio waveform synthesis engine."""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class WaveformConfig:
    config_id: str
    wave_type: str = "sine"  # sine, square, sawtooth, triangle, noise
    frequency_hz: float = 440.0
    amplitude: float = 0.5
    duration_ms: float = 1000.0
    sample_rate: int = 16000
    phase: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "config_id": self.config_id,
            "wave_type": self.wave_type,
            "frequency_hz": self.frequency_hz,
            "amplitude": self.amplitude,
            "duration_ms": self.duration_ms,
            "sample_rate": self.sample_rate,
            "phase": self.phase,
        }


@dataclass
class SynthesizedAudio:
    audio_id: str
    samples: List[float] = field(default_factory=list)
    sample_rate: int = 16000
    duration_ms: float = 0.0
    config: Optional[WaveformConfig] = None

    def to_dict(self) -> Dict:
        return {
            "audio_id": self.audio_id,
            "sample_count": len(self.samples),
            "sample_rate": self.sample_rate,
            "duration_ms": self.duration_ms,
            "config": self.config.to_dict() if self.config else None,
        }


class SpeechSynthesis:
    """Audio waveform synthesis using multiple oscillator types."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "speech_synthesis"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audio_clips: Dict[str, SynthesizedAudio] = {}
        self.configs: Dict[str, WaveformConfig] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for a in data.get("audio_clips", []):
                    cfg = WaveformConfig(**a.pop("config", {})) if "config" in a else None
                    self.audio_clips[a["audio_id"]] = SynthesizedAudio(config=cfg, **a)
                for c in data.get("configs", []):
                    self.configs[c["config_id"]] = WaveformConfig(**c)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "audio_clips": [a.to_dict() for a in self.audio_clips.values()],
            "configs": [c.to_dict() for c in self.configs.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def _generate_wave(self, config: WaveformConfig) -> List[float]:
        """Generate waveform samples based on config."""
        num_samples = int(config.sample_rate * config.duration_ms / 1000.0)
        samples = []
        for i in range(num_samples):
            t = i / config.sample_rate
            if config.wave_type == "sine":
                sample = math.sin(2 * math.pi * config.frequency_hz * t + config.phase)
            elif config.wave_type == "square":
                sample = 1.0 if math.sin(2 * math.pi * config.frequency_hz * t + config.phase) >= 0 else -1.0
            elif config.wave_type == "sawtooth":
                sample = 2 * ((config.frequency_hz * t + config.phase / (2 * math.pi)) % 1.0) - 1.0
            elif config.wave_type == "triangle":
                phase = (config.frequency_hz * t + config.phase / (2 * math.pi)) % 1.0
                sample = 4 * abs(phase - 0.5) - 1.0
            elif config.wave_type == "noise":
                sample = math.sin(i * 9301 + 49297) % 1.0 * 2 - 1.0
            else:
                sample = 0.0
            samples.append(sample * config.amplitude)
        return samples

    def synthesize(self, config: WaveformConfig) -> SynthesizedAudio:
        """Synthesize audio from waveform configuration."""
        samples = self._generate_wave(config)
        audio = SynthesizedAudio(
            audio_id=f"audio_{config.config_id}_{int(time.time())}",
            samples=samples,
            sample_rate=config.sample_rate,
            duration_ms=config.duration_ms,
            config=config,
        )
        self.audio_clips[audio.audio_id] = audio
        self.configs[config.config_id] = config
        self._save_state()
        return audio

    def mix(self, audio_ids: List[str], weights: Optional[List[float]] = None) -> SynthesizedAudio:
        """Mix multiple audio clips together."""
        if not audio_ids:
            return SynthesizedAudio(audio_id="empty")
        clips = [self.audio_clips[aid] for aid in audio_ids if aid in self.audio_clips]
        if not clips:
            return SynthesizedAudio(audio_id="empty")
        max_len = max(len(c.samples) for c in clips)
        if weights is None:
            weights = [1.0 / len(clips)] * len(clips)
        mixed = [0.0] * max_len
        for clip, w in zip(clips, weights):
            for i, s in enumerate(clip.samples):
                mixed[i] += s * w
        mixed_id = f"mixed_{int(time.time())}"
        result = SynthesizedAudio(
            audio_id=mixed_id,
            samples=mixed,
            sample_rate=clips[0].sample_rate,
            duration_ms=len(mixed) * 1000.0 / clips[0].sample_rate,
        )
        self.audio_clips[mixed_id] = result
        self._save_state()
        return result

    def create_config(self, wave_type: str, frequency_hz: float, duration_ms: float, amplitude: float = 0.5, sample_rate: int = 16000) -> WaveformConfig:
        config = WaveformConfig(
            config_id=f"cfg_{wave_type}_{int(frequency_hz)}_{int(time.time())}",
            wave_type=wave_type,
            frequency_hz=frequency_hz,
            amplitude=amplitude,
            duration_ms=duration_ms,
            sample_rate=sample_rate,
        )
        self.configs[config.config_id] = config
        self._save_state()
        return config

    def get_stats(self) -> Dict:
        total_samples = sum(len(a.samples) for a in self.audio_clips.values())
        return {
            "audio_clips_total": len(self.audio_clips),
            "configs_total": len(self.configs),
            "total_samples_generated": total_samples,
            "wave_types_used": list(set(c.wave_type for c in self.configs.values())),
        }

    def to_dict(self) -> Dict:
        return {
            "audio_clips": [a.to_dict() for a in self.audio_clips.values()],
            "configs": [c.to_dict() for c in self.configs.values()],
            "stats": self.get_stats(),
        }


__all__ = ["SpeechSynthesis", "WaveformConfig", "SynthesizedAudio"]
