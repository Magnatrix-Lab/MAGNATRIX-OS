#!/usr/bin/env python3
"""
inshorts_native.py
═══════════════════════════════════════════════════════════════════════════════
Inshorts News API Native — Unofficial API wrapper for Inshorts news platform
Pure Python · stdlib only · zero external dependencies

Observed repo: sumitkolhe/inshorts
  — Unofficial API for Inshorts news platform
  — 18 categories, pagination, bilingual (en/hi)
  — 60-word news summaries with images, timestamps, sources

Target: ~400 lines · Single file · Runnable without install
Author: GQRIS (AMATI-PELAJARI-TIRU)
"""

from __future__ import annotations

import json
import logging
import random
import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════
# Section 1 — BaseLayer
# Enums, Data Models, Request Builder
# ════════════════════════════════════════════════════════════════

class NewsCategory(Enum):
    """All 18 news categories supported by Inshorts."""
    TOP_STORIES     = "top_stories"
    NATIONAL        = "national"
    BUSINESS        = "business"
    SPORTS          = "sports"
    WORLD           = "world"
    POLITICS        = "politics"
    TECHNOLOGY      = "technology"
    STARTUP         = "startup"
    ENTERTAINMENT   = "entertainment"
    MISCELLANEOUS   = "miscellaneous"
    HATKE           = "hatke"
    SCIENCE         = "science"
    AUTOMOBILE      = "automobile"
    TRAVEL          = "travel"
    FASHION         = "fashion"
    EDUCATION       = "education"
    HEALTH          = "health"
    FOOD            = "food"


class Language(Enum):
    """Supported languages."""
    ENGLISH = "en"
    HINDI   = "hi"


@dataclass(frozen=True)
class NewsArticle:
    """Single news article from Inshorts."""
    title:        str
    content:      str
    link:         str
    image_url:    str
    author:       str
    category:     str
    language:     str
    published_at: str  # ISO 8601
    source:       str
    read_more:    str = ""  # deep link to full article

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 0) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent or None)

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def summary(self) -> str:
        """Human-readable one-line summary."""
        return f"[{self.category.upper()}] {self.title[:60]}... ({self.author})"


@dataclass
class NewsFeed:
    """Paginated feed result."""
    category:   str
    language:   str
    articles:   List[NewsArticle] = field(default_factory=list)
    offset:     int = 0
    has_more:   bool = True
    total_seen: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category":   self.category,
            "language":   self.language,
            "offset":     self.offset,
            "has_more":   self.has_more,
            "total_seen": self.total_seen,
            "articles":   [a.to_dict() for a in self.articles],
        }

    def to_json(self, indent: int = 0) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent or None)


@dataclass
class SearchResult:
    """Search across categories."""
    query:      str
    articles:   List[NewsArticle] = field(default_factory=list)
    total:      int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query":    self.query,
            "total":    self.total,
            "articles": [a.to_dict() for a in self.articles],
        }


# ──────────────────────────────────────────────────────────────
# 1.1 Request Builder — HTTP layer (stdlib only)
# ──────────────────────────────────────────────────────────────

