"""Melody Generator — Markov chains, scales, arpeggios, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random, math

@dataclass
class MelodyGenerator:
    scale = [0, 2, 4, 5, 7, 9, 11]
    """C major semitone offsets"""
    transitions: Dict[int, List[int]] = field(default_factory=dict)

    def train_markov(self, melodies: List[List[int]]):
        for mel in melodies:
            for i in range(len(mel) - 1):
                self.transitions.setdefault(mel[i], []).append(mel[i+1])

    def generate_markov(self, start: int, length: int = 16) -> List[int]:
        result = [start]
        for _ in range(length - 1):
            next_notes = self.transitions.get(result[-1], self.scale)
            result.append(random.choice(next_notes) if next_notes else result[-1])
        return result

    def arpeggio(self, root: int, chord_type: str = "major", length: int = 8) -> List[int]:
        if chord_type == "major":
            intervals = [0, 4, 7, 12]
        elif chord_type == "minor":
            intervals = [0, 3, 7, 12]
        else:
            intervals = [0, 4, 7, 12]
        return [(root + intervals[i % len(intervals)]) % 128 for i in range(length)]

    def scale_walk(self, root: int, length: int = 16) -> List[int]:
        result = [root]
        for _ in range(length - 1):
            step = random.choice([-2, -1, 0, 1, 2])
            new = result[-1] + step
            result.append(max(0, min(127, new)))
        return result

    def notes_to_names(self, midi_notes: List[int]) -> List[str]:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return [f"{names[n % 12]}{n // 12 - 1}" for n in midi_notes]

    def stats(self, melody: List[int]) -> Dict:
        return {"notes": len(melody), "range": max(melody) - min(melody) if melody else 0}

def run():
    mg = MelodyGenerator()
    mg.train_markov([[60,62,64,65],[60,64,67,72]])
    print("Markov:", mg.generate_markov(60, 8))
    print("Arpeggio:", mg.arpeggio(60, "major", 8))
    print("Walk:", mg.scale_walk(60, 8))
    print(mg.stats(mg.scale_walk(60, 8)))

if __name__ == "__main__":
    run()
