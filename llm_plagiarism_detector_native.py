"""Plagiarism Detector — n-gram, similarity, fingerprint, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import re

@dataclass
class PlagiarismDetector:
    n: int = 3

    def ngrams(self, text: str) -> Set[str]:
        words = re.findall(r'\w+', text.lower())
        return set(' '.join(words[i:i+self.n]) for i in range(len(words) - self.n + 1)) if len(words) >= self.n else set(words)

    def similarity(self, a: str, b: str) -> float:
        g1 = self.ngrams(a)
        g2 = self.ngrams(b)
        if not g1 or not g2:
            return 0.0
        return len(g1 & g2) / len(g1 | g2)

    def fingerprint(self, text: str) -> int:
        words = re.findall(r'\w+', text.lower())
        return sum(hash(w) for w in words) % (2**32)

    def check_against_corpus(self, text: str, corpus: List[str]) -> List[Tuple[str, float]]:
        results = []
        for doc in corpus:
            sim = self.similarity(text, doc)
            if sim > 0.1:
                results.append((doc[:50], sim))
        return sorted(results, key=lambda x: x[1], reverse=True)

    def stats(self, text: str, corpus: List[str]) -> Dict:
        matches = self.check_against_corpus(text, corpus)
        return {"checked": len(corpus), "matches": len(matches), "max_similarity": round(matches[0][1], 3) if matches else 0}

def run():
    pd = PlagiarismDetector()
    text = "The quick brown fox jumps over the lazy dog"
    corpus = ["The quick brown fox jumps over the lazy dog", "Something completely different", "The quick brown fox runs"]
    print(pd.stats(text, corpus))
    print("Similarity:", pd.similarity(text, corpus[2]))

if __name__ == "__main__":
    run()