class InshortsRequestBuilder:
    """Constructs HTTP requests to Inshorts endpoints."""

    BASE_URL = "https://inshorts.com/api/v1/public"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE

    def _fetch(self, url: str) -> Optional[Dict[str, Any]]:
        """Execute GET and parse JSON."""
        req = urllib.request.Request(url, headers=self.HEADERS)
        try:
            with urllib.request.urlopen(req, context=self._ctx, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            logger.warning("HTTP %s: %s", e.code, url)
        except urllib.error.URLError as e:
            logger.warning("URL error: %s — %s", e.reason, url)
        except json.JSONDecodeError as e:
            logger.warning("JSON parse error: %s", e)
        except Exception as e:
            logger.warning("Fetch failed: %s", e)
        return None

    def fetch_news(
        self,
        category: str,
        language: str = "en",
        offset:   int = 0,
        limit:    int = 10,
    ) -> Optional[Dict[str, Any]]:
        """Fetch raw news payload for a category."""
        params = f"category={category}&lang={language}&max_limit={limit}&include_card_data=true"
        if offset > 0:
            params += f"&news_offset={offset}"
        url = f"{self.BASE_URL}/news?{params}"
        return self._fetch(url)

    def fetch_all_categories(self, language: str = "en") -> Optional[Dict[str, Any]]:
        """Fetch available categories metadata."""
        url = f"{self.BASE_URL}/categories?lang={language}"
        return self._fetch(url)


# ════════════════════════════════════════════════════════════════
# Section 2 — CoreEngine
# Parser, Feed Generator, Search Engine
# ════════════════════════════════════════════════════════════════

class InshortsParser:
    """Parse raw Inshorts JSON into structured dataclasses."""

    @staticmethod
    def parse_article(raw: Dict[str, Any], category: str, language: str) -> Optional[NewsArticle]:
        """Extract article from raw card data."""
        try:
            title = raw.get("title", "").strip()
            content = raw.get("content", "").strip()
            if not title or not content:
                return None

            return NewsArticle(
                title=title,
                content=content,
                link=raw.get("source_url", raw.get("url", "")),
                image_url=raw.get("image_url", raw.get("imageUrl", "")),
                author=raw.get("author_name", raw.get("author", "Inshorts")),
                category=category,
                language=language,
                published_at=InshortsParser._parse_time(raw.get("created_at", raw.get("date", ""))),
                source=raw.get("source_name", raw.get("source", "Inshorts")),
                read_more=raw.get("deeplink", ""),
            )
        except Exception as e:
            logger.debug("Parse error: %s", e)
            return None

    @staticmethod
    def _parse_time(ts_raw: Any) -> str:
        """Convert Inshorts timestamp to ISO 8601."""
        if not ts_raw:
            return datetime.now(timezone.utc).isoformat()
        try:
            # Try epoch milliseconds
            if isinstance(ts_raw, (int, float)):
                dt = datetime.fromtimestamp(ts_raw / 1000.0, tz=timezone.utc)
                return dt.isoformat()
            # Try string formats
            if isinstance(ts_raw, str):
                if ts_raw.isdigit():
                    dt = datetime.fromtimestamp(int(ts_raw) / 1000.0, tz=timezone.utc)
                    return dt.isoformat()
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d %b %Y, %H:%M"):
                    try:
                        dt = datetime.strptime(ts_raw, fmt).replace(tzinfo=timezone.utc)
                        return dt.isoformat()
                    except ValueError:
                        continue
            return str(ts_raw)
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def parse_feed(
        payload:  Dict[str, Any],
        category: str,
        language: str,
        offset:   int,
    ) -> NewsFeed:
        """Parse full feed response."""
        feed = NewsFeed(category=category, language=language, offset=offset)
        data = payload.get("data", {})
        news_list = data.get("news_list", data.get("newsList", []))
        min_news_id = data.get("min_news_id", data.get("minNewsId", None))

        for item in news_list:
            raw = item.get("news_obj", item)
            article = InshortsParser.parse_article(raw, category, language)
            if article:
                feed.articles.append(article)
                feed.total_seen += 1

        feed.has_more = min_news_id is not None and len(feed.articles) > 0
        if feed.has_more and min_news_id:
            try:
                feed.offset = int(min_news_id)
            except (ValueError, TypeError):
                feed.offset = offset + len(feed.articles)
        return feed


class InshortsFeedGenerator:
    """High-level feed generator with pagination and caching."""

    def __init__(self, builder: Optional[InshortsRequestBuilder] = None):
        self.builder = builder or InshortsRequestBuilder()
        self.parser = InshortsParser()
        self._cache: Dict[str, Tuple[float, NewsFeed]] = {}
        self.cache_ttl = 300.0  # 5 minutes

    def _cache_key(self, category: str, language: str, offset: int) -> str:
        return f"{category}:{language}:{offset}"

    def get_feed(
        self,
        category: str,
        language: str = "en",
        offset:   int = 0,
        limit:    int = 10,
        use_cache: bool = True,
    ) -> NewsFeed:
        """Fetch a single page of news."""
        key = self._cache_key(category, language, offset)
        now = time.time()
        if use_cache and key in self._cache:
            ts, cached = self._cache[key]
            if now - ts < self.cache_ttl:
                return cached

        payload = self.builder.fetch_news(category, language, offset, limit)
        if payload:
            feed = self.parser.parse_feed(payload, category, language, offset)
            self._cache[key] = (now, feed)
            return feed

        return NewsFeed(category=category, language=language, offset=offset, has_more=False)

    def iter_feed(
        self,
        category:  str,
        language:  str = "en",
        max_pages: int = 5,
        limit:     int = 10,
    ):
        """Generator yielding successive pages."""
        offset = 0
        for _ in range(max_pages):
            feed = self.get_feed(category, language, offset, limit, use_cache=False)
            if not feed.articles:
                break
            yield feed
            if not feed.has_more:
                break
            offset = feed.offset

    def all_articles(
        self,
        category:  str,
        language:  str = "en",
        max_pages: int = 5,
        limit:     int = 10,
    ) -> List[NewsArticle]:
        """Collect all articles across pages."""
        result: List[NewsArticle] = []
        for feed in self.iter_feed(category, language, max_pages, limit):
            result.extend(feed.articles)
        return result

    def trending(self, language: str = "en", samples: int = 5) -> List[NewsArticle]:
        """Sample trending articles from top categories."""
        result: List[NewsArticle] = []
        cats = [
            NewsCategory.TOP_STORIES,
            NewsCategory.TECHNOLOGY,
            NewsCategory.WORLD,
            NewsCategory.BUSINESS,
            NewsCategory.SCIENCE,
        ]
        for cat in cats:
            feed = self.get_feed(cat.value, language, limit=samples)
            result.extend(feed.articles)
        random.shuffle(result)
        return result[:samples]

    def clear_cache(self) -> None:
        self._cache.clear()


class InshortsSearchEngine:
    """Simple in-memory search across fetched articles."""

    def __init__(self, generator: Optional[InshortsFeedGenerator] = None):
        self.generator = generator or InshortsFeedGenerator()

    def search(
        self,
        query:       str,
        categories:  Optional[List[str]] = None,
        language:    str = "en",
        max_results: int = 20,
    ) -> SearchResult:
        """Search articles by keyword across categories."""
        cats = categories or [c.value for c in NewsCategory]
        qlower = query.lower()
        result = SearchResult(query=query)
        seen_links: set = set()

        for cat in cats:
            articles = self.generator.all_articles(cat, language, max_pages=2, limit=10)
            for art in articles:
                if art.link in seen_links:
                    continue
                text = f"{art.title} {art.content} {art.author} {art.source}".lower()
                if qlower in text:
                    result.articles.append(art)
                    seen_links.add(art.link)
                    if len(result.articles) >= max_results:
                        result.total = len(result.articles)
                        return result

        result.total = len(result.articles)
        return result

    def search_exact(
        self,
        query:       str,
        categories:  Optional[List[str]] = None,
        language:    str = "en",
        max_results: int = 20,
    ) -> SearchResult:
        """Word-boundary exact match search."""
        cats = categories or [c.value for c in NewsCategory]
        pattern = re.compile(rf"\b{re.escape(query.lower())}\b")
        result = SearchResult(query=query)
        seen_links: set = set()

        for cat in cats:
            articles = self.generator.all_articles(cat, language, max_pages=2, limit=10)
            for art in articles:
                if art.link in seen_links:
                    continue
                text = f"{art.title} {art.content}".lower()
                if pattern.search(text):
                    result.articles.append(art)
                    seen_links.add(art.link)
                    if len(result.articles) >= max_results:
                        result.total = len(result.articles)
                        return result

        result.total = len(result.articles)
        return result


# ════════════════════════════════════════════════════════════════
# Section 3 — Features
# CLI, Export, Analytics
# ════════════════════════════════════════════════════════════════

class InshortsCLI:
    """Command-line interface for quick news access."""

    def __init__(self, generator: Optional[InshortsFeedGenerator] = None):
        self.generator = generator or InshortsFeedGenerator()

    def print_feed(
        self,
        category: str,
        language: str = "en",
        pages:    int = 1,
        limit:    int = 10,
    ) -> None:
        """Pretty-print news feed to stdout."""
        for page_num, feed in enumerate(self.generator.iter_feed(category, language, pages, limit), 1):
            print(f"\n{'═'*60}")
            print(f"  📰  {category.upper()}  —  Page {page_num}  ({language})")
            print(f"{'═'*60}")
            for art in feed.articles:
                print(f"\n  ▸ {art.title}")
                print(f"    {art.content[:120]}...")
                print(f"    — {art.author}  |  {art.published_at[:10]}  |  {art.source}")
                if art.link:
                    print(f"    🔗 {art.link}")
            print(f"\n  {'─'*56}")
            print(f"  Articles: {len(feed.articles)}  |  Has more: {feed.has_more}")

    def print_trending(self, samples: int = 5) -> None:
        """Print trending sample."""
        articles = self.generator.trending(samples=samples)
        print(f"\n{'═'*60}")
        print(f"  🔥  TRENDING NOW")
        print(f"{'═'*60}")
        for art in articles:
            print(f"\n  [{art.category.upper()}] {art.title}")
            print(f"  {art.content[:100]}...")

    def print_categories(self, language: str = "en") -> None:
        """List all available categories."""
        print(f"\n{'═'*60}")
        print(f"  📂  NEWS CATEGORIES  ({language})")
        print(f"{'═'*60}")
        for i, cat in enumerate(NewsCategory, 1):
            print(f"  {i:2}. {cat.value:20} — {cat.name.replace('_', ' ').title()}")


class InshortsExporter:
    """Export feeds to various formats."""

    @staticmethod
    def to_json(feed: NewsFeed, indent: int = 2) -> str:
        return feed.to_json(indent)

    @staticmethod
    def to_jsonl(articles: List[NewsArticle]) -> str:
        return "\n".join(a.to_json() for a in articles)

    @staticmethod
    def to_markdown(articles: List[NewsArticle]) -> str:
        lines = ["# Inshorts News Feed\n"]
        for art in articles:
            lines.append(f"## {art.title}\n")
            lines.append(f"**{art.category.upper()}**  |  {art.author}  |  {art.published_at[:10]}\n")
            lines.append(f"{art.content}\n")
            if art.link:
                lines.append(f"[Read more]({art.link})\n")
            if art.image_url:
                lines.append(f"![Image]({art.image_url})\n")
            lines.append("---\n")
        return "\n".join(lines)

    @staticmethod
    def to_rss(articles: List[NewsArticle], title: str = "Inshorts Feed") -> str:
        """Generate minimal RSS 2.0 XML."""
        now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        items = []
        for art in articles:
            items.append(
                f"    <item>\n"
                f"      <title>{_xml_escape(art.title)}</title>\n"
                f"      <description>{_xml_escape(art.content)}</description>\n"
                f"      <link>{_xml_escape(art.link)}</link>\n"
                f"      <pubDate>{art.published_at[:10]}</pubDate>\n"
                f"      <category>{_xml_escape(art.category)}</category>\n"
                f"    </item>"
            )
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<rss version="2.0">\n'
            f"  <channel>\n"
            f"    <title>{_xml_escape(title)}</title>\n"
            f"    <link>https://inshorts.com</link>\n"
            f"    <description>News in 60 words</description>\n"
            f"    <lastBuildDate>{now}</lastBuildDate>\n"
            f"    {chr(10).join(items)}\n"
            f"  </channel>\n"
            f"</rss>"
        )


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class InshortsAnalytics:
    """Simple analytics over collected articles."""

    @staticmethod
    def category_distribution(articles: List[NewsArticle]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for art in articles:
            dist[art.category] = dist.get(art.category, 0) + 1
        return dict(sorted(dist.items(), key=lambda x: x[1], reverse=True))

    @staticmethod
    def author_distribution(articles: List[NewsArticle], top_n: int = 10) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for art in articles:
            dist[art.author] = dist.get(art.author, 0) + 1
        return dict(sorted(dist.items(), key=lambda x: x[1], reverse=True)[:top_n])

    @staticmethod
    def hourly_pattern(articles: List[NewsArticle]) -> Dict[int, int]:
        """Distribution by hour of day."""
        dist: Dict[int, int] = {}
        for art in articles:
            try:
                dt = datetime.fromisoformat(art.published_at.replace("Z", "+00:00"))
                dist[dt.hour] = dist.get(dt.hour, 0) + 1
            except Exception:
                continue
        return dict(sorted(dist.items()))


# ════════════════════════════════════════════════════════════════
# Section 4 — Kernel / Integration Bridge
# MAGNATRIX Layer 6 (Media/Content) bridge
# ════════════════════════════════════════════════════════════════

@dataclass
class InshortsKernelConfig:
    """Configuration for kernel integration."""
    default_language: str = "en"
    default_limit:    int = 10
    cache_enabled:    bool = True
    timeout:          int = 15


class InshortsKernel:
    """MAGNATRIX integration kernel — bridges news to agent memory."""

    def __init__(self, config: Optional[InshortsKernelConfig] = None):
        self.config = config or InshortsKernelConfig()
        self.builder = InshortsRequestBuilder(timeout=self.config.timeout)
        self.generator = InshortsFeedGenerator(self.builder)
        self.search = InshortsSearchEngine(self.generator)
        self.cli = InshortsCLI(self.generator)
        self.exporter = InshortsExporter()

    def news_brief(self, category: str = "top_stories", count: int = 5) -> str:
        """Generate a plain-text brief for agent consumption."""
        feed = self.generator.get_feed(category, self.config.default_language, limit=count)
        lines = [f"📰 News Brief — {category.upper()} ({len(feed.articles)} items)"]
        for art in feed.articles:
            lines.append(f"\n• {art.title}")
            lines.append(f"  {art.content}")
            lines.append(f"  — {art.author}, {art.published_at[:10]}")
        return "\n".join(lines)

    def trending_digest(self, count: int = 5) -> str:
        """Cross-category trending digest."""
        articles = self.generator.trending(language=self.config.default_language, samples=count)
        lines = [f"🔥 Trending Digest ({len(articles)} items)"]
        for art in articles:
            lines.append(f"\n[{art.category}] {art.title}")
            lines.append(f"  {art.content[:100]}...")
        return "\n".join(lines)

    def search_digest(self, query: str, max_results: int = 5) -> str:
        """Search and format results."""
        result = self.search.search(query, language=self.config.default_language, max_results=max_results)
        lines = [f'🔍 Search: "{query}" — {result.total} results']
        for art in result.articles:
            lines.append(f"\n• {art.title}")
            lines.append(f"  {art.content[:120]}...")
        return "\n".join(lines)

    def health_check(self) -> Dict[str, Any]:
        """Quick connectivity check."""
        start = time.time()
        feed = self.generator.get_feed("top_stories", limit=1, use_cache=False)
        latency = round((time.time() - start) * 1000, 2)
        return {
            "status":     "healthy" if feed.articles else "degraded",
            "latency_ms": latency,
            "articles":   len(feed.articles),
            "cached":     bool(self.generator._cache),
        }


# ════════════════════════════════════════════════════════════════
# DEMO
# ════════════════════════════════════════════════════════════════

def _demo() -> None:
    print("Inshorts News API Native — Demo Run")
    print("═" * 60)

    kernel = InshortsKernel()

    # Health check
    health = kernel.health_check()
    print(f"\n1. Health Check: {health}")

    # Category listing
    kernel.cli.print_categories()

    # Fetch a feed
    print("\n2. Fetching TOP_STORIES...")
    feed = kernel.generator.get_feed("top_stories", limit=3)
    print(f"   Got {len(feed.articles)} articles, has_more={feed.has_more}")
    for art in feed.articles:
        print(f"   • {art.summary}")

    # Trending digest
    print("\n3. Trending Digest:")
    print(kernel.trending_digest(count=3))

    # Search
    print("\n4. Search Demo (query='tech'):")
    print(kernel.search_digest("tech", max_results=3))

    # Export demo
    if feed.articles:
        print("\n5. Export Formats:")
        print(f"   JSON size: {len(InshortsExporter.to_json(feed))} chars")
        print(f"   Markdown size: {len(InshortsExporter.to_markdown(feed.articles))} chars")

    print("\n" + "═" * 60)
    print("Demo complete. Kernel ready for MAGNATRIX integration.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    _demo()
