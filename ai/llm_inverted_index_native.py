"""Inverted Index - Document indexing for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from collections import defaultdict
import re

@dataclass
class InvertedIndex:
    index: Dict[str, Set[int]] = field(default_factory=lambda: defaultdict(set))
    documents: Dict[int, str] = field(default_factory=dict)
    doc_id_counter: int = 0

    def add_document(self, text: str) -> int:
        self.doc_id_counter += 1
        doc_id = self.doc_id_counter
        self.documents[doc_id] = text
        tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        for token in tokens:
            self.index[token].add(doc_id)
        return doc_id

    def search(self, query: str) -> Set[int]:
        tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
        if not tokens: return set()
        result = set(self.index.get(tokens[0], set()))
        for token in tokens[1:]:
            result &= self.index.get(token, set())
        return result

    def stats(self) -> dict:
        return {"terms": len(self.index), "documents": len(self.documents), "avg_postings": round(sum(len(v) for v in self.index.values())/len(self.index), 2) if self.index else 0}

def run():
    ii = InvertedIndex()
    ii.add_document("The quick brown fox")
    ii.add_document("The lazy dog sleeps")
    ii.add_document("The quick dog jumps")
    print("Search 'the dog':", ii.search("the dog"))
    print("Stats:", ii.stats())

if __name__ == "__main__": run()
