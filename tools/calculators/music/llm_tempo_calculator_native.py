"""Native stdlib module: Tempo Calculator
Calculates BPM, delay times, and note durations for music production.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class TempoCalculator:
    bpm: float
    time_signature_numerator: int = 4
    time_signature_denominator: int = 4

    def quarter_note_ms(self) -> float:
        if self.bpm == 0:
            return 0.0
        return 60000 / self.bpm

    def eighth_note_ms(self) -> float:
        return self.quarter_note_ms() / 2

    def sixteenth_note_ms(self) -> float:
        return self.quarter_note_ms() / 4

    def half_note_ms(self) -> float:
        return self.quarter_note_ms() * 2

    def whole_note_ms(self) -> float:
        return self.quarter_note_ms() * 4

    def dotted_quarter_ms(self) -> float:
        return self.quarter_note_ms() * 1.5

    def triplet_quarter_ms(self) -> float:
        return self.quarter_note_ms() * (2/3)

    def bar_duration_ms(self) -> float:
        return self.quarter_note_ms() * self.time_signature_numerator

    def delay_times_ms(self) -> Dict[str, float]:
        return {
            "1/1": round(self.whole_note_ms(), 2),
            "1/2": round(self.half_note_ms(), 2),
            "1/4": round(self.quarter_note_ms(), 2),
            "1/8": round(self.eighth_note_ms(), 2),
            "1/16": round(self.sixteenth_note_ms(), 2),
            "1/4d": round(self.dotted_quarter_ms(), 2),
            "1/4t": round(self.triplet_quarter_ms(), 2),
        }

    def stats(self) -> Dict:
        return {
            "bpm": self.bpm,
            "time_signature": f"{self.time_signature_numerator}/{self.time_signature_denominator}",
            "quarter_note_ms": round(self.quarter_note_ms(), 2),
            "bar_duration_ms": round(self.bar_duration_ms(), 2),
            "delay_times_ms": self.delay_times_ms(),
        }

def run():
    tc = TempoCalculator(bpm=120, time_signature_numerator=4, time_signature_denominator=4)
    print(tc.stats())

if __name__ == "__main__":
    run()
