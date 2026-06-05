"""Native stdlib module: Readability Scorer
Scores text readability using Flesch-Kincaid and Gunning Fog indices.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class ReadabilityScorer:
    text: str

    def word_count(self) -> int:
        return len(self.text.split())

    def sentence_count(self) -> int:
        return max(1, self.text.count(".") + self.text.count("!") + self.text.count("?"))

    def syllable_count(self) -> int:
        words = self.text.lower().split()
        count = 0
        for word in words:
            syllables = 0
            vowels = "aeiouy"
            if word[0] in vowels:
                syllables += 1
            for i in range(1, len(word)):
                if word[i] in vowels and word[i-1] not in vowels:
                    syllables += 1
            if word.endswith("e"):
                syllables -= 1
            count += max(1, syllables)
        return count

    def flesch_kincaid_ease(self) -> float:
        if self.sentence_count() == 0 or self.word_count() == 0:
            return 0.0
        return 206.835 - 1.015 * (self.word_count() / self.sentence_count()) - 84.6 * (self.syllable_count() / self.word_count())

    def flesch_kincaid_grade(self) -> float:
        if self.sentence_count() == 0 or self.word_count() == 0:
            return 0.0
        return 0.39 * (self.word_count() / self.sentence_count()) + 11.8 * (self.syllable_count() / self.word_count()) - 15.59

    def gunning_fog(self) -> float:
        if self.sentence_count() == 0 or self.word_count() == 0:
            return 0.0
        complex_words = sum(1 for w in self.text.split() if len(w) > 6)
        return 0.4 * ((self.word_count() / self.sentence_count()) + 100 * (complex_words / self.word_count()))

    def stats(self) -> Dict[str, float]:
        return {
            "flesch_kincaid_ease": round(self.flesch_kincaid_ease(), 1),
            "flesch_kincaid_grade": round(self.flesch_kincaid_grade(), 1),
            "gunning_fog": round(self.gunning_fog(), 1),
        }

def run():
    rs = ReadabilityScorer(text="The quick brown fox jumps over the lazy dog. The cat sat on the mat. A journey of a thousand miles begins with a single step.")
    print(rs.stats())

if __name__ == "__main__":
    run()
