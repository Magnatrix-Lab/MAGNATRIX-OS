"""Text Summarizer - Extractive summarization for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import Counter
import re
import math

@dataclass
class TextSummarizer:
    ratio: float = 0.3

    def score_sentences(self, sentences: List[str]) -> List[Tuple[int, float]]:
        word_freq = Counter()
        for s in sentences:
            words = re.findall(r"[a-zA-Z0-9]+", s.lower())
            word_freq.update(words)
        scores = []
        for i, s in enumerate(sentences):
            words = re.findall(r"[a-zA-Z0-9]+", s.lower())
            if words:
                score = sum(word_freq[w] for w in words) / len(words)
                scores.append((i, score))
        return scores

    def summarize(self, text: str, num_sentences: int = 3) -> List[str]:
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        scores = self.score_sentences(sentences)
        top_indices = sorted(scores, key=lambda x: x[1], reverse=True)[:num_sentences]
        top_indices = sorted([i for i, _ in top_indices])
        return [sentences[i] for i in top_indices]

    def stats(self, text: str) -> dict:
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        return {"sentences": len(sentences), "summary_len": max(1, int(len(sentences) * self.ratio))}

def run():
    ts = TextSummarizer(0.3)
    text = "Machine learning is a subset of AI. Deep learning is a subset of machine learning. Neural networks are used in deep learning. AI is transforming industries. Natural language processing is a field of AI."
    print("Summary:", ts.summarize(text, 2))
    print("Stats:", ts.stats(text))

if __name__ == "__main__": run()
