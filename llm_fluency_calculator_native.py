"""Native stdlib module: Fluency Calculator
Calculates stuttering frequency, severity, and speech rate.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class FluencyCalculator:
    total_syllables: int
    stuttered_syllables: int
    total_words: int
    speaking_time_min: float
    prolongation_count: int
    block_count: int
    repetition_count: int

    def percent_syllables_stuttered(self) -> float:
        if self.total_syllables == 0:
            return 0.0
        return (self.stuttered_syllables / self.total_syllables) * 100

    def speech_rate_syllables_per_min(self) -> float:
        if self.speaking_time_min == 0:
            return 0.0
        return self.total_syllables / self.speaking_time_min

    def speech_rate_words_per_min(self) -> float:
        if self.speaking_time_min == 0:
            return 0.0
        return self.total_words / self.speaking_time_min

    def stuttering_moments_per_min(self) -> float:
        if self.speaking_time_min == 0:
            return 0.0
        return (self.prolongation_count + self.block_count + self.repetition_count) / self.speaking_time_min

    def severity(self) -> str:
        pss = self.percent_syllables_stuttered()
        if pss < 1:
            return "very_mild"
        elif pss < 5:
            return "mild"
        elif pss < 10:
            return "moderate"
        elif pss < 20:
            return "severe"
        return "very_severe"

    def stuttering_type_breakdown(self) -> Dict:
        total = self.prolongation_count + self.block_count + self.repetition_count
        if total == 0:
            return {"prolongation": 0, "block": 0, "repetition": 0}
        return {
            "prolongation_pct": round((self.prolongation_count / total) * 100, 1),
            "block_pct": round((self.block_count / total) * 100, 1),
            "repetition_pct": round((self.repetition_count / total) * 100, 1),
        }

    def stats(self) -> Dict:
        return {
            "total_syllables": self.total_syllables,
            "stuttered_syllables": self.stuttered_syllables,
            "pss_pct": round(self.percent_syllables_stuttered(), 1),
            "speech_rate_spm": round(self.speech_rate_syllables_per_min(), 1),
            "speech_rate_wpm": round(self.speech_rate_words_per_min(), 1),
            "stuttering_moments_per_min": round(self.stuttering_moments_per_min(), 1),
            "severity": self.severity(),
            "type_breakdown": self.stuttering_type_breakdown(),
        }

def run():
    fc = FluencyCalculator(total_syllables=300, stuttered_syllables=25, total_words=200, speaking_time_min=2, prolongation_count=3, block_count=5, repetition_count=8)
    print(fc.stats())

if __name__ == "__main__":
    run()
