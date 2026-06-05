"""Named Entity Recognizer — person, org, location, date, rule-based, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import re

@dataclass
class NamedEntityRecognizer:
    person_prefixes: Set[str] = field(default_factory=lambda: {"Mr", "Mrs", "Ms", "Dr", "Prof"})
    location_suffixes: Set[str] = field(default_factory=lambda: {"City", "Town", "River", "Mountain", "Lake"})
    org_suffixes: Set[str] = field(default_factory=lambda: {"Inc", "Corp", "Ltd", "LLC", "Company", "Bank"})

    def recognize(self, text: str) -> List[Tuple[str, str, int, int]]:
        entities = []
        tokens = re.findall(r'\w+', text)
        pos = 0
        for i, token in enumerate(tokens):
            tpos = text.find(token, pos)
            end = tpos + len(token)
            if token in self.person_prefixes and i + 1 < len(tokens):
                next_t = tokens[i+1]
                entities.append(("PERSON", f"{token} {next_t}", tpos, end + len(next_t) + 1))
            elif token in self.org_suffixes or (i > 0 and tokens[i-1] in {"The", "A"}):
                entities.append(("ORG", token, tpos, end))
            elif token in self.location_suffixes or token[0].isupper() and token in {"London", "Paris", "Tokyo", "New York"}:
                entities.append(("LOC", token, tpos, end))
            elif re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', token):
                entities.append(("DATE", token, tpos, end))
            pos = end
        return entities

    def extract_patterns(self, text: str) -> List[Tuple[str, str]]:
        entities = []
        for m in re.finditer(r'[A-Z][a-z]+\s[A-Z][a-z]+', text):
            entities.append(("PERSON", m.group()))
        for m in re.finditer(r'\d{1,2}/\d{1,2}/\d{2,4}', text):
            entities.append(("DATE", m.group()))
        for m in re.finditer(r'\$\d+(\.\d+)?', text):
            entities.append(("MONEY", m.group()))
        return entities

    def stats(self, text: str) -> Dict:
        ents = self.recognize(text)
        return {"entities": len(ents), "types": len(set(e[0] for e in ents))}

def run():
    ner = NamedEntityRecognizer()
    text = "Dr Smith visited Paris on 5/12/2024 for $500."
    print("Entities:", ner.recognize(text))
    print("Patterns:", ner.extract_patterns(text))
    print(ner.stats(text))

if __name__ == "__main__":
    run()
