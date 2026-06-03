"""LLM Chord Recognizer — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class ChordRecognizer:
    def __init__(self) -> None:
        self._note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        self._chords: Dict[str, List[int]] = {
            "C": [0, 4, 7], "Cm": [0, 3, 7], "C7": [0, 4, 7, 10], "Cm7": [0, 3, 7, 10],
            "D": [2, 6, 9], "Dm": [2, 5, 9], "D7": [2, 6, 9, 11], "Dm7": [2, 5, 9, 11],
            "E": [4, 8, 11], "Em": [4, 7, 11], "E7": [4, 8, 11, 2], "Em7": [4, 7, 11, 2],
            "F": [5, 9, 0], "Fm": [5, 8, 0], "F7": [5, 9, 0, 3], "Fm7": [5, 8, 0, 3],
            "G": [7, 11, 2], "Gm": [7, 10, 2], "G7": [7, 11, 2, 5], "Gm7": [7, 10, 2, 5],
            "A": [9, 1, 4], "Am": [9, 0, 4], "A7": [9, 1, 4, 7], "Am7": [9, 0, 4, 7],
            "B": [11, 3, 6], "Bm": [11, 2, 6], "B7": [11, 3, 6, 9], "Bm7": [11, 2, 6, 9],
        }

    def midi_to_note(self, midi_note: int) -> str:
        return self._note_names[midi_note % 12] + str(midi_note // 12 - 1)

    def notes_to_chord(self, notes: List[int]) -> List[str]:
        if len(notes) < 3:
            return []
        pitch_classes = sorted(set(n % 12 for n in notes))
        matches = []
        for chord_name, intervals in self._chords.items():
            if all(i in pitch_classes for i in intervals):
                matches.append(chord_name)
        return matches

    def identify(self, notes: List[int]) -> Optional[str]:
        matches = self.notes_to_chord(notes)
        return matches[0] if matches else None

    def get_intervals(self, chord_name: str) -> List[int]:
        return self._chords.get(chord_name, [])

    def transpose(self, chord_name: str, semitones: int) -> str:
        intervals = self._chords.get(chord_name)
        if not intervals:
            return chord_name
        root = intervals[0]
        new_root = (root + semitones) % 12
        base_note = self._note_names[new_root]
        is_minor = "m" in chord_name
        has_7 = "7" in chord_name
        if is_minor and has_7:
            return base_note + "m7"
        elif has_7:
            return base_note + "7"
        elif is_minor:
            return base_note + "m"
        return base_note

    def get_stats(self) -> Dict[str, Any]:
        return {"chords": len(self._chords), "notes": len(self._note_names)}

def run() -> None:
    print("Chord Recognizer test")
    e = ChordRecognizer()
    print("  C major: " + str(e.notes_to_chord([60, 64, 67])))
    print("  Am: " + str(e.notes_to_chord([69, 72, 76])))
    print("  G7: " + str(e.notes_to_chord([67, 71, 74, 77])))
    print("  Transpose C up 2: " + e.transpose("C", 2))
    print("  Transpose Am down 3: " + e.transpose("Am", -3))
    print("  Stats: " + str(e.get_stats()))
    print("Chord Recognizer test complete.")

if __name__ == "__main__":
    run()
