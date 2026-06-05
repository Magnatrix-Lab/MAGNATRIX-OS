"""Native stdlib module: Pitch Calculator
Calculates frequencies, intervals, and tuning for musical notes.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class PitchCalculator:
    reference_freq: float = 440.0
    reference_note: str = "A4"

    def note_frequency(self, semitones_from_a4: int) -> float:
        return self.reference_freq * (2 ** (semitones_from_a4 / 12))

    def interval_ratio(self, semitones: int) -> float:
        return 2 ** (semitones / 12)

    def cents_difference(self, freq1: float, freq2: float) -> float:
        if freq2 == 0:
            return 0.0
        return 1200 * math.log2(freq1 / freq2)

    def octave_freq(self, freq: float, octaves: int) -> float:
        return freq * (2 ** octaves)

    def just_intonation(self, ratio: tuple) -> float:
        if self.reference_freq == 0:
            return 0.0
        return self.reference_freq * (ratio[0] / ratio[1])

    def circle_of_fifths(self, starting_note: str = "C") -> list:
        notes = ["C", "G", "D", "A", "E", "B", "F#", "C#", "G#", "D#", "A#", "F"]
        try:
            idx = notes.index(starting_note)
        except ValueError:
            return notes
        return notes[idx:] + notes[:idx]

    def stats(self) -> Dict:
        return {
            "reference_freq": self.reference_freq,
            "reference_note": self.reference_note,
            "c4_freq": round(self.note_frequency(-9), 2),
            "e4_freq": round(self.note_frequency(-5), 2),
            "g4_freq": round(self.note_frequency(-2), 2),
            "a4_freq": round(self.note_frequency(0), 2),
            "perfect_fifth_ratio": round(self.interval_ratio(7), 4),
            "perfect_fourth_ratio": round(self.interval_ratio(5), 4),
            "major_third_ratio": round(self.interval_ratio(4), 4),
        }

def run():
    pc = PitchCalculator(reference_freq=440.0)
    print(pc.stats())

if __name__ == "__main__":
    run()
