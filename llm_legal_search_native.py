"""Legal Search — precedent matching, statute lookup, relevance scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import re
from collections import Counter

class LegalSearch:
    def __init__(self):
        self.documents: List[Dict] = []
        self.index: Dict[str, List[int]] = {}

    def add_document(self, doc_id: str, text: str, category: str = "precedent"):
        self.documents.append({"id": doc_id, "text": text, "category": category})
        doc_idx = len(self.documents) - 1
        words = re.findall(r'\w+', text.lower())
        for w in words:
            if w not in self.index:
                self.index[w] = []
            self.index[w].append(doc_idx)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        q_words = re.findall(r'\w+', query.lower())
        scores = Counter()
        for w in q_words:
            for idx in self.index.get(w, []):
                scores[idx] += 1
        results = []
        for idx, score in scores.most_common(top_k):
            doc = self.documents[idx]
            results.append({"id": doc["id"], "score": score, "category": doc["category"], "snippet": doc["text"][:100]})
        return results

    def search_by_category(self, query: str, category: str) -> List[Dict]:
        return [r for r in self.search(query, 20) if r["category"] == category]

    def stats(self) -> Dict:
        return {"documents": len(self.documents), "index_terms": len(self.index)}

def run():
    ls = LegalSearch()
    ls.add_document("P1", "In case Smith v. Jones, the court held that breach of contract requires damages.", "precedent")
    ls.add_document("S1", "Contract law requires offer, acceptance, and consideration.", "statute")
    ls.add_document("P2", "Jones v. Smith established that negligence requires duty and breach.", "precedent")
    print(ls.search("breach contract damages"))
    print(ls.stats())

if __name__ == "__main__":
    run()
