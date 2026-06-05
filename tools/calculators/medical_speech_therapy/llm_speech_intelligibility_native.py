"""Native stdlib module: Speech Intelligibility Calculator
Calculates speech intelligibility scores and severity ratings.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Severity(Enum):
    NORMAL = "normal"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    PROFOUND = "profound"

@dataclass
class WordTranscription:
    target_word: str
    transcribed_word: str

@dataclass
class SpeechIntelligibilityCalculator:
    patient_name: str
    age: int
    transcriptions: List[WordTranscription] = field(default_factory=list)

    def correct_words(self) -> int:
        return sum(1 for t in self.transcriptions if t.target_word.lower() == t.transcribed_word.lower())

    def intelligibility_pct(self) -> float:
        if not self.transcriptions:
            return 0.0
        return (self.correct_words() / len(self.transcriptions)) * 100

    def severity(self) -> Severity:
        pct = self.intelligibility_pct()
        if pct >= 95:
            return Severity.NORMAL
        elif pct >= 80:
            return Severity.MILD
        elif pct >= 50:
            return Severity.MODERATE
        elif pct >= 25:
            return Severity.SEVERE
        return Severity.PROFOUND

    def word_count(self) -> int:
        return len(self.transcriptions)

    def phoneme_error_rate(self, target_phonemes: int, correct_phonemes: int) -> float:
        if target_phonemes == 0:
            return 0.0
        return ((target_phonemes - correct_phonemes) / target_phonemes) * 100

    def estimated_age_equivalent(self) -> float:
        pct = self.intelligibility_pct()
        if pct >= 95:
            return self.age
        elif pct >= 80:
            return max(2, self.age - 2)
        elif pct >= 50:
            return max(2, self.age - 5)
        return max(2, self.age - 8)

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "age": self.age,
            "words_tested": self.word_count(),
            "correct_words": self.correct_words(),
            "intelligibility_pct": round(self.intelligibility_pct(), 1),
            "severity": self.severity().value,
            "age_equivalent": round(self.estimated_age_equivalent(), 1),
        }

def run():
    sic = SpeechIntelligibilityCalculator(
        patient_name="Child-A",
        age=5,
        transcriptions=[
            WordTranscription("cat", "cat"),
            WordTranscription("dog", "tog"),
            WordTranscription("fish", "fish"),
            WordTranscription("bird", "buh"),
            WordTranscription("elephant", "ephant"),
            WordTranscription("monkey", "monkey"),
            WordTranscription("tiger", "tiger"),
            WordTranscription("lion", "wion"),
            WordTranscription("bear", "bear"),
            WordTranscription("snake", "nake"),
        ]
    )
    print(sic.stats())

if __name__ == "__main__":
    run()
