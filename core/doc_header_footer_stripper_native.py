"""Doc Header Footer Stripper - Remove headers and footers from document pages."""
from __future__ import annotations
import json, re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

@dataclass
class PageContent:
    page_id: str
    page_number: int
    header: str = ""
    body: str = ""
    footer: str = ""
    stripped: bool = False

    def to_dict(self) -> Dict:
        return {"page_id": self.page_id, "page_number": self.page_number, "header": self.header,
                "body": self.body, "footer": self.footer, "stripped": self.stripped}

class DocHeaderFooterStripper:
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "doc_stripper"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pages: Dict[str, PageContent] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for p in data.get("pages",[]): self.pages[p["page_id"]] = PageContent(**p)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"pages": [p.to_dict() for p in self.pages.values()]}, indent=2))

    def strip(self, text: str, page_id: str, page_number: int) -> PageContent:
        NL = chr(10)
        lines = text.split(NL)
        if len(lines) < 3:
            pc = PageContent(page_id=page_id, page_number=page_number, body=text, stripped=False)
            self.pages[page_id] = pc
            return pc
        header = lines[0].strip()
        footer = lines[-1].strip()
        body = NL.join(lines[1:-1]).strip()
        body = self._clean_patterns(body)
        pc = PageContent(page_id=page_id, page_number=page_number, header=header, body=body, footer=footer, stripped=True)
        self.pages[page_id] = pc
        self._save_state()
        return pc

    def _clean_patterns(self, text: str) -> str:
        patterns = [
            r'^\s*Page\s+\d+\s*/\s*\d+\s*$',
            r'^\s*\d+\s*$',
            r'^\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$',
            r'^\s*https?://\S+\s*$',
            r'^\s*Copyright\s+\u00a9.*$',
            r'^\s*All rights reserved\s*$',
        ]
        NL = chr(10)
        lines = text.split(NL)
        cleaned = []
        for line in lines:
            if any(re.match(p, line, re.IGNORECASE) for p in patterns):
                continue
            cleaned.append(line)
        return NL.join(cleaned)

    def batch_strip(self, pages: List[Dict]) -> List[PageContent]:
        return [self.strip(p["text"], p["page_id"], p["page_number"]) for p in pages]

    def get_stats(self) -> Dict:
        return {"pages_total": len(self.pages), "stripped": sum(1 for p in self.pages.values() if p.stripped)}

    def to_dict(self) -> Dict:
        return {"pages": [p.to_dict() for p in self.pages.values()], "stats": self.get_stats()}

__all__ = ["DocHeaderFooterStripper", "PageContent"]
