"""Music Pattern Generator — scales, chords, rhythm, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class ScaleType(Enum):
    MAJOR = auto()
    MINOR = auto()
    PENTATONIC = auto()
    BLUES = auto()
    CHROMATIC = auto()

class MusicPatternGenerator:
    def __init__(self, base_freq: float = 440.0):
        self.base_freq = base_freq
        self.scales = {
            ScaleType.MAJOR: [0, 2, 4, 5, 7, 9, 11],
            ScaleType.MINOR: [0, 2, 3, 5, 7, 8, 10],
            ScaleType.PENTATONIC: [0, 2, 4, 7, 9],
            ScaleType.BLUES: [0, 3, 5, 6, 7, 10],
            ScaleType.CHROMATIC: list(range(12)),
        }
        self.chords = {
            "major": [0, 4, 7],
            "minor": [0, 3, 7],
            "diminished": [0, 3, 6],
            "augmented": [0, 4, 8],
            "maj7": [0, 4, 7, 11],
        }

    def note_to_freq(self, semitone: int) -> float:
        return self.base_freq * (2 ** (semitone / 12.0))

    def generate_scale(self, root: int, scale_type: ScaleType) -> List[float]:
        intervals = self.scales.get(scale_type, [])
        return [self.note_to_freq(root + i) for i in intervals]

    def generate_chord(self, root: int, chord_type: str) -> List[float]:
        intervals = self.chords.get(chord_type, [0, 4, 7])
        return [self.note_to_freq(root + i) for i in intervals]

    def generate_rhythm(self, beats: int = 16, density: float = 0.5) -> List[int]:
        import random
        random.seed(42)
        return [1 if random.random() < density else 0 for _ in range(beats)]

    def generate_progression(self, root: int, progression: List[str]) -> List[List[float]]:
        roots = [root + i for i in [0, 5, 7, 0]]
        return [self.generate_chord(roots[i % len(roots)], progression[i % len(progression)]) for i in range(len(progression))]

    def arpeggiate(self, chord: List[float], pattern: str = "up") -> List[float]:
        if pattern == "up":
            return chord
        elif pattern == "down":
            return list(reversed(chord))
        elif pattern == "updown":
            return chord + list(reversed(chord))
        return chord

    def stats(self) -> Dict:
        return {"scales": len(self.scales), "chords": len(self.chords), "base_freq": self.base_freq}

def run():
    music = MusicPatternGenerator(440.0)
    c_major = music.generate_scale(0, ScaleType.MAJOR)
    print("C Major:", [round(f, 1) for f in c_major])
    c_chord = music.generate_chord(0, "major")
    print("C Major chord:", [round(f, 1) for f in c_chord])
    print("Arpeggio:", music.arpeggiate(c_chord, "updown"))
    print(music.stats())

if __name__ == "__main__":
    run()
