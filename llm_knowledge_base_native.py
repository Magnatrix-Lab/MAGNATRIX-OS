"""Knowledge Base — FAQ, topics, search, relevance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import re

@dataclass
class KnowledgeBase:
    entries: List[Dict] = field(default_factory=list)
    """Each: {question, answer, tags, category}"""

    def add_entry(self, question: str, answer: str, tags: List[str], category: str):
        self.entries.append({"question": question, "answer": answer, "tags": tags, "category": category})

    def search(self, query: str) -> List[Dict]:
        q = query.lower()
        results = []
        for e in self.entries:
            score = 0
            if q in e["question"].lower():
                score += 3
            if q in e["answer"].lower():
                score += 1
            if any(q in t.lower() for t in e["tags"]):
                score += 2
            if score > 0:
                results.append((e, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results]

    def by_category(self, category: str) -> List[Dict]:
        return [e for e in self.entries if e["category"] == category]

    def relevance(self, query: str, entry: Dict) -> float:
        q_words = set(re.findall(r'\w+', query.lower()))
        text = (entry["question"] + " " + entry["answer"] + " " + " ".join(entry["tags"])).lower()
        e_words = set(re.findall(r'\w+', text))
        inter = q_words & e_words
        union = q_words | e_words
        return len(inter) / len(union) if union else 0.0

    def stats(self) -> Dict:
        cats = {}
        for e in self.entries:
            cats[e["category"]] = cats.get(e["category"], 0) + 1
        return {"entries": len(self.entries), "categories": cats}

def run():
    kb = KnowledgeBase()
    kb.add_entry("How to reset password?", "Click forgot password.", ["password", "account"], "account")
    kb.add_entry("How to contact support?", "Email support@example.com", ["support", "contact"], "help")
    print(kb.stats())
    print("Search:", [e["question"] for e in kb.search("password")])

if __name__ == "__main__":
    run()
