"""Legal Search — statutes, cases, citation matching, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import re

@dataclass
class LegalDocument:
    id: str
    title: str
    text: str
    citations: List[str] = field(default_factory=list)

class LegalSearch:
    def __init__(self):
        self.documents: List[LegalDocument] = []

    def add_document(self, d: LegalDocument):
        self.documents.append(d)

    def search(self, query: str) -> List[LegalDocument]:
        q = query.lower()
        return [d for d in self.documents if q in d.title.lower() or q in d.text.lower()]

    def by_citation(self, citation: str) -> List[LegalDocument]:
        return [d for d in self.documents if citation in d.citations]

    def extract_citations(self, text: str) -> List[str]:
        return re.findall(r'\d+\s+U\.S\.\s+\d+', text)

    def related_cases(self, doc_id: str) -> List[str]:
        doc = next((d for d in self.documents if d.id == doc_id), None)
        if not doc:
            return []
        related = []
        for d in self.documents:
            if d.id != doc_id and any(c in d.citations for c in doc.citations):
                related.append(d.id)
        return related

    def stats(self) -> Dict:
        return {"documents": len(self.documents), "total_citations": sum(len(d.citations) for d in self.documents)}

def run():
    ls = LegalSearch()
    ls.add_document(LegalDocument("R1", "Roe v Wade", "Right to privacy...", ["410 U.S. 113"]))
    ls.add_document(LegalDocument("P1", "Planned Parenthood", "Abortion rights...", ["410 U.S. 113"]))
    print(ls.stats())
    print("Search 'privacy':", [d.title for d in ls.search("privacy")])
    print("Related to R1:", ls.related_cases("R1"))

if __name__ == "__main__":
    run()
