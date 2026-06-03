"""LLM Music Pattern Generator — Native Python (stdlib only)."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class Scale(Enum):
    MAJOR = auto()
    MINOR = auto()
    PENTATONIC = auto()
    BLUES = auto()
    CHROMATIC = auto()

@dataclass
class Note:
    pitch: int
    duration: float
    velocity: int = 100

class MusicPatternGenerator:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._scales: Dict[Scale, List[int]] = {
            Scale.MAJOR: [0, 2, 4, 5, 7, 9, 11],
            Scale.MINOR: [0, 2, 3, 5, 7, 8, 10],
            Scale.PENTATONIC: [0, 2, 4, 7, 9],
            Scale.BLUES: [0, 3, 5, 6, 7, 10],
            Scale.CHROMATIC: list(range(12))
        }

    def generate_melody(self, scale: Scale, length: int = 8, base_octave: int = 4) -> List[Note]:
        intervals = self._scales.get(scale, self._scales[Scale.MAJOR])
        notes = []
        for _ in range(length):
            interval = self._rng.choice(intervals)
            pitch = base_octave * 12 + interval
            duration = self._rng.choice([0.25, 0.5, 1.0])
            velocity = self._rng.randint(60, 127)
            notes.append(Note(pitch, duration, velocity))
        return notes

    def generate_chord_progression(self, scale: Scale, num_chords: int = 4) -> List[List[int]]:
        intervals = self._scales.get(scale, self._scales[Scale.MAJOR])
        chords = []
        for _ in range(num_chords):
            root = self._rng.choice(intervals)
            chord = [root, (root + 4) % 12, (root + 7) % 12]
            chords.append(chord)
        return chords

    def generate_rhythm(self, beats: int = 4, density: float = 0.5) -> List[bool]:
        pattern = []
        for _ in range(beats * 4):
            pattern.append(self._rng.random() < density)
        return pattern

    def get_stats(self) -> Dict[str, Any]:
        return {"scales": len(self._scales), "notes_per_octave": 12}

def run() -> None:
    print("Music Pattern Generator test")
    e = MusicPatternGenerator(seed=42)
    melody = e.generate_melody(Scale.MAJOR, 8)
    print("  Melody: " + str([(n.pitch, n.duration) for n in melody]))
    chords = e.generate_chord_progression(Scale.MINOR, 4)
    print("  Chords: " + str(chords))
    rhythm = e.generate_rhythm(4, 0.6)
    print("  Rhythm: " + str(rhythm))
    print("  Stats: " + str(e.get_stats()))
    print("Music Pattern Generator test complete.")

if __name__ == "__main__":
    run()
