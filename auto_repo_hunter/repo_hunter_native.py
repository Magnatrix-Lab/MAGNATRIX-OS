#!/usr/bin/env python3
"""
Auto Repo Hunter — GitHub API Repository Discovery Engine
Layer 13.5 — Self Improvement

Pure Python stdlib + requests. Searches GitHub for repos by stars/language/topic,
handles rate limiting, caches results, ranks by relevance score.
"""

import json
import os
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GITHUB_API = "https://api.github.com"
DEFAULT_PER_PAGE = 30
MAX_PER_PAGE = 100
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class RepoResult:
    """A discovered repository with metadata."""
    full_name: str
    html_url: str
    description: Optional[str] = None
    stars: int = 0
    forks: int = 0
    language: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    open_issues: int = 0
    size_kb: int = 0
    license: Optional[str] = None
    raw_json: Dict[str, Any] = field(default_factory=dict, repr=False)
    relevance_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SearchQuery:
    """Structured search query for GitHub."""
    keywords: List[str] = field(default_factory=list)
    language: Optional[str] = None
    min_stars: Optional[int] = None
    max_stars: Optional[int] = None
    topics: List[str] = field(default_factory=list)
    created_after: Optional[str] = None  # ISO date
    pushed_after: Optional[str] = None
    sort: str = "stars"  # stars, forks, updated
    order: str = "desc"

    def build_q(self) -> str:
        parts = list(self.keywords)
        if self.language:
            parts.append(f"language:{self.language}")
        if self.min_stars is not None:
            parts.append(f"stars:>={self.min_stars}")
        if self.max_stars is not None:
            parts.append(f"stars:<={self.max_stars}")
        for t in self.topics:
            parts.append(f"topic:{t}")
        if self.created_after:
            parts.append(f"created:>{self.created_after}")
        if self.pushed_after:
            parts.append(f"pushed:>{self.pushed_after}")
        return " ".join(parts)

