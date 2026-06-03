"""LLM Document Parser — Native Python (stdlib only)."""
from __future__ import annotations
import re, json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class DocumentType(Enum):
    TEXT = auto()
    MARKDOWN = auto()
    JSON = auto()
    XML = auto()
    CSV = auto()
    YAML = auto()

@dataclass
class DocumentSection:
    id: str
    title: str
    content: str
    level: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

class DocumentParser:
    def __init__(self) -> None:
        self._sections: List[DocumentSection] = []

    def parse_markdown(self, text: str) -> List[DocumentSection]:
        sections = []
        lines = text.splitlines()
        current_content = []
        current_title = ""
        current_level = 1
        for line in lines:
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                if current_title or current_content:
                    sections.append(DocumentSection("sec_" + str(len(sections)), current_title or "Untitled", "\n".join(current_content), current_level))
                current_level = len(match.group(1))
                current_title = match.group(2)
                current_content = []
            else:
                current_content.append(line)
        if current_title or current_content:
            sections.append(DocumentSection("sec_" + str(len(sections)), current_title or "Untitled", "\n".join(current_content), current_level))
        self._sections = sections
        return sections

    def parse_json(self, text: str) -> Dict[str, Any]:
        return json.loads(text)

    def parse_headers(self, text: str) -> List[tuple]:
        headers = []
        for match in re.finditer(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE):
            headers.append((len(match.group(1)), match.group(2)))
        return headers

    def extract_links(self, text: str) -> List[str]:
        return re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', text)

    def extract_code_blocks(self, text: str) -> List[tuple]:
        return re.findall(r'```(\w+)?\n(.*?)```', text, re.DOTALL)

    def get_stats(self) -> Dict[str, Any]:
        return {"sections": len(self._sections), "total_content": sum(len(s.content) for s in self._sections)}

def run() -> None:
    print("Document Parser test")
    e = DocumentParser()
    text = "# Introduction\n\nThis is intro.\n\n## Details\n\nMore details here.\n```python\nprint('hello')\n```\n\n[Link](https://example.com)"
    sections = e.parse_markdown(text)
    for s in sections:
        print("  " + s.title + " (level " + str(s.level) + "): " + str(len(s.content)) + " chars")
    print("  Links: " + str(e.extract_links(text)))
    print("  Code blocks: " + str(len(e.extract_code_blocks(text))))
    print("  Stats: " + str(e.get_stats()))
    print("Document Parser test complete.")

if __name__ == "__main__":
    run()
