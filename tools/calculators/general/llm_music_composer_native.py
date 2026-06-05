"""Music Composer — scales, chord progression, tempo, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class MusicComposer:
    root_note: int = 60  # MIDI C4
    scale: str = "major"
    bpm: float = 120.0

    def scale_notes(self) -> List[int]:
        intervals = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}
        return [self.root_note + i for i in intervals.get(self.scale, [0, 2, 4, 5, 7, 9, 11])]

    def chord_triad(self, degree: int = 1) -> List[int]:
        notes = self.scale_notes()
        idx = degree - 1
        return [notes[idx % 7], notes[(idx + 2) % 7], notes[(idx + 4) % 7]]

    def beat_duration_ms(self, beats: int = 1) -> float:
        return (60000.0 / self.bpm) * beats

    def stats(self) -> Dict:
        return {"scale": self.scale_notes(), "I_chord": self.chord_triad(1), "beat_ms": round(self.beat_duration_ms(), 2)}

def run():
    mc = MusicComposer(root_note=62, scale="minor", bpm=140)
    print(mc.stats())

if __name__ == "__main__":
    run()
