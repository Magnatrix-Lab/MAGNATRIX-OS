
"""
web_content_reader_native.py
MAGNATRIX-OS — Web Content Reader

Read and extract content from any web page without API keys.
Inspired by Agent-Reach. Pure Python standard library.
"""

import urllib.request
import urllib.parse
import urllib.error
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WebContent:
    url: str
    title: str
    text: str
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    headings: List[str] = field(default_factory=list)
    meta_description: str = ""
    timestamp: str = ""


class WebContentReader:
    """Read and extract content from web pages."""

    def __init__(self, user_agent: str = "Mozilla/5.0 (compatible; Agent-Reach/1.0)"):
        self.user_agent = user_agent
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "identity",
        }
        self._cache: Dict[str, WebContent] = {}

    def fetch(self, url: str, timeout: int = 15) -> Optional[str]:
        """Fetch raw HTML from URL."""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    def read(self, url: str) -> WebContent:
        """Read and extract structured content from a web page."""
        if url in self._cache:
            return self._cache[url]
        html = self.fetch(url)
        if not html:
            return WebContent(url=url, title="", text="", timestamp=datetime.now().isoformat())
        content = self._parse(html, url)
        self._cache[url] = content
        return content

    def _parse(self, html: str, url: str) -> WebContent:
        title = self._extract_title(html)
        text = self._extract_text(html)
        links = self._extract_links(html, url)
        images = self._extract_images(html, url)
        headings = self._extract_headings(html)
        meta = self._extract_meta(html)
        return WebContent(
            url=url, title=title, text=text, links=links[:50],
            images=images[:20], headings=headings[:20],
            meta_description=meta, timestamp=datetime.now().isoformat(),
        )

    def _extract_title(self, html: str) -> str:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        return m.group(1).strip() if m else ""

    def _extract_text(self, html: str) -> str:
        # Remove script/style tags first
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<nav[^>]*>.*?</nav>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<footer[^>]*>.*?</footer>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Remove remaining tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:20000]  # Limit to 20k chars

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        links = []
        for m in re.finditer(r'href\s*=\s*["\']([^"\']+)["\']', html):
            href = m.group(1)
            if href.startswith("http"):
                links.append(href)
            elif href.startswith("/"):
                # Resolve relative URL
                parsed = urllib.parse.urlparse(base_url)
                links.append(f"{parsed.scheme}://{parsed.netloc}{href}")
        return list(set(links))

    def _extract_images(self, html: str, base_url: str) -> List[str]:
        images = []
        for m in re.finditer(r'src\s*=\s*["\']([^"\']+)["\']', html):
            src = m.group(1)
            if src.startswith("http"):
                images.append(src)
            elif src.startswith("/"):
                parsed = urllib.parse.urlparse(base_url)
                images.append(f"{parsed.scheme}://{parsed.netloc}{src}")
        return list(set(images))

    def _extract_headings(self, html: str) -> List[str]:
        headings = []
        for m in re.finditer(r"<h[1-6][^>]*>(.*?)</h[1-6]>", html, re.IGNORECASE | re.DOTALL):
            text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if text:
                headings.append(text)
        return headings

    def _extract_meta(self, html: str) -> str:
        m = re.search(r'<meta[^>]*name\s*=\s*["\']description["\'][^>]*content\s*=\s*["\']([^"\']+)', html, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'<meta[^>]*content\s*=\s*["\']([^"\']+)["\'][^>]*name\s*=\s*["\']description["\']', html, re.IGNORECASE)
        return m.group(1) if m else ""

    def search_duckduckgo(self, query: str, count: int = 5) -> List[Dict[str, str]]:
        """Search via DuckDuckGo HTML (no API key)."""
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        html = self.fetch(url)
        if not html:
            return []
        results = []
        # DuckDuckGo HTML results
        for m in re.finditer(r'<a rel="nofollow" class="result__a" href="([^"]+)">(.*?)</a>', html, re.DOTALL):
            href = m.group(1)
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if href and title:
                results.append({"title": title, "url": href})
            if len(results) >= count:
                break
        return results

    def summarize(self, url: str, max_chars: int = 500) -> str:
        """Get a quick summary of a web page."""
        content = self.read(url)
        lines = [f"Title: {content.title}", f"URL: {content.url}", ""]
        if content.meta_description:
            lines.append(f"Description: {content.meta_description}")
        if content.headings:
            lines.append(f"Key Topics: {', '.join(content.headings[:5])}")
        lines.append(f"Content Preview: {content.text[:max_chars]}...")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {"cache_size": len(self._cache), "user_agent": self.user_agent}


__all__ = ["WebContentReader", "WebContent"]
