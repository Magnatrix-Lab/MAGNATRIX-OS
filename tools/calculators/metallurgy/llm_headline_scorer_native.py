"""Native stdlib module: Headline Scorer
Scores headlines by length, keyword density, and emotional impact.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class HeadlineScorer:
    headline: str

    def word_count(self) -> int:
        return len(self.headline.split())

    def char_count(self) -> int:
        return len(self.headline)

    def has_numbers(self) -> bool:
        return any(c.isdigit() for c in self.headline)

    def has_power_words(self) -> bool:
        power_words = {"breakthrough", "exclusive", "revealed", "shocking", "urgent", "secret", "official", "confirmed"}
        return any(word in self.headline.lower() for word in power_words)

    def has_question(self) -> bool:
        return "?" in self.headline

    def score(self) -> float:
        score = 5.0
        wc = self.word_count()
        if 6 <= wc <= 12:
            score += 2.0
        elif wc < 6:
            score += 0.5
        elif wc > 15:
            score -= 1.0
        if self.has_numbers():
            score += 1.5
        if self.has_power_words():
            score += 2.0
        if self.has_question():
            score += 1.0
        if self.char_count() > 70:
            score -= 1.0
        return max(0, min(10, score))

    def stats(self) -> Dict:
        return {
            "headline": self.headline,
            "word_count": self.word_count(),
            "char_count": self.char_count(),
            "has_numbers": self.has_numbers(),
            "has_power_words": self.has_power_words(),
            "has_question": self.has_question(),
            "score": round(self.score(), 1),
        }

def run():
    hs = HeadlineScorer(headline="BREAKTHROUGH: New Treatment Revealed After 10 Years of Research")
    print(hs.stats())

if __name__ == "__main__":
    run()
