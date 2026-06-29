
"""
internet_search_engine_native.py
MAGNATRIX-OS — Internet Search Engine

Unified search across the internet combining DuckDuckGo, Reddit,
GitHub, and web scraping. Inspired by Agent-Reach.
Pure Python standard library.
"""

import urllib.request
import urllib.parse
import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    rank: int
    timestamp: str


class InternetSearchEngine:
    """Unified internet search engine with no API keys."""

    def __init__(self, user_agent: str = "Mozilla/5.0 (compatible; Agent-Reach/1.0)"):
        self.user_agent = user_agent
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "identity",
        }
        self._cache: Dict[str, List[SearchResult]] = {}

    def _fetch(self, url: str) -> Optional[str]:
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    def search_duckduckgo(self, query: str, count: int = 10) -> List[SearchResult]:
        """Search via DuckDuckGo HTML interface."""
        cache_key = f"ddg:{query}"
        if cache_key in self._cache:
            return self._cache[cache_key][:count]
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        html = self._fetch(url)
        if not html:
            return []
        results = []
        # Parse DuckDuckGo results
        for i, m in enumerate(re.finditer(r'<a rel="nofollow" class="result__a" href="([^"]+)">(.*?)</a>.*?<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL), 1):
            href = m.group(1)
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            snippet = re.sub(r"<[^>]+>", "", m.group(3)).strip()
            results.append(SearchResult(
                title=title, url=href, snippet=snippet, source="duckduckgo",
                rank=i, timestamp=datetime.now().isoformat(),
            ))
            if len(results) >= count:
                break
        self._cache[cache_key] = results
        return results

    def search_reddit(self, query: str, count: int = 5) -> List[SearchResult]:
        """Search Reddit posts."""
        cache_key = f"reddit:{query}"
        if cache_key in self._cache:
            return self._cache[cache_key][:count]
        url = f"https://www.reddit.com/search.json?q={urllib.parse.quote(query)}&limit={count}"
        self.headers["Accept"] = "application/json"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                results = []
                for i, child in enumerate(data.get("data", {}).get("children", [])[:count], 1):
                    post = child.get("data", {})
                    results.append(SearchResult(
                        title=post.get("title", ""), url=f"https://reddit.com{post.get('permalink', '')}",
                        snippet=post.get("selftext", "")[:200], source="reddit",
                        rank=i, timestamp=datetime.now().isoformat(),
                    ))
                self.headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                self._cache[cache_key] = results
                return results
        except Exception:
            self.headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            return []

    def search_github(self, query: str, count: int = 5) -> List[SearchResult]:
        """Search GitHub repositories."""
        cache_key = f"github:{query}"
        if cache_key in self._cache:
            return self._cache[cache_key][:count]
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&per_page={count}"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                results = []
                for i, item in enumerate(data.get("items", [])[:count], 1):
                    results.append(SearchResult(
                        title=item.get("full_name", ""), url=item.get("html_url", ""),
                        snippet=item.get("description", "") or "", source="github",
                        rank=i, timestamp=datetime.now().isoformat(),
                    ))
                self._cache[cache_key] = results
                return results
        except Exception:
            return []

    def unified_search(self, query: str, count: int = 10) -> Dict[str, List[SearchResult]]:
        """Search across all sources and return unified results."""
        return {
            "web": self.search_duckduckgo(query, count),
            "reddit": self.search_reddit(query, count // 2),
            "github": self.search_github(query, count // 2),
        }

    def get_result_summary(self, results: Dict[str, List[SearchResult]]) -> str:
        """Generate a text summary of search results."""
        lines = [f"Search Results Summary", "=" * 40, ""]
        for source, items in results.items():
            lines.append(f"--- {source.upper()} ({len(items)} results) ---")
            for item in items[:3]:
                lines.append(f"  {item.rank}. {item.title}")
                lines.append(f"     {item.url}")
                lines.append(f"     {item.snippet[:100]}...")
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {"cache_size": len(self._cache), "sources": ["duckduckgo", "reddit", "github"]}


__all__ = ["InternetSearchEngine", "SearchResult"]
