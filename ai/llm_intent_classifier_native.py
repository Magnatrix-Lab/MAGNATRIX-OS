"""
llm_intent_classifier_native.py
MAGNATRIX-OS Intent Classifier Engine
Native Python, stdlib only.
Provides rule-based and keyword intent classification, entity extraction, and confidence scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Intent:
    name: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    matched_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "confidence": self.confidence, "entities": self.entities}


class IntentClassifierEngine:
    """Rule-based intent classification with entity extraction."""

    def __init__(self) -> None:
        self._intents: Dict[str, Dict[str, Any]] = {}  # intent_name -> {patterns, entity_extractors}
        self._fallback_intent = "unknown"

    def register_intent(self, name: str, patterns: List[str], entity_extractors: Optional[Dict[str, str]] = None) -> None:
        self._intents[name] = {
            "patterns": [re.compile(p, re.IGNORECASE) for p in patterns],
            "entity_extractors": entity_extractors or {},
        }

    def classify(self, text: str) -> Intent:
        text_lower = text.lower()
        best_intent = self._fallback_intent
        best_confidence = 0.0
        matched_patterns = []
        entities = {}

        for intent_name, config in self._intents.items():
            matches = 0
            for pattern in config["patterns"]:
                if pattern.search(text):
                    matches += 1
                    matched_patterns.append(pattern.pattern)

            if matches > 0:
                confidence = min(1.0, matches / len(config["patterns"]) + 0.1 * matches)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_intent = intent_name
                    # Extract entities
                    for entity_name, extractor_pattern in config["entity_extractors"].items():
                        match = re.search(extractor_pattern, text, re.IGNORECASE)
                        if match:
                            entities[entity_name] = match.group(1) if match.groups() else match.group(0)

        return Intent(name=best_intent, confidence=best_confidence, entities=entities, matched_patterns=matched_patterns)

    def batch_classify(self, texts: List[str]) -> List[Intent]:
        return [self.classify(t) for t in texts]

    def get_intents(self) -> List[str]:
        return list(self._intents.keys())

    def get_stats(self) -> Dict[str, Any]:
        return {"intents": len(self._intents), "total_patterns": sum(len(c["patterns"]) for c in self._intents.values())}


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Intent Classifier Engine")
    print("=" * 60)

    engine = IntentClassifierEngine()

    engine.register_intent("greeting", [r"hello", r"hi", r"hey", r"good morning", r"good afternoon"])
    engine.register_intent("farewell", [r"bye", r"goodbye", r"see you", r"later"])
    engine.register_intent("weather", [r"weather", r"temperature", r"forecast", r"rain"], {"location": r"in (\w+)"})
    engine.register_intent("search", [r"search", r"find", r"look up", r"lookup"], {"query": r"for (.+)"})

    tests = [
        "Hello there!",
        "What's the weather in Paris?",
        "Search for best pizza recipes",
        "Goodbye!",
        "Random unrelated text",
    ]

    for text in tests:
        intent = engine.classify(text)
        print(f"\n  '{text}' -> {intent.name} (conf={intent.confidence:.2f})")
        if intent.entities:
            print(f"    Entities: {intent.entities}")

    print("\nIntent Classifier test complete.")


if __name__ == "__main__":
    run()
