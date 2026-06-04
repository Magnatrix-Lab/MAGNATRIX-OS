"""Voice Activity Detector - Energy-based VAD for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class VoiceActivityDetector:
    energy_threshold: float = 0.01
    frame_size: int = 256

    def detect(self, audio: List[float]) -> List[bool]:
        results = []
        for i in range(0, len(audio), self.frame_size):
            frame = audio[i:i+self.frame_size]
            energy = sum(x*x for x in frame) / len(frame) if frame else 0
            results.append(energy > self.energy_threshold)
        return results

    def find_segments(self, audio: List[float]) -> List[Tuple[int, int]]:
        active = self.detect(audio)
        segments = []
        start = None
        for i, is_active in enumerate(active):
            if is_active and start is None:
                start = i * self.frame_size
            elif not is_active and start is not None:
                segments.append((start, i * self.frame_size))
                start = None
        if start is not None:
            segments.append((start, len(audio)))
        return segments

    def stats(self, audio: List[float]) -> dict:
        active = self.detect(audio)
        return {"frames": len(active), "active_frames": sum(active), "frame_size": self.frame_size}

def run():
    vad = VoiceActivityDetector(0.1, 10)
    audio = [0.0]*10 + [0.5]*10 + [0.0]*10 + [0.8]*10 + [0.0]*10
    segments = vad.find_segments(audio)
    print("Segments:", segments)
    print("Stats:", vad.stats(audio))

if __name__ == "__main__": run()
