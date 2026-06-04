"""Extractive Summarizer — sentence scoring, ranking, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import re
from collections import Counter

@dataclass
class SentenceScore:
    sentence: str
    score: float
    index: int

class ExtractiveSummarizer:
    def __init__(self, compression_ratio: float = 0.3):
        self.compression_ratio = compression_ratio

    def _tokenize_sentences(self, text: str) -> List[str]:
        return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

    def _score_tf_idf(self, sentences: List[str]) -> List[float]:
        word_freq = Counter()
        for s in sentences:
            words = re.findall(r'\w+', s.lower())
            word_freq.update(words)
        scores = []
        for s in sentences:
            words = re.findall(r'\w+', s.lower())
            score = sum(word_freq[w] for w in words) / (len(words) + 1)
            scores.append(score)
        return scores

    def _score_position(self, sentences: List[str]) -> List[float]:
        n = len(sentences)
        return [1.0 - abs(i - n * 0.2) / n for i in range(n)]

    def summarize(self, text: str, num_sentences: Optional[int] = None) -> str:
        sentences = self._tokenize_sentences(text)
        if not sentences:
            return ""
        n = num_sentences or max(1, int(len(sentences) * self.compression_ratio))
        tf_scores = self._score_tf_idf(sentences)
        pos_scores = self._score_position(sentences)
        combined = [tf_scores[i] + pos_scores[i] for i in range(len(sentences))]
        scored = [SentenceScore(sentences[i], combined[i], i) for i in range(len(sentences))]
        scored.sort(key=lambda x: x.score, reverse=True)
        top = scored[:n]
        top.sort(key=lambda x: x.index)
        return ". ".join(s.sentence for s in top) + "."

    def stats(self) -> Dict:
        return {"compression_ratio": self.compression_ratio, "method": "tf-idf + position"}

def run():
    summarizer = ExtractiveSummarizer(0.3)
    text = "The quick brown fox jumps over the lazy dog. Foxes are wild animals. Dogs are domestic pets. This sentence is about animals in general. Many people love pets. The dog barked loudly."
    print(summarizer.summarize(text))
    print(summarizer.stats())

if __name__ == "__main__":
    run()
