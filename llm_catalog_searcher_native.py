"""Catalog Searcher — Dewey, LCC, keyword, boolean, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
import re

@dataclass
class CatalogEntry:
    id: str
    title: str
    author: str
    subject: List[str] = field(default_factory=list)
    dewey: str = ""
    lcc: str = ""
    keywords: List[str] = field(default_factory=list)

class CatalogSearcher:
    def __init__(self):
        self.entries: List[CatalogEntry] = []

    def add_entry(self, e: CatalogEntry):
        self.entries.append(e)

    def search(self, query: str, field: str = "title") -> List[CatalogEntry]:
        q = query.lower()
        if field == "title":
            return [e for e in self.entries if q in e.title.lower()]
        elif field == "author":
            return [e for e in self.entries if q in e.author.lower()]
        elif field == "subject":
            return [e for e in self.entries if any(q in s.lower() for s in e.subject)]
        elif field == "dewey":
            return [e for e in self.entries if e.dewey.startswith(q)]
        elif field == "lcc":
            return [e for e in self.entries if e.lcc.startswith(q.upper())]
        return []

    def boolean_search(self, terms: List[str], operator: str = "AND") -> List[CatalogEntry]:
        results = []
        for e in self.entries:
            text = (e.title + " " + e.author + " " + " ".join(e.subject) + " " + " ".join(e.keywords)).lower()
            matches = [t.lower() in text for t in terms]
            if operator == "AND" and all(matches):
                results.append(e)
            elif operator == "OR" and any(matches):
                results.append(e)
            elif operator == "NOT" and not any(matches):
                results.append(e)
        return results

    def dewey_range(self, start: str, end: str) -> List[CatalogEntry]:
        return [e for e in self.entries if start <= e.dewey <= end]

    def stats(self) -> Dict:
        return {"entries": len(self.entries), "subjects": len(set(s for e in self.entries for s in e.subject))}

def run():
    cs = CatalogSearcher()
    cs.add_entry(CatalogEntry("1", "Python Programming", "John Smith", ["computers", "programming"], "005.13", "QA76.5", ["python", "coding"]))
    cs.add_entry(CatalogEntry("2", "Data Science", "Jane Doe", ["computers", "statistics"], "006.3", "QA76.7", ["data", "ml"]))
    print(cs.stats())
    print("Search python:", [e.title for e in cs.search("python", "title")])
    print("Boolean:", [e.title for e in cs.boolean_search(["python", "programming"], "AND")])

if __name__ == "__main__":
    run()
