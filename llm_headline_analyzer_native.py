"""Headline Analyzer — sentiment, clickbait, SEO, length, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re

@dataclass
class HeadlineAnalyzer:
    text: str = ""

    def word_count(self) -> int:
        return len(self.text.split())

    def char_count(self) -> int:
        return len(self.text)

    def sentiment(self) -> str:
        positive = ["amazing", "best", "great", "win", "success", "breakthrough"]
        negative = ["worst", "crisis", "disaster", "fail", "scandal", "shocking"]
        words = self.text.lower().split()
        pos = sum(1 for w in words if w in positive)
        neg = sum(1 for w in words if w in negative)
        if pos > neg: return "positive"
        if neg > pos: return "negative"
        return "neutral"

    def clickbait_score(self) -> float:
        markers = ["you won't believe", "shocking", "secret", "this is why", "what happens next", "mind blowing"]
        text_lower = self.text.lower()
        count = sum(1 for m in markers if m in text_lower)
        return min(1.0, count / 2 + (1 if "?" in self.text else 0) * 0.3 + (1 if "!" in self.text else 0) * 0.2)

    def seo_score(self, keyword: str) -> float:
        if keyword.lower() in self.text.lower():
            return 1.0
        return 0.0

    def readability(self) -> float:
        words = self.text.split()
        if not words:
            return 0.0
        syllables = sum(max(1, len(w) // 3) for w in words)
        return 206.835 - 1.015 * len(words) - 84.6 * (syllables / len(words))

    def stats(self) -> Dict:
        return {"words": self.word_count(), "chars": self.char_count(), "sentiment": self.sentiment(), "clickbait": round(self.clickbait_score(), 2)}

def run():
    ha = HeadlineAnalyzer("Shocking Secret: You Won't Believe What Happens Next!")
    print(ha.stats())
    print("SEO 'secret':", ha.seo_score("secret"))

if __name__ == "__main__":
    run()
