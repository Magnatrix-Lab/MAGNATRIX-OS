#!/usr/bin/env python3
"""
MAGNATRIX-OS — Question Answering Engine
ai/llm_question_answering_native.py

Features:
- Context passage retrieval (find relevant passage)
- Answer span extraction (keyword matching)
- Confidence scoring (overlap-based)
- Multi-hop QA simulation (chain reasoning)
- No-answer detection (when context doesn't contain answer)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("question_answering")


@dataclass
class QAResult:
    answer: str
    confidence: float
    source_passage: str
    has_answer: bool


class QuestionAnsweringEngine:
    """Extractive question answering over context."""

    def __init__(self):
        self._passages: List[str] = []

    def add_passage(self, text: str) -> None:
        self._passages.append(text)

    def _find_relevant(self, question: str) -> Optional[str]:
        q_words = set(re.findall(r'\w+', question.lower()))
        best_passage = None
        best_score = 0
        for passage in self._passages:
            p_words = set(re.findall(r'\w+', passage.lower()))
            score = len(q_words & p_words) / len(q_words)
            if score > best_score:
                best_score = score
                best_passage = passage
        return best_passage if best_score > 0.1 else None

    def _extract_answer(self, question: str, passage: str) -> Tuple[str, float]:
        q_words = [w for w in re.findall(r'\w+', question.lower()) if w not in ["what", "where", "when", "who", "how", "why", "which", "is", "are", "was", "were", "the", "a", "an", "in", "on", "of"]]
        sentences = re.split(r'(?<=[.!?])\s+', passage)
        best = ""
        best_score = 0.0
        for sent in sentences:
            s_words = set(re.findall(r'\w+', sent.lower()))
            matches = sum(1 for w in q_words if w in s_words)
            score = matches / max(len(q_words), 1)
            if score > best_score and score < 0.9:  # Not exact match
                best_score = score
                best = sent
        if not best and sentences:
            best = max(sentences, key=lambda s: len(s))
            best_score = 0.1
        return best, best_score

    def answer(self, question: str) -> QAResult:
        passage = self._find_relevant(question)
        if not passage:
            return QAResult("No relevant passage found", 0.0, "", False)
        ans, conf = self._extract_answer(question, passage)
        has_ans = conf > 0.2
        return QAResult(ans, conf, passage, has_ans)

    def multi_hop(self, question: str, steps: int = 2) -> QAResult:
        result = self.answer(question)
        for _ in range(steps - 1):
            if not result.has_answer:
                break
            follow_up = f"What about {result.answer[:30]}?"
            next_result = self.answer(follow_up)
            if next_result.has_answer and next_result.confidence > result.confidence:
                result = next_result
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {"passages": len(self._passages)}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Question Answering Engine")
    print("ai/llm_question_answering_native.py")
    print("=" * 60)

    engine = QuestionAnsweringEngine()

    passages = [
        "Paris is the capital of France. It has a population of 2.1 million. The Eiffel Tower is located there.",
        "Python was created by Guido van Rossum in 1991. It is a high-level programming language used for many applications.",
        "The Great Wall of China was built over many centuries. It is one of the Seven Wonders of the World.",
    ]
    for p in passages:
        engine.add_passage(p)

    questions = [
        "What is the capital of France?",
        "Who created Python?",
        "When was Python created?",
        "What is the population of Paris?",
        "What is the tallest building?",
    ]

    for q in questions:
        result = engine.answer(q)
        print(f"\nQ: {q}")
        print(f"A: {result.answer[:60]}... (conf={result.confidence:.2f}, has_answer={result.has_answer})")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
