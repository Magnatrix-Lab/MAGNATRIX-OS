"""LLM Web Scraper — Native Python (stdlib only)."""
from __future__ import annotations
import urllib.request, urllib.parse, ssl, re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class WebScraper:
    def __init__(self) -> None:
        self._context = ssl._create_unverified_context()
        self._headers = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"}
        self._history: List[str] = []

    def fetch(self, url: str) -> str:
        req = urllib.request.Request(url, headers=self._headers)
        with urllib.request.urlopen(req, timeout=30, context=self._context) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
            self._history.append(url)
            return data

    def extract_text(self, html: str) -> str:
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_links(self, html: str, base_url: str = "") -> List[str]:
        found = re.findall(r'href=["\']([^"\']+)["\']', html)
        if base_url:
            resolved = []
            for link in found:
                if link.startswith("http"):
                    resolved.append(link)
                elif link.startswith("/"):
                    parsed = urllib.parse.urlparse(base_url)
                    resolved.append(parsed.scheme + "://" + parsed.netloc + link)
                else:
                    resolved.append(base_url.rstrip("/") + "/" + link)
            return resolved
        return found

    def extract_title(self, html: str) -> str:
        match = re.search(r'<title[^>]*>([^<]*)</title>', html, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def extract_meta(self, html: str) -> Dict[str, str]:
        meta = {}
        for match in re.finditer(r'<meta[^>]*name=["\']([^"\']*)["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE):
            meta[match.group(1)] = match.group(2)
        return meta

    def get_stats(self) -> Dict[str, Any]:
        return {"fetches": len(self._history)}

def run() -> None:
    print("Web Scraper test")
    e = WebScraper()
    html = "<html><head><title>Test Page</title><meta name='author' content='John'></head><body><a href='/page1'>Link 1</a><a href='http://other.com'>External</a></body></html>"
    print("  Title: " + e.extract_title(html))
    print("  Text: " + e.extract_text(html))
    print("  Links: " + str(e.extract_links(html, "http://example.com")))
    print("  Meta: " + str(e.extract_meta(html)))
    print("  Stats: " + str(e.get_stats()))
    print("Web Scraper test complete.")

if __name__ == "__main__":
    run()
