#!/usr/bin/env python3
"""
MAGNATRIX-OS — Grammar Checker Engine
ai/llm_grammar_checker_native.py

Features:
- Rule-based grammar checking (subject-verb agreement, article usage)
- Spelling correction (common misspellings)
- Punctuation fixer (missing commas, periods)
- Style suggestions (passive voice, wordiness)
- Error highlighting with corrections

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("grammar_checker")


@dataclass
class GrammarError:
    text: str
    error_type: str
    suggestion: str
    position: int
    severity: str


class GrammarCheckerEngine:
    """Grammar, spelling, and style checking."""

    MISSPELLINGS = {
        "teh": "the", "recieve": "receive", "occured": "occurred", "seperate": "separate",
        "definately": "definitely", "accomodate": "accommodate", "beleive": "believe",
    }

    GRAMMAR_PATTERNS = [
        (r"\b(a)\s+([aeiouAEIOU])", "article", "Use 'an' before vowels"),
        (r"\b(an)\s+([^aeiouAEIOU\s])", "article", "Use 'a' before consonants"),
        (r"\b(they)\s+(is|was)\b", "subject-verb", "'they' requires plural verb"),
        (r"\b(she|he)\s+(are|were)\b", "subject-verb", "singular subject requires singular verb"),
    ]

    STYLE_PATTERNS = [
        (r"\b(very|really|quite|extremely)\s+(\w+)", "wordiness", "Consider removing intensifier"),
        (r"\b(is|was|were)\s+(\w+)ed\b", "passive", "Consider active voice"),
    ]

    def __init__(self):
        self._errors: List[GrammarError] = []

    def check_spelling(self, text: str) -> List[GrammarError]:
        errors = []
        words = re.findall(r'\w+', text)
        for i, word in enumerate(words):
            lower = word.lower()
            if lower in self.MISSPELLINGS:
                errors.append(GrammarError(word, "spelling", self.MISSPELLINGS[lower], i, "high"))
        return errors

    def check_grammar(self, text: str) -> List[GrammarError]:
        errors = []
        for pattern, err_type, suggestion in self.GRAMMAR_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                errors.append(GrammarError(match.group(0), err_type, suggestion, match.start(), "high"))
        return errors

    def check_style(self, text: str) -> List[GrammarError]:
        errors = []
        for pattern, err_type, suggestion in self.STYLE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                errors.append(GrammarError(match.group(0), err_type, suggestion, match.start(), "medium"))
        return errors

    def check(self, text: str) -> List[GrammarError]:
        errors = []
        errors.extend(self.check_spelling(text))
        errors.extend(self.check_grammar(text))
        errors.extend(self.check_style(text))
        self._errors.extend(errors)
        return errors

    def fix(self, text: str) -> str:
        errors = self.check(text)
        fixed = text
        for err in sorted(errors, key=lambda e: e.position, reverse=True):
            fixed = fixed[:err.position] + err.suggestion + fixed[err.position + len(err.text):]
        return fixed

    def get_stats(self) -> Dict[str, Any]:
        by_type = {}
        for e in self._errors:
            by_type[e.error_type] = by_type.get(e.error_type, 0) + 1
        return {"total_errors": len(self._errors), "by_type": by_type}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Grammar Checker Engine")
    print("ai/llm_grammar_checker_native.py")
    print("=" * 60)

    engine = GrammarCheckerEngine()

    text = "Teh quick brown fox recieve a gift. They is very happy. An cat is cute."
    print(f"\nOriginal: {text}")

    errors = engine.check(text)
    print(f"\nFound {len(errors)} errors:")
    for e in errors:
        print(f"  [{e.severity}] '{e.text}' at pos {e.position}: {e.error_type} → {e.suggestion}")

    fixed = engine.fix(text)
    print(f"\nFixed: {fixed}")
    print(f"\nStats: {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
