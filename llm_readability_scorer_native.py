"""Readability Scorer — Flesch-Kincaid, Gunning Fog, SMOG, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re, math

@dataclass
class ReadabilityScorer:
    text: str = ""

    def _counts(self) -> Tuple[int, int, int, int]:
        sentences = len(re.findall(r'[.!?]+', self.text)) or 1
        words = len(re.findall(r'\w+', self.text)) or 1
        syllables = sum(max(1, len(w) // 3) for w in re.findall(r'\w+', self.text))
        complex_words = sum(1 for w in re.findall(r'\w+', self.text) if max(1, len(w) // 3) >= 3)
        return sentences, words, syllables, complex_words

    def flesch_reading_ease(self) -> float:
        s, w, sy, _ = self._counts()
        return 206.835 - 1.015 * (w / s) - 84.6 * (sy / w)

    def flesch_kincaid_grade(self) -> float:
        s, w, sy, _ = self._counts()
        return 0.39 * (w / s) + 11.8 * (sy / w) - 15.59

    def gunning_fog(self) -> float:
        s, w, _, cw = self._counts()
        return 0.4 * ((w / s) + 100 * (cw / w))

    def smog_index(self) -> float:
        sentences = len(re.findall(r'[.!?]+', self.text)) or 1
        complex_words = sum(1 for w in re.findall(r'\w+', self.text) if max(1, len(w) // 3) >= 3)
        return math.sqrt(complex_words * (30 / sentences)) + 3 if sentences > 0 else 0

    def grade_level(self) -> str:
        fk = self.flesch_kincaid_grade()
        if fk < 6: return "elementary"
        elif fk < 9: return "middle school"
        elif fk < 13: return "high school"
        elif fk < 16: return "college"
        return "graduate"

    def stats(self) -> Dict:
        return {
            "flesch": round(self.flesch_reading_ease(), 1),
            "fk_grade": round(self.flesch_kincaid_grade(), 1),
            "gunning_fog": round(self.gunning_fog(), 1),
            "smog": round(self.smog_index(), 1),
            "grade": self.grade_level()
        }

def run():
    text = "The cat sat on the mat. It was very comfortable. The sun was shining brightly."
    rs = ReadabilityScorer(text)
    print(rs.stats())

if __name__ == "__main__":
    run()
