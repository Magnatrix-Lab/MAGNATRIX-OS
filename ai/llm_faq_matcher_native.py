"""FAQ Matcher - Question-answer matching for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import re
from collections import Counter
import math

@dataclass
class FAQMatcher:
    faqs: List[Dict[str, str]] = field(default_factory=list)
    
    def add_faq(self, question: str, answer: str) -> None:
        self.faqs.append({"question": question, "answer": answer, "tokens": set(re.findall(r"[a-zA-Z]+", question.lower()))})
    
    def match(self, query: str) -> Tuple[str, float]:
        query_tokens = set(re.findall(r"[a-zA-Z]+", query.lower()))
        best_match = ""
        best_score = -1.0
        for faq in self.faqs:
            intersection = query_tokens & faq["tokens"]
            union = query_tokens | faq["tokens"]
            score = len(intersection) / len(union) if union else 0.0
            if score > best_score:
                best_score = score
                best_match = faq["answer"]
        return best_match, best_score
    
    def stats(self) -> dict:
        return {"faqs": len(self.faqs), "avg_tokens": sum(len(f["tokens"]) for f in self.faqs) / len(self.faqs) if self.faqs else 0}

def run():
    fm = FAQMatcher()
    fm.add_faq("What is AI?", "AI stands for Artificial Intelligence.")
    fm.add_faq("How does ML work?", "Machine Learning uses algorithms to learn from data.")
    fm.add_faq("What is Python?", "Python is a programming language.")
    answer, score = fm.match("Tell me about artificial intelligence")
    print(f"Match: {answer} (score: {score:.4f})")
    print("Stats:", fm.stats())

if __name__ == "__main__": run()
