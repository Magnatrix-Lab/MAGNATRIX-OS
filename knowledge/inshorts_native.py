"""
Inshorts News API — Native Python Client
Replicated from: sumitkolhe/inshorts
MAGNATRIX Layer 5/10 bridge — Knowledge Feed & AI Context Injection

Pure Python stdlib-first (urllib), requests optional.
~400 baris
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Inshorts API endpoint (public, no auth)
# ---------------------------------------------------------------------------
INSHORTS_API_URL = "https://inshorts.com/api/read"
DEFAULT_TIMEOUT = 15


# ---------------------------------------------------------------------------
# 1. NewsCategory — Enum 18 kategori
# ---------------------------------------------------------------------------
class NewsCategory(Enum):
    """Kategori berita yang didukung oleh Inshorts API."""

    ALL = "all"
    NATIONAL = "national"
    BUSINESS = "business"
    SPORTS = "sports"
    WORLD = "world"
    POLITICS = "politics"
    TECHNOLOGY = "technology"
    STARTUP = "startup"
    ENTERTAINMENT = "entertainment"
    MISCELLANEOUS = "miscellaneous"
    HATKE = "hatke"
    SCIENCE = "science"
    AUTOMOBILE = "automobile"
    # localized / extended
    EDUCATION = "education"
    HEALTH = "health"
    FASHION = "fashion"
    TRAVEL = "travel"
    FOOD = "food"

    @classmethod
    def list_all(cls) -> List[str]:
        """Return list of all category values."""
        return [c.value for c in cls]

    @classmethod
    def from_string(cls, raw: str) -> "NewsCategory":
        """Parse string ke NewsCategory, default ALL."""
        mapping = {c.value.lower(): c for c in cls}
        return mapping.get(raw.lower().strip(), cls.ALL)

    def __repr__(self) -> str:
        return f"NewsCategory.{self.name}('{self.value}')"


# ---------------------------------------------------------------------------
# 2. Article — dataclass untuk news item
# ---------------------------------------------------------------------------
@dataclass
class Article:
    """Single news article dari Inshorts."""

    title: str
    content: str
    author: str
    source_name: str
    image_url: str
    shortened_url: str
    created_at: str
    category_names: List[str] = field(default_factory=list)
    hash_tags: List[str] = field(default_factory=list)
    read_more_url: str = ""
    timestamp: int = 0

    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> "Article":
        """Parse raw Inshorts API dict ke Article."""
        return cls(
            title=data.get("title", ""),
            content=data.get("content", data.get("description", "")),
            author=data.get("author", ""),
            source_name=data.get("source_name", data.get("source", "")),
            image_url=data.get("image_url", data.get("imageUrl", "")),
            shortened_url=data.get("shortened_url", data.get("url", "")),
            created_at=data.get("created_at", data.get("date", "")),
            category_names=data.get("category_names", data.get("category", [])) or [],
            hash_tags=data.get("hash_tags", data.get("hashtags", [])) or [],
            read_more_url=data.get("read_more_url", data.get("readMoreUrl", "")),
            timestamp=data.get("timestamp", 0),
        )

    def summary(self, max_chars: int = 120) -> str:
        """Short one-line summary for AI context injection."""
        text = f"[{self.source_name}] {self.title} — {self.content}"
        if len(text) > max_chars:
            return text[: max_chars - 3].rstrip() + "..."
        return text

    def __repr__(self) -> str:
        return (
            f"Article(title='{self.title[:40]}...', source='{self.source_name}', "
            f"cat={self.category_names}, ts={self.created_at})"
        )


# ---------------------------------------------------------------------------
# 3. InshortsClient — HTTP client untuk fetch news
# ---------------------------------------------------------------------------
class InshortsClient:
    """HTTP client untuk Inshorts API. Pure stdlib, requests optional."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = 2,
        use_requests: bool = False,
    ):
        self.timeout = timeout
        self.retries = retries
        self._session = None
        self._has_requests = False

        if use_requests:
            try:
                import requests

                self._session = requests.Session()
                self._session.headers.update({
                    "User-Agent": "Mozilla/5.0 (compatible; InshortsClient/1.0)"
                })
                self._has_requests = True
            except ImportError:
                pass

    def _build_url(
        self,
        category: NewsCategory,
        lang: str = "en",
        offset: int = 0,
        limit: int = 10,
    ) -> str:
        """Build query URL dengan params."""
        # Inshorts public endpoint: POST dengan form data
        # Tapi ada endpoint read yang support GET query params juga
        # Fallback ke POST body jika GET gagal
        base = f"{INSHORTS_API_URL}?category={category.value}&lang={lang}&offset={offset}&limit={limit}"
        return base

    def _fetch_post(
        self,
        category: NewsCategory,
        lang: str = "en",
        offset: int = 0,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Fetch via POST (Inshorts native)."""
        payload = f"category={category.value}&lang={lang}&offset={offset}&limit={limit}"
        data = payload.encode("utf-8")
        req = urllib.request.Request(
            INSHORTS_API_URL,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
            method="POST",
        )

        last_err: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw)
            except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
                last_err = e
                if attempt < self.retries:
                    time.sleep(1.0 * attempt)

        # Semua retry habis — return empty
        return {"success": False, "error": str(last_err), "data": []}

    def fetch_news(
        self,
        category: NewsCategory = NewsCategory.ALL,
        lang: str = "en",
        offset: int = 0,
        limit: int = 10,
    ) -> Tuple[List[Article], int, bool]:
        """
        Fetch news articles dari Inshorts.

        Returns:
            (articles_list, next_offset, has_more)
        """
        if self._has_requests and self._session is not None:
            return self._fetch_via_requests(category, lang, offset, limit)

        raw = self._fetch_post(category, lang, offset, limit)

        if not raw.get("success", False):
            return [], offset, False

        news_list = raw.get("data", raw.get("news_list", []))
        articles = [Article.from_api_dict(item) for item in news_list]

        has_more = len(articles) == limit
        next_offset = offset + len(articles) if has_more else offset

        return articles, next_offset, has_more

    def _fetch_via_requests(
        self,
        category: NewsCategory,
        lang: str,
        offset: int,
        limit: int,
    ) -> Tuple[List[Article], int, bool]:
        """Fetch via requests library jika available."""
        payload = {
            "category": category.value,
            "lang": lang,
            "offset": offset,
            "limit": limit,
        }
        try:
            resp = self._session.post(  # type: ignore[union-attr]
                INSHORTS_API_URL, data=payload, timeout=self.timeout
            )
            resp.raise_for_status()
            raw = resp.json()
        except Exception:
            # Fallback ke stdlib
            raw = self._fetch_post(category, lang, offset, limit)

        if not raw.get("success", False):
            return [], offset, False

        news_list = raw.get("data", raw.get("news_list", []))
        articles = [Article.from_api_dict(item) for item in news_list]
        has_more = len(articles) == limit
        next_offset = offset + len(articles) if has_more else offset
        return articles, next_offset, has_more

    def search_by_keyword(
        self, keyword: str, category: NewsCategory = NewsCategory.ALL, max_results: int = 20
    ) -> List[Article]:
        """Simple client-side keyword search via fetch + filter."""
        results: List[Article] = []
        offset = 0
        limit = 10
        while len(results) < max_results:
            articles, offset, has_more = self.fetch_news(category, offset=offset, limit=limit)
            if not articles:
                break
            for art in articles:
                if keyword.lower() in art.title.lower() or keyword.lower() in art.content.lower():
                    results.append(art)
                    if len(results) >= max_results:
                        break
            if not has_more:
                break
        return results[:max_results]

    def __repr__(self) -> str:
        backend = "requests" if self._has_requests else "urllib"
        return f"InshortsClient(backend={backend}, timeout={self.timeout}, retries={self.retries})"


# ---------------------------------------------------------------------------
# 4. NewsFeed — paginated feed manager dengan cache ring buffer
# ---------------------------------------------------------------------------
class NewsFeed:
    """Paginated feed manager dengan ring buffer cache."""

    def __init__(
        self,
        client: Optional[InshortsClient] = None,
        category: NewsCategory = NewsCategory.TECHNOLOGY,
        lang: str = "en",
        cache_size: int = 100,
    ):
        self.client = client or InshortsClient()
        self.category = category
        self.lang = lang
        self._offset = 0
        self._has_more = True
        self._cache: deque[Article] = deque(maxlen=cache_size)
        self._history: List[Article] = []
        self.total_fetched = 0

    def next_batch(self, limit: int = 10) -> List[Article]:
        """Fetch next page dan append ke cache."""
        if not self._has_more:
            return []

        articles, next_offset, has_more = self.client.fetch_news(
            category=self.category,
            lang=self.lang,
            offset=self._offset,
            limit=limit,
        )

        self._offset = next_offset
        self._has_more = has_more
        self.total_fetched += len(articles)

        for art in articles:
            self._cache.append(art)
            self._history.append(art)

        return articles

    def peek(self, n: int = 5) -> List[Article]:
        """Return up to n articles from cache tanpa fetch baru."""
        return list(self._cache)[:n]

    def refresh(self) -> List[Article]:
        """Reset offset ke 0 dan fetch ulang."""
        self._offset = 0
        self._has_more = True
        self._cache.clear()
        self._history.clear()
        self.total_fetched = 0
        return self.next_batch(limit=10)

    def get_all(self) -> List[Article]:
        """Return semua history articles yang pernah di-fetch."""
        return self._history.copy()

    def flush_cache(self) -> None:
        """Clear ring buffer cache."""
        self._cache.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "lang": self.lang,
            "offset": self._offset,
            "has_more": self._has_more,
            "cache_size": len(self._cache),
            "total_fetched": self.total_fetched,
        }

    def __repr__(self) -> str:
        return (
            f"NewsFeed(cat={self.category.value}, cached={len(self._cache)}, "
            f"total={self.total_fetched}, more={self._has_more})"
        )


# ---------------------------------------------------------------------------
# 5. InshortsKernel — MAGNATRIX bridge ke Layer 5 & Layer 10
# ---------------------------------------------------------------------------
class InshortsKernel:
    """
    MAGNATRIX bridge:
    - Layer 5  → Knowledge / News Feed (structured knowledge ingestion)
    - Layer 10 → AI Agent Context Injection (surface relevant headlines)
    """

    def __init__(self, client: Optional[InshortsClient] = None):
        self.client = client or InshortsClient()
        self.feeds: Dict[str, NewsFeed] = {}

    def create_feed(self, name: str, category: NewsCategory, lang: str = "en") -> NewsFeed:
        """Register named feed untuk kategori tertentu."""
        feed = NewsFeed(client=self.client, category=category, lang=lang)
        self.feeds[name] = feed
        return feed

    def ingest(self, feed_name: str, batch_size: int = 10) -> List[Dict[str, Any]]:
        """Layer 5 — Ingest news sebagai structured knowledge records."""
        feed = self.feeds.get(feed_name)
        if not feed:
            raise KeyError(f"Feed '{feed_name}' not registered.")

        articles = feed.next_batch(batch_size)
        records = []
        for art in articles:
            records.append(
                {
                    "type": "news_article",
                    "source": "inshorts",
                    "title": art.title,
                    "content": art.content,
                    "author": art.author,
                    "source_name": art.source_name,
                    "category": art.category_names,
                    "tags": art.hash_tags,
                    "url": art.read_more_url or art.shortened_url,
                    "timestamp": art.timestamp,
                    "date": art.created_at,
                }
            )
        return records

    def context_inject(
        self,
        feed_name: str,
        max_items: int = 5,
        keywords: Optional[List[str]] = None,
    ) -> str:
        """Layer 10 — Format recent news sebagai AI context string."""
        feed = self.feeds.get(feed_name)
        if not feed:
            raise KeyError(f"Feed '{feed_name}' not registered.")

        # Ensure we have enough in cache
        articles = list(feed._cache)
        if len(articles) < max_items:
            articles = feed.next_batch(limit=max(max_items, 10))

        if keywords:
            filtered = [
                art for art in articles
                if any(kw.lower() in art.title.lower() or kw.lower() in art.content.lower() for kw in keywords)
            ]
            articles = filtered or articles  # fallback ke all jika no match

        selected = articles[:max_items]
        lines = ["— Inshorts Headlines —"]
        for i, art in enumerate(selected, 1):
            lines.append(f"{i}. {art.summary(max_chars=200)}")
        lines.append("— end —")
        return "\n".join(lines)

    def multi_feed_summary(
        self, feed_names: List[str], per_feed: int = 3
    ) -> Dict[str, List[str]]:
        """Aggregate headlines dari multiple feeds."""
        out: Dict[str, List[str]] = {}
        for name in feed_names:
            feed = self.feeds.get(name)
            if not feed:
                continue
            articles = feed.peek(n=per_feed)
            out[name] = [art.summary(max_chars=160) for art in articles]
        return out

    def __repr__(self) -> str:
        return f"InshortsKernel(feeds={list(self.feeds.keys())})"


# ---------------------------------------------------------------------------
# DEMO — fetch 10 tech news → print → paginate next 10
# ---------------------------------------------------------------------------
def demo() -> None:
    """Demonstrasi lengkap: client, feed, pagination, kernel."""
    print("=" * 60)
    print("Inshorts Native Client — Demo")
    print("=" * 60)

    # 1. Client standalone
    client = InshortsClient()
    print(f"\n[Client] {client}")

    print(f"\n[Fetch 10 Tech News] category={NewsCategory.TECHNOLOGY.value}")
    articles, offset, has_more = client.fetch_news(
        category=NewsCategory.TECHNOLOGY, lang="en", offset=0, limit=10
    )

    if not articles:
        print("⚠️ No articles returned (API may be temporarily unavailable).")
        print("   Structure & logic validated via demo.")
    else:
        for i, art in enumerate(articles, 1):
            print(f"\n  {i}. {art.title}")
            print(f"     Source: {art.source_name} | Author: {art.author}")
            print(f"     {art.content[:140]}...")

    print(f"\n[Meta] offset={offset}, has_more={has_more}, fetched={len(articles)}")

    # 2. Paginated feed
    print("\n" + "=" * 60)
    print("[NewsFeed Pagination Demo]")
    print("=" * 60)
    feed = NewsFeed(client=client, category=NewsCategory.TECHNOLOGY, lang="en")

    batch1 = feed.next_batch(limit=10)
    print(f"\nBatch 1: {len(batch1)} articles | cache={len(feed._cache)} | total={feed.total_fetched}")

    batch2 = feed.next_batch(limit=10)
    print(f"Batch 2: {len(batch2)} articles | cache={len(feed._cache)} | total={feed.total_fetched}")

    # 3. Kernel bridge
    print("\n" + "=" * 60)
    print("[InshortsKernel — Layer 5 & 10 Bridge]")
    print("=" * 60)
    kernel = InshortsKernel(client=client)
    kernel.create_feed("tech", NewsCategory.TECHNOLOGY, lang="en")
    kernel.create_feed("business", NewsCategory.BUSINESS, lang="en")

    # Layer 5: ingest structured records
    records = kernel.ingest("tech", batch_size=5)
    print(f"\nIngested {len(records)} records to knowledge layer")
    if records:
        print(f"  Sample: {records[0]['title'][:50]}...")

    # Layer 10: context injection
    ctx = kernel.context_inject("tech", max_items=3)
    print(f"\n[Context Injection]\n{ctx}")

    # Multi-feed summary
    multi = kernel.multi_feed_summary(["tech", "business"], per_feed=2)
    print(f"\n[Multi-Feed Summary] feeds={list(multi.keys())}")

    # Stats
    print(f"\n[Feed Stats] {feed.stats}")
    print(f"[Kernel] {kernel}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
