"""Discourse Analyzer — coherence, anaphora, discourse markers, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import re

@dataclass
class DiscourseAnalyzer:
    sentences: List[str] = field(default_factory=list)
    pronouns: Set[str] = field(default_factory=lambda: {"he", "she", "it", "they", "him", "her", "them", "this", "that"})
    markers: Set[str] = field(default_factory=lambda: {"however", "therefore", "because", "since", "although", "but", "so", "then"})

    def add_sentence(self, text: str):
        self.sentences.append(text)

    def anaphora_resolution(self) -> Dict[str, str]:
        antecedents = {}
        last_noun = ""
        for sent in self.sentences:
            words = re.findall(r'\w+', sent.lower())
            for i, word in enumerate(words):
                if word in self.pronouns and last_noun:
                    antecedents[word] = last_noun
            nouns = [w for w in words if w not in self.pronouns and len(w) > 2]
            if nouns:
                last_noun = nouns[-1]
        return antecedents

    def discourse_markers(self) -> List[Tuple[int, str]]:
        found = []
        for i, sent in enumerate(self.sentences):
            words = set(re.findall(r'\w+', sent.lower()))
            for marker in self.markers:
                if marker in words:
                    found.append((i, marker))
        return found

    def coherence_score(self) -> float:
        if len(self.sentences) < 2:
            return 1.0
        overlap = 0
        for i in range(len(self.sentences) - 1):
            w1 = set(re.findall(r'\w+', self.sentences[i].lower()))
            w2 = set(re.findall(r'\w+', self.sentences[i+1].lower()))
            if w1 and w2:
                overlap += len(w1 & w2) / len(w1 | w2)
        return overlap / (len(self.sentences) - 1)

    def stats(self) -> Dict:
        return {"sentences": len(self.sentences), "coherence": round(self.coherence_score(), 3)}

def run():
    da = DiscourseAnalyzer()
    da.add_sentence("Alice went to the store.")
    da.add_sentence("She bought some milk.")
    da.add_sentence("However, it was expired.")
    print("Anaphora:", da.anaphora_resolution())
    print("Markers:", da.discourse_markers())
    print(da.stats())

if __name__ == "__main__":
    run()
