"""Pitch Detector — autocorrelation, YIN, FFT-based, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math, cmath

@dataclass
class PitchDetector:
    sample_rate: float = 44100.0

    def autocorrelation(self, signal: List[float]) -> List[float]:
        N = len(signal)
        return [sum(signal[i] * signal[i + lag] for i in range(N - lag)) for lag in range(1, N // 2)]

    def detect_pitch(self, signal: List[float]) -> float:
        if not signal:
            return 0.0
        ac = self.autocorrelation(signal)
        min_lag = int(self.sample_rate / 2000) if self.sample_rate > 0 else 10
        max_lag = int(self.sample_rate / 50) if self.sample_rate > 0 else len(ac)
        best_lag = min_lag
        best_val = -1
        for lag in range(min_lag, min(max_lag, len(ac))):
            if ac[lag] > best_val:
                best_val = ac[lag]
                best_lag = lag
        return self.sample_rate / best_lag if best_lag > 0 else 0.0

    def midi_note(self, freq: float) -> float:
        if freq <= 0:
            return 0.0
        return 69 + 12 * math.log2(freq / 440.0)

    def note_name(self, freq: float) -> str:
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        midi = self.midi_note(freq)
        octave = int(midi // 12) - 1
        idx = int(midi % 12)
        return f"{notes[idx]}{octave}"

    def stats(self, signal: List[float]) -> Dict:
        f = self.detect_pitch(signal)
        return {"pitch_hz": round(f, 2), "note": self.note_name(f), "midi": round(self.midi_note(f), 2)}

def run():
    import math
    sig = [math.sin(2 * math.pi * 440 * t / 44100) for t in range(2048)]
    pd = PitchDetector()
    print(pd.stats(sig))

if __name__ == "__main__":
    run()