# ---------------------------------------------------------------------------
# Rate Limit Manager
# ---------------------------------------------------------------------------
class RateLimitManager:
    """Tracks GitHub API rate limits and sleeps when needed."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.remaining = 5000 if self.token else 60
        self.reset_at: Optional[float] = None
        self.last_check: float = 0.0

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github+json", "User-Agent": "Magnatrix-AutoRepoHunter/1.0"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _update_from_response(self, response: Any) -> None:
        """Parse rate limit headers from a response."""
        try:
            self.remaining = int(response.headers.get("X-RateLimit-Remaining", self.remaining))
            reset_ts = int(response.headers.get("X-RateLimit-Reset", 0))
            if reset_ts:
                self.reset_at = reset_ts
        except (ValueError, TypeError):
            pass

    def wait_if_needed(self) -> None:
        """Sleep if we are close to hitting the limit."""
        if self.remaining <= 1 and self.reset_at:
            now = time.time()
            wait = max(self.reset_at - now + 1, 1)
            print(f"[RateLimit] sleeping {wait:.0f}s until reset…")
            time.sleep(wait)
            self.remaining = 5000 if self.token else 60

    def request(self, url: str, method: str = "GET", data: Optional[bytes] = None) -> Dict[str, Any]:
        """Make a rate-limited HTTP request and return JSON."""
        self.wait_if_needed()
        req = urllib.request.Request(url, headers=self._headers(), method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, data=data, timeout=30) as resp:
                self._update_from_response(resp)
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            self._update_from_response(e)
            if e.code == 403 and self.remaining <= 0:
                self.wait_if_needed()
                return self.request(url, method, data)
            if e.code == 404:
                return {"__error": "not_found", "status": 404}
            raise

# ---------------------------------------------------------------------------
# Repo Hunter Engine
# ---------------------------------------------------------------------------
class RepoHunter:
    """GitHub repository discovery engine."""

    def __init__(self, token: Optional[str] = None):
        self.rl = RateLimitManager(token)
        self.cache: Dict[str, Any] = {}

    def _cache_key(self, query: SearchQuery, page: int) -> str:
        return f"{query.build_q()}|{query.sort}|{page}"

    def _cache_path(self, key: str) -> str:
        safe = "".join(c if c.isalnum() else "_" for c in key)[:120]
        return os.path.join(CACHE_DIR, f"{safe}.json")

    def _load_cache(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._cache_path(key)
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if time.time() - mtime < 3600:  # 1 hour TTL
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        return None

    def _save_cache(self, key: str, data: Dict[str, Any]) -> None:
        path = self._cache_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _parse_repo(self, item: Dict[str, Any]) -> RepoResult:
        return RepoResult(
            full_name=item.get("full_name", ""),
            html_url=item.get("html_url", ""),
            description=item.get("description"),
            stars=item.get("stargazers_count", 0),
            forks=item.get("forks_count", 0),
            language=item.get("language"),
            topics=item.get("topics", []),
            created_at=item.get("created_at"),
            updated_at=item.get("updated_at"),
            open_issues=item.get("open_issues_count", 0),
            size_kb=item.get("size", 0),
            license=item.get("license", {}).get("spdx_id") if item.get("license") else None,
            raw_json=item,
        )

    def _score_relevance(self, repo: RepoResult, query: SearchQuery) -> float:
        """Score repo relevance 0.0–1.0 based on query match."""
        score = 0.0
        # Stars weight (log scale, capped)
        score += min(repo.stars / 10000, 1.0) * 0.25
        # Language exact match
        if query.language and repo.language and repo.language.lower() == query.language.lower():
            score += 0.20
        # Topic overlap
        if query.topics and repo.topics:
            overlap = len(set(t.lower() for t in query.topics) & set(t.lower() for t in repo.topics))
            score += min(overlap / max(len(query.topics), 1), 1.0) * 0.25
        # Recency — updated within 90 days
        if repo.updated_at:
            try:
                updated = datetime.fromisoformat(repo.updated_at.replace("Z", "+00:00"))
                age_days = (datetime.now(updated.tzinfo) - updated).days
                if age_days < 90:
                    score += 0.15
                elif age_days < 365:
                    score += 0.05
            except ValueError:
                pass
        # Description quality
        if repo.description and len(repo.description) > 20:
            score += 0.10
        # Has license
        if repo.license:
            score += 0.05
        return round(min(score, 1.0), 3)

    def search(self, query: SearchQuery, max_results: int = 30, use_cache: bool = True) -> List[RepoResult]:
        """Execute a GitHub search and return ranked RepoResults."""
        results: List[RepoResult] = []
        per_page = min(MAX_PER_PAGE, max_results)
        pages_needed = (max_results + per_page - 1) // per_page

        for page in range(1, pages_needed + 1):
            if len(results) >= max_results:
                break

            key = self._cache_key(query, page)
            if use_cache:
                cached = self._load_cache(key)
                if cached:
                    items = cached.get("items", [])
                    for item in items:
                        repo = self._parse_repo(item)
                        repo.relevance_score = self._score_relevance(repo, query)
                        results.append(repo)
                    continue

            q = urllib.parse.quote(query.build_q())
            url = (
                f"{GITHUB_API}/search/repositories?q={q}"
                f"&sort={query.sort}&order={query.order}"
                f"&per_page={per_page}&page={page}"
            )
            data = self.rl.request(url)
            if "__error" in data:
                print(f"[RepoHunter] search error: {data['__error']}")
                break

            items = data.get("items", [])
            if use_cache:
                self._save_cache(key, data)

            for item in items:
                repo = self._parse_repo(item)
                repo.relevance_score = self._score_relevance(repo, query)
                results.append(repo)

            if len(items) < per_page:
                break

        # Sort by relevance score desc, then stars desc
        results.sort(key=lambda r: (-r.relevance_score, -r.stars))
        return results[:max_results]

    def get_repo_details(self, full_name: str) -> Optional[RepoResult]:
        """Fetch detailed metadata for a single repo."""
        url = f"{GITHUB_API}/repos/{full_name}"
        data = self.rl.request(url)
        if "__error" in data:
            return None
        return self._parse_repo(data)

    def get_readme(self, full_name: str) -> Optional[str]:
        """Fetch raw README.md content for a repo."""
        url = f"{GITHUB_API}/repos/{full_name}/readme"
        data = self.rl.request(url)
        if "__error" in data:
            return None
        download_url = data.get("download_url")
        if not download_url:
            return None
        try:
            req = urllib.request.Request(download_url, headers=self.rl._headers())
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"[RepoHunter] README download failed for {full_name}: {e}")
            return None

    def get_languages(self, full_name: str) -> Dict[str, int]:
        """Fetch language breakdown for a repo."""
        url = f"{GITHUB_API}/repos/{full_name}/languages"
        data = self.rl.request(url)
        if "__error" in data:
            return {}
        return {k: v for k, v in data.items() if isinstance(v, int)}

    def get_tree(self, full_name: str, sha: str = "HEAD") -> List[Dict[str, Any]]:
        """Fetch repository file tree (recursive, limited)."""
        url = f"{GITHUB_API}/repos/{full_name}/git/trees/{sha}?recursive=1"
        data = self.rl.request(url)
        if "__error" in data:
            return []
        return data.get("tree", [])

    def get_file_content(self, full_name: str, path: str, ref: str = "HEAD") -> Optional[str]:
        """Fetch raw content of a single file."""
        url = f"{GITHUB_API}/repos/{full_name}/contents/{path}?ref={ref}"
        data = self.rl.request(url)
        if "__error" in data:
            return None
        import base64
        encoded = data.get("content", "")
        if encoded:
            try:
                return base64.b64decode(encoded).decode("utf-8", errors="replace")
            except Exception:
                pass
        download_url = data.get("download_url")
        if download_url:
            try:
                req = urllib.request.Request(download_url, headers=self.rl._headers())
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except Exception as e:
                print(f"[RepoHunter] file download failed: {e}")
        return None

    def trending(self, language: Optional[str] = None, since: str = "daily", max_results: int = 10) -> List[RepoResult]:
        """Discover trending repos using a pushed-after heuristic."""
        days = {"daily": 1, "weekly": 7, "monthly": 30}.get(since, 7)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        q = SearchQuery(min_stars=50, pushed_after=cutoff, sort="stars", order="desc")
        if language:
            q.language = language
        return self.search(q, max_results=max_results)

# ---------------------------------------------------------------------------
# CLI / Self-Test
# ---------------------------------------------------------------------------
def _demo() -> None:
    hunter = RepoHunter()
    print("=" * 60)
    print("Auto Repo Hunter — Demo Search")
    print("=" * 60)

    # Demo 1: Python repos with >1000 stars, topic "machine-learning"
    q1 = SearchQuery(
        keywords=["machine learning"],
        language="python",
        min_stars=1000,
        topics=["machine-learning"],
        sort="stars",
    )
    print(f"\n🔍 Query: {q1.build_q()}")
    repos = hunter.search(q1, max_results=5)
    for i, r in enumerate(repos, 1):
        print(f"  {i}. {r.full_name} ⭐{r.stars} 🎯{r.relevance_score}")
        print(f"     {r.html_url}")
        if r.description:
            print(f"     {r.description[:100]}…")

    # Demo 2: Trending Python this week
    print("\n🔥 Trending Python (weekly)")
    trending = hunter.trending(language="python", since="weekly", max_results=5)
    for i, r in enumerate(trending, 1):
        print(f"  {i}. {r.full_name} ⭐{r.stars} 🎯{r.relevance_score}")

    # Demo 3: README fetch
    if repos:
        first = repos[0]
        print(f"\n📄 README preview for {first.full_name}:")
        readme = hunter.get_readme(first.full_name)
        if readme:
            preview = readme[:500].replace("\n", " ")
            print(f"     {preview}…")
        else:
            print("     (no README found)")

    print("\n✅ Demo complete.")

if __name__ == "__main__":
    _demo()
