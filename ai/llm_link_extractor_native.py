"""LLM Link Extractor — Native Python (stdlib only)."""
from __future__ import annotations
import re, urllib.parse
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

@dataclass
class Link:
    url: str
    text: str
    rel: str = ""
    title: str = ""
    is_external: bool = False

class LinkExtractor:
    def __init__(self) -> None:
        self._links: List[Link] = []

    def extract(self, html: str, base_url: str = "") -> List[Link]:
        links = []
        for match in re.finditer(r'<a\s+([^>]*)>([^<]*)</a>', html, re.IGNORECASE):
            attrs = match.group(1)
            text = match.group(2).strip()
            href = re.search(r'href=["\']([^"\']*)["\']', attrs)
            rel = re.search(r'rel=["\']([^"\']*)["\']', attrs)
            title = re.search(r'title=["\']([^"\']*)["\']', attrs)
            url = href.group(1) if href else ""
            if base_url and url:
                url = urllib.parse.urljoin(base_url, url)
            is_external = bool(url and not url.startswith(base_url) if base_url else False)
            links.append(Link(url, text, rel.group(1) if rel else "", title.group(1) if title else "", is_external))
        self._links = links
        return links

    def extract_images(self, html: str, base_url: str = "") -> List[Dict[str, str]]:
        images = []
        for match in re.finditer(r'<img\s+([^>]*)>', html, re.IGNORECASE):
            attrs = match.group(1)
            src = re.search(r'src=["\']([^"\']*)["\']', attrs)
            alt = re.search(r'alt=["\']([^"\']*)["\']', attrs)
            if src:
                url = urllib.parse.urljoin(base_url, src.group(1)) if base_url else src.group(1)
                images.append({"url": url, "alt": alt.group(1) if alt else ""})
        return images

    def get_external(self, links: List[Link]) -> List[Link]:
        return [l for l in links if l.is_external]

    def get_internal(self, links: List[Link]) -> List[Link]:
        return [l for l in links if not l.is_external]

    def get_stats(self, links: List[Link]) -> Dict[str, Any]:
        return {"total": len(links), "external": len(self.get_external(links)), "internal": len(self.get_internal(links))}

def run() -> None:
    print("Link Extractor test")
    e = LinkExtractor()
    html = "<a href='/page1' rel='next'>Page 1</a><a href='http://other.com' title='External'>Other</a><a href='/page2'>Page 2</a>"
    links = e.extract(html, "http://example.com")
    for l in links:
        print("  " + l.url + " (" + ("ext" if l.is_external else "int") + ")")
    print("  External: " + str(len(e.get_external(links))))
    print("  Stats: " + str(e.get_stats(links)))
    print("Link Extractor test complete.")

if __name__ == "__main__":
    run()
