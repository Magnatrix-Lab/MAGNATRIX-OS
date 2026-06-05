"""Bibliography Manager — citation formats, references, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

@dataclass
class Reference:
    ref_id: str
    authors: List[str]
    title: str
    year: int
    journal: str = ""
    url: str = ""
    doi: str = ""

class BibliographyManager:
    def __init__(self):
        self.references: List[Reference] = []
        self.citation_style = "APA"

    def add(self, ref: Reference):
        self.references.append(ref)

    def format_apa(self, ref: Reference) -> str:
        authors = ", ".join(ref.authors)
        if ref.journal:
            return f"{authors} ({ref.year}). {ref.title}. {ref.journal}."
        return f"{authors} ({ref.year}). {ref.title}."

    def format_mla(self, ref: Reference) -> str:
        authors = " and ".join(ref.authors)
        return f'{authors}. "{ref.title}." {ref.journal}, {ref.year}.'

    def format_bibtex(self, ref: Reference) -> str:
        key = f"{ref.authors[0].split()[-1].lower()}{ref.year}"
        author_str = " and ".join(ref.authors)
        lines = [f"@article{{{key},"]
        lines.append(f"  author = {{{author_str}}},")
        lines.append(f"  title = {{{ref.title}}},")
        lines.append(f"  year = {{{ref.year}}},")
        if ref.journal:
            lines.append(f"  journal = {{{ref.journal}}},")
        lines.append("}")
        return '\n'.join(lines)

    def generate_bibliography(self, style: str = "APA") -> List[str]:
        if style == "APA":
            return [self.format_apa(r) for r in self.references]
        elif style == "MLA":
            return [self.format_mla(r) for r in self.references]
        elif style == "BibTeX":
            return [self.format_bibtex(r) for r in self.references]
        return []

    def stats(self) -> Dict:
        return {"references": len(self.references), "styles": ["APA", "MLA", "BibTeX"]}

def run():
    bib = BibliographyManager()
    bib.add(Reference("1", ["Alice Smith", "Bob Jones"], "Deep Learning", 2023, "Nature AI", "https://example.com", "10.123/abc"))
    for c in bib.generate_bibliography("APA"):
        print(c)
    print(bib.stats())

if __name__ == "__main__":
    run()
