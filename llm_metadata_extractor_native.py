"""Metadata Extractor — Dublin Core, MARC, RIS, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class MetadataExtractor:
    raw: Dict[str, str] = field(default_factory=dict)

    def dublin_core(self) -> Dict[str, str]:
        return {
            "dc.title": self.raw.get("title", ""),
            "dc.creator": self.raw.get("author", ""),
            "dc.subject": self.raw.get("subject", ""),
            "dc.date": self.raw.get("date", ""),
            "dc.publisher": self.raw.get("publisher", ""),
            "dc.type": self.raw.get("type", ""),
            "dc.format": self.raw.get("format", ""),
            "dc.language": self.raw.get("language", ""),
        }

    def marc_245(self) -> str:
        title = self.raw.get("title", "")
        author = self.raw.get("author", "")
        return f"245 10 $a{title} / $c{author}."

    def ris(self) -> str:
        lines = [f"TY  - {self.raw.get('type', 'BOOK')}",
                 f"TI  - {self.raw.get('title', '')}",
                 f"AU  - {self.raw.get('author', '')}",
                 f"PY  - {self.raw.get('date', '')}",
                 f"ER  - "]
        return "\n".join(lines)

    def bibtex(self) -> str:
        key = f"{self.raw.get('author', 'Unknown').split()[-1].lower()}{self.raw.get('date', '')}"
        title = self.raw.get('title', '')
        author = self.raw.get('author', '')
        year = self.raw.get('date', '')
        return f"@book{{{key},\n  title={{{title}}},\n  author={{{author}}},\n  year={{{year}}}\n}}"

    def completeness(self) -> float:
        fields = ["title", "author", "date", "publisher", "subject"]
        filled = sum(1 for f in fields if self.raw.get(f))
        return filled / len(fields)

    def stats(self) -> Dict:
        return {"completeness": round(self.completeness(), 2), "formats": ["dublin_core", "marc", "ris", "bibtex"]}

def run():
    me = MetadataExtractor({"title": "Deep Learning", "author": "Ian Goodfellow", "date": "2016", "publisher": "MIT Press", "type": "BOOK"})
    print(me.stats())
    print(me.ris())

if __name__ == "__main__":
    run()
