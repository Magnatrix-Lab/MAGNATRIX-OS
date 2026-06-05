"""Advanced Sentiment Analyzer — lexicon-based, rule-based, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import re
import math

class SentimentPolarity(Enum):
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()
    MIXED = auto()

@dataclass
class SentimentResult:
    text: str
    polarity: SentimentPolarity
    score: float
    confidence: float
    aspects: Dict[str, float] = field(default_factory=dict)

class AdvancedSentimentAnalyzer:
    def __init__(self):
        self.positive_lexicon = {"good", "great", "excellent", "amazing", "love", "best", "happy", "wonderful", "fantastic", "perfect"}
        self.negative_lexicon = {"bad", "terrible", "awful", "worst", "hate", "horrible", "disappointing", "poor", "sad", "ugly"}
        self.negators = {"not", "no", "never", "none", "nobody", "nothing", "neither", "nowhere", "hardly", "barely", "scarcely"}
        self.intensifiers = {"very", "extremely", "incredibly", "absolutely", "completely", "totally", "really", "quite", "too"}
        self.diminishers = {"somewhat", "slightly", "kind of", "a bit", "fairly", "pretty", "rather", "moderately"}

    def analyze(self, text: str) -> SentimentResult:
        words = re.findall(r"\w+", text.lower())
        pos_score = 0.0
        neg_score = 0.0
        negation_active = False
        multiplier = 1.0
        for i, word in enumerate(words):
            if word in self.negators:
                negation_active = True
                continue
            if word in self.intensifiers:
                multiplier = 1.5
                continue
            if word in self.diminishers:
                multiplier = 0.5
                continue
            if word in self.positive_lexicon:
                if negation_active:
                    neg_score += 1.0 * multiplier
                    negation_active = False
                else:
                    pos_score += 1.0 * multiplier
            elif word in self.negative_lexicon:
                if negation_active:
                    pos_score += 1.0 * multiplier
                    negation_active = False
                else:
                    neg_score += 1.0 * multiplier
            multiplier = 1.0
        total = pos_score + neg_score
        if total == 0:
            return SentimentResult(text, SentimentPolarity.NEUTRAL, 0.0, 0.5)
        score = (pos_score - neg_score) / total
        if score > 0.1:
            polarity = SentimentPolarity.POSITIVE
        elif score < -0.1:
            polarity = SentimentPolarity.NEGATIVE
        else:
            polarity = SentimentPolarity.NEUTRAL
        confidence = abs(score)
        return SentimentResult(text, polarity, score, confidence)

    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        return [self.analyze(t) for t in texts]

    def stats(self) -> Dict:
        return {"positive_words": len(self.positive_lexicon), "negative_words": len(self.negative_lexicon), "negators": len(self.negators)}

def run():
    analyzer = AdvancedSentimentAnalyzer()
    texts = [
        "This product is absolutely amazing and wonderful!",
        "I am very disappointed, this is terrible and awful.",
        "The service was not bad but not great either.",
        "It is a somewhat good experience but quite poor quality.",
    ]
    for t in texts:
        r = analyzer.analyze(t)
        print(f"{r.polarity.name}: {r.score:.2f} (conf={r.confidence:.2f})")
    print(analyzer.stats())

if __name__ == "__main__":
    run()
