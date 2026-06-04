"""Speech Synthesizer - Parametric synthesis for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class SpeechSynthesizer:
    sample_rate: int = 16000
    frequency: float = 440.0
    duration: float = 1.0

    def synthesize(self, phonemes: List[str]) -> List[float]:
        samples = []
        samples_per_phoneme = int(self.sample_rate * self.duration / max(len(phonemes), 1))
        for phoneme in phonemes:
            f = self.frequency * (1.0 if phoneme in ["a", "e", "i", "o", "u"] else 0.5)
            for i in range(samples_per_phoneme):
                t = i / self.sample_rate
                samples.append(math.sin(2 * math.pi * f * t))
        return samples

    def stats(self, phonemes: List[str]) -> dict:
        samples = self.synthesize(phonemes)
        return {"phonemes": len(phonemes), "samples": len(samples), "duration": round(len(samples)/self.sample_rate, 4)}

def run():
    ss = SpeechSynthesizer(8000, 440, 0.5)
    samples = ss.synthesize(["h", "e", "l", "o"])
    print("Samples:", len(samples))
    print("Stats:", ss.stats(["h", "e", "l", "o"]))

if __name__ == "__main__": run()
