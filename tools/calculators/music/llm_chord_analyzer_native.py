"""Chord Analyzer — chord detection, progression, harmony, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class ChordAnalyzer:
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def note_to_midi(self, note: str) -> int:
        n = note[:-1] if len(note) > 1 else note
        octave = int(note[-1]) if note[-1].isdigit() else 4
        idx = self.notes.index(n) if n in self.notes else 0
        return idx + (octave + 1) * 12

    def chord_from_notes(self, notes: List[str]) -> str:
        if len(notes) < 3:
            return ""
        midi = sorted([self.note_to_midi(n) % 12 for n in notes])
        intervals = [(midi[i] - midi[0]) % 12 for i in range(len(midi))]
        if intervals == [0, 4, 7]:
            return f"{self.notes[midi[0]]} major"
        elif intervals == [0, 3, 7]:
            return f"{self.notes[midi[0]]} minor"
        elif intervals == [0, 4, 7, 10]:
            return f"{self.notes[midi[0]]}7"
        elif intervals == [0, 3, 7, 10]:
            return f"{self.notes[midi[0]]}m7"
        return f"{self.notes[midi[0]]} unknown"

    def progression(self, chords: List[str]) -> List[str]:
        return chords

    def circle_of_fifths(self, key: str) -> List[str]:
        idx = self.notes.index(key) if key in self.notes else 0
        return [self.notes[(idx + i * 7) % 12] for i in range(12)]

    def stats(self, chords: List[str]) -> Dict:
        return {"chords": len(chords), "unique": len(set(chords))}

def run():
    ca = ChordAnalyzer()
    print("Chord:", ca.chord_from_notes(["C4", "E4", "G4"]))
    print("Circle:", ca.circle_of_fifths("C"))
    print(ca.stats(["C major", "G major", "A minor"]))

if __name__ == "__main__":
    run()
