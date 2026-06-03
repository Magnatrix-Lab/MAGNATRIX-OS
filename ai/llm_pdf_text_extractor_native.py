"""LLM PDF Text Extractor — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class PDFTextExtractor:
    def __init__(self) -> None:
        self._pages: List[str] = []
        self._meta: Dict[str, str] = {}

    def extract_text(self, raw_pdf_content: str) -> str:
        text_parts = []
        for obj in re.findall(r'stream\r?\n(.*?)\r?\nendstream', raw_pdf_content, re.DOTALL):
            text = re.sub(r'[^\x20-\x7E\x0A\x0D]', '', obj)
            text_parts.append(text)
        full = "\n".join(text_parts)
        self._pages = full.split("\f")
        return full

    def extract_meta(self, raw_pdf_content: str) -> Dict[str, str]:
        meta = {}
        for match in re.findall(r'/Title\s*\(([^)]*)\)', raw_pdf_content):
            meta["title"] = match
        for match in re.findall(r'/Author\s*\(([^)]*)\)', raw_pdf_content):
            meta["author"] = match
        for match in re.findall(r'/CreationDate\s*\(([^)]*)\)', raw_pdf_content):
            meta["created"] = match
        self._meta = meta
        return meta

    def get_page(self, page_num: int) -> Optional[str]:
        if 0 <= page_num < len(self._pages):
            return self._pages[page_num]
        return None

    def get_page_count(self) -> int:
        return len(self._pages)

    def search_text(self, text: str, keyword: str) -> List[int]:
        lines = text.splitlines()
        return [i for i, line in enumerate(lines) if keyword.lower() in line.lower()]

    def get_stats(self, text: str) -> Dict[str, Any]:
        return {"pages": len(self._pages), "chars": len(text), "lines": len(text.splitlines())}

def run() -> None:
    print("PDF Text Extractor test")
    e = PDFTextExtractor()
    raw = "stream\nHello World\nendstream\nstream\nPage 2 content\nendstream\n/Title (Sample PDF) /Author (John Doe)"
    text = e.extract_text(raw)
    meta = e.extract_meta(raw)
    print("  Text: " + text[:50])
    print("  Meta: " + str(meta))
    print("  Pages: " + str(e.get_page_count()))
    print("  Stats: " + str(e.get_stats(text)))
    print("PDF Text Extractor test complete.")

if __name__ == "__main__":
    run()
