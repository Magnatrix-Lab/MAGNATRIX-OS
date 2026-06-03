"""LLM POS Tagger — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class POSTag(Enum):
    NOUN = auto()
    VERB = auto()
    ADJECTIVE = auto()
    ADVERB = auto()
    PRONOUN = auto()
    PREPOSITION = auto()
    CONJUNCTION = auto()
    DETERMINER = auto()
    INTERJECTION = auto()
    NUMERAL = auto()
    PARTICLE = auto()
    UNKNOWN = auto()

class POSTagger:
    def __init__(self) -> None:
        self._lexicon: Dict[str, POSTag] = {}
        self._suffix_rules: List[tuple] = [
            ("ly", POSTag.ADVERB), ("ful", POSTag.ADJECTIVE), ("less", POSTag.ADJECTIVE),
            ("ous", POSTag.ADJECTIVE), ("ive", POSTag.ADJECTIVE), ("able", POSTag.ADJECTIVE),
            ("tion", POSTag.NOUN), ("sion", POSTag.NOUN), ("ment", POSTag.NOUN),
            ("ness", POSTag.NOUN), ("ity", POSTag.NOUN), ("er", POSTag.NOUN),
            ("or", POSTag.NOUN), ("ist", POSTag.NOUN), ("ism", POSTag.NOUN),
            ("ing", POSTag.VERB), ("ed", POSTag.VERB), ("en", POSTag.VERB),
        ]
        self._function_words: Dict[str, POSTag] = {
            "the": POSTag.DETERMINER, "a": POSTag.DETERMINER, "an": POSTag.DETERMINER,
            "and": POSTag.CONJUNCTION, "or": POSTag.CONJUNCTION, "but": POSTag.CONJUNCTION,
            "in": POSTag.PREPOSITION, "on": POSTag.PREPOSITION, "at": POSTag.PREPOSITION,
            "to": POSTag.PREPOSITION, "for": POSTag.PREPOSITION, "with": POSTag.PREPOSITION,
            "he": POSTag.PRONOUN, "she": POSTag.PRONOUN, "it": POSTag.PRONOUN,
            "they": POSTag.PRONOUN, "we": POSTag.PRONOUN, "you": POSTag.PRONOUN,
            "I": POSTag.PRONOUN, "me": POSTag.PRONOUN, "him": POSTag.PRONOUN,
            "her": POSTag.PRONOUN, "them": POSTag.PRONOUN, "us": POSTag.PRONOUN,
            "my": POSTag.PRONOUN, "your": POSTag.PRONOUN, "his": POSTag.PRONOUN,
            "this": POSTag.DETERMINER, "that": POSTag.DETERMINER, "these": POSTag.DETERMINER,
            "those": POSTag.DETERMINER, "one": POSTag.NUMERAL, "two": POSTag.NUMERAL,
            "is": POSTag.VERB, "are": POSTag.VERB, "was": POSTag.VERB, "were": POSTag.VERB,
            "be": POSTag.VERB, "been": POSTag.VERB, "have": POSTag.VERB, "has": POSTag.VERB,
            "had": POSTag.VERB, "do": POSTag.VERB, "does": POSTag.VERB, "did": POSTag.VERB,
            "will": POSTag.VERB, "would": POSTag.VERB, "can": POSTag.VERB, "could": POSTag.VERB,
            "may": POSTag.VERB, "might": POSTag.VERB, "shall": POSTag.VERB, "should": POSTag.VERB,
            "must": POSTag.VERB, "oh": POSTag.INTERJECTION, "wow": POSTag.INTERJECTION,
        }

    def tag(self, word: str) -> POSTag:
        lower = word.lower()
        if lower in self._function_words:
            return self._function_words[lower]
        if lower in self._lexicon:
            return self._lexicon[lower]
        for suffix, tag in self._suffix_rules:
            if lower.endswith(suffix):
                return tag
        if lower.isdigit():
            return POSTag.NUMERAL
        return POSTag.NOUN

    def tag_sentence(self, words: List[str]) -> List[tuple]:
        return [(w, self.tag(w)) for w in words]

    def tag_sequence(self, words: List[str]) -> List[tuple]:
        tags = [self.tag(w) for w in words]
        for i in range(len(words)):
            if tags[i] == POSTag.NOUN and i > 0 and tags[i-1] in (POSTag.DETERMINER, POSTag.ADJECTIVE):
                continue
            if tags[i] == POSTag.UNKNOWN and words[i].lower().endswith("ing"):
                tags[i] = POSTag.VERB
        return [(words[i], tags[i]) for i in range(len(words))]

    def get_stats(self, tags: List[tuple]) -> Dict[str, Any]:
        counts = {}
        for _, tag in tags:
            counts[tag.name] = counts.get(tag.name, 0) + 1
        return {"total": len(tags), "by_tag": counts}

def run() -> None:
    print("POS Tagger test")
    e = POSTagger()
    words = ["The", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog", "happily", "on", "Monday"]
    tags = e.tag_sequence(words)
    for w, t in tags:
        print("  " + w + " -> " + t.name)
    print("  Stats: " + str(e.get_stats(tags)))
    print("POS Tagger test complete.")

if __name__ == "__main__":
    run()
