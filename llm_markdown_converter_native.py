"""Markdown Converter — to/from HTML, table of contents, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import re

class MarkdownConverter:
    def __init__(self):
        self.toc: List[Dict] = []

    def to_html(self, md: str) -> str:
        html = md
        html = re.sub(r'^# (.*)$', r'<h1></h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*)$', r'<h2></h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.*)$', r'<h3></h3>', html, flags=re.MULTILINE)
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong></strong>', html)
        html = re.sub(r'\*(.*?)\*', r'<em></em>', html)
        html = re.sub(r'`(.*?)`', r'<code></code>', html)
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href=""></a>', html)
        html = re.sub(r'^\* (.*)$', r'<li></li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>)', r'<ul></ul>', html, flags=re.DOTALL)
        html = html.replace('\n', '<br>\n')
        return html

    def extract_toc(self, md: str) -> List[Dict]:
        toc = []
        for line in md.split('\n'):
            m = re.match(r'^(#{1,6})\s+(.*)$', line)
            if m:
                level = len(m.group(1))
                title = m.group(2)
                anchor = re.sub(r'[^\w]', '-', title.lower())
                toc.append({"level": level, "title": title, "anchor": anchor})
        return toc

    def to_plain_text(self, md: str) -> str:
        text = re.sub(r'\*\*|\*|#|`|\[|\]|\([^)]*\)', '', md)
        return text.strip()

    def stats(self) -> Dict:
        return {"toc_entries": len(self.toc)}

def run():
    conv = MarkdownConverter()
    md = "# Hello\n\nThis is **bold** and *italic*.\n\n## Section\n\n* Item 1\n* Item 2\n\n[Link](http://example.com)"
    print(conv.to_html(md)[:200])
    print(conv.extract_toc(md))
    print(conv.to_plain_text(md))
    print(conv.stats())

if __name__ == "__main__":
    run()
