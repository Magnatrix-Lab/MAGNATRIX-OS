"""Review Analyzer — sentiment, aspects, rating predictor, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import re

@dataclass
class ReviewAnalyzer:
    positive_words: set = field(default_factory=lambda: {"excellent", "great", "amazing", "perfect", "love", "beautiful", "clean", "friendly"})
    negative_words: set = field(default_factory=lambda: {"terrible", "worst", "dirty", "rude", "awful", "horrible", "bad", "disappointing"})
    aspects: Dict[str, List[str]] = field(default_factory=lambda: {
        "cleanliness": ["clean", "dirty", "tidy", "messy"],
        "service": ["friendly", "rude", "helpful", "unprofessional"],
        "location": ["convenient", "remote", "central", "noisy"],
        "value": ["cheap", "expensive", "worth", "overpriced"]
    })

    def sentiment_score(self, text: str) -> float:
        words = set(re.findall(r'\w+', text.lower()))
        pos = len(words & self.positive_words)
        neg = len(words & self.negative_words)
        total = pos + neg
        return (pos - neg) / total if total > 0 else 0.0

    def aspect_scores(self, text: str) -> Dict[str, float]:
        words = set(re.findall(r'\w+', text.lower()))
        scores = {}
        for aspect, keywords in self.aspects.items():
            matches = len(words & set(keywords))
            scores[aspect] = matches / len(keywords) if keywords else 0.0
        return scores

    def predicted_rating(self, text: str) -> float:
        score = self.sentiment_score(text)
        return max(1, min(5, 3 + score * 2))

    def summarize(self, reviews: List[str]) -> Dict:
        avg_sentiment = sum(self.sentiment_score(r) for r in reviews) / len(reviews) if reviews else 0
        avg_rating = sum(self.predicted_rating(r) for r in reviews) / len(reviews) if reviews else 0
        return {"avg_sentiment": round(avg_sentiment, 3), "avg_rating": round(avg_rating, 1), "count": len(reviews)}

    def stats(self, text: str) -> Dict:
        return {"sentiment": round(self.sentiment_score(text), 3), "rating": round(self.predicted_rating(text), 1), "aspects": self.aspect_scores(text)}

def run():
    ra = ReviewAnalyzer()
    text = "The hotel was clean and the staff were friendly. Great location but a bit expensive."
    print(ra.stats(text))
    print("Summary:", ra.summarize([text, "Amazing place! Love it!", "Dirty room and rude staff."]))

if __name__ == "__main__":
    run()
