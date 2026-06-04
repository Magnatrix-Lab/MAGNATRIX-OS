"""Intent Classifier - Intent detection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import Counter
import re
import math

@dataclass
class IntentClassifier:
    intents: Dict[str, List[str]] = field(default_factory=dict)
    vocab: Dict[str, int] = field(default_factory=dict)

    def train(self, examples: Dict[str, List[str]]) -> None:
        self.intents = examples
        all_words = []
        for utterances in examples.values():
            for u in utterances:
                all_words.extend(re.findall(r"[a-zA-Z0-9]+", u.lower()))
        self.vocab = {w: i for i, w in enumerate(set(all_words))}

    def classify(self, text: str) -> Tuple[str, float]:
        words = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
        best_intent = "unknown"
        best_score = -1
        for intent, utterances in self.intents.items():
            intent_words = set()
            for u in utterances:
                intent_words.update(re.findall(r"[a-zA-Z0-9]+", u.lower()))
            score = len(words & intent_words) / max(len(words), 1)
            if score > best_score:
                best_score = score
                best_intent = intent
        return best_intent, best_score

    def stats(self) -> dict:
        return {"intents": len(self.intents), "vocab": len(self.vocab)}

def run():
    ic = IntentClassifier()
    ic.train({"greeting": ["hello", "hi", "hey there"], "goodbye": ["bye", "see you", "goodbye"], "help": ["help me", "I need help", "assist me"]})
    print("Classify 'hi there':", ic.classify("hi there"))
    print("Stats:", ic.stats())

if __name__ == "__main__": run()
