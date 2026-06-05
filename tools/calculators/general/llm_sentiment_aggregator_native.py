"""Sentiment Aggregator — aggregation, polarity, aspect-based, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re

@dataclass
class SentimentAggregator:
    positive_words: set = field(default_factory=lambda: {"good","great","excellent","love","happy","best","amazing"})
    negative_words: set = field(default_factory=lambda: {"bad","terrible","hate","worst","awful","poor","sad"})

    def score(self, text: str) -> float:
        words = re.findall(r'\w+', text.lower())
        pos = sum(1 for w in words if w in self.positive_words)
        neg = sum(1 for w in words if w in self.negative_words)
        total = pos + neg
        if total == 0:
            return 0.0
        return (pos - neg) / total

    def aggregate(self, texts: List[str]) -> Dict:
        scores = [self.score(t) for t in texts]
        return {"mean": sum(scores)/len(scores) if scores else 0, "positive_pct": sum(1 for s in scores if s > 0)/len(scores)*100 if scores else 0, "negative_pct": sum(1 for s in scores if s < 0)/len(scores)*100 if scores else 0, "neutral_pct": sum(1 for s in scores if s == 0)/len(scores)*100 if scores else 0}

    def aspect_sentiment(self, text: str, aspects: List[str]) -> Dict[str, float]:
        result = {}
        for aspect in aspects:
            pattern = re.compile(r'[^.]*' + aspect + r'[^.]*\.')
            sentences = pattern.findall(text.lower())
            if sentences:
                scores = [self.score(s) for s in sentences]
                result[aspect] = sum(scores) / len(scores)
            else:
                result[aspect] = 0.0
        return result

    def stats(self, texts: List[str]) -> Dict:
        return {"texts": len(texts), "aggregate": self.aggregate(texts)}

def run():
    sa = SentimentAggregator()
    texts = ["I love this product. Great quality!", "Terrible service. Bad experience.", "It was okay."]
    print(sa.aggregate(texts))
    print(sa.aspect_sentiment("The camera is great but battery is bad", ["camera", "battery"]))
    print(sa.stats(texts))

if __name__ == "__main__":
    run()
