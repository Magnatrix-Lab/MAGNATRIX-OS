
"""
social_media_scraper_native.py
MAGNATRIX-OS — Social Media Scraper

Inspired by Agent-Reach (Panniantong/Agent-Reach):
Scrape Twitter, Reddit, Bilibili, XiaoHongShu without API fees.
Pure Python standard library (urllib, regex, json).
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SocialPost:
    platform: str
    author: str
    content: str
    url: str
    timestamp: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    media: List[str] = field(default_factory=list)


class SocialMediaScraper:
    """Scrape social media platforms without API keys."""

    def __init__(self, user_agent: str = "Mozilla/5.0 (compatible; Agent-Reach/1.0)"):
        self.user_agent = user_agent
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "identity",
        }

    def _fetch(self, url: str, timeout: int = 15) -> Optional[str]:
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    def scrape_twitter(self, username: str, count: int = 5) -> List[SocialPost]:
        """Scrape Twitter/X profile posts via nitter proxy fallback."""
        posts = []
        # Try nitter instances (decentralized Twitter frontends)
        nitter_urls = [
            f"https://nitter.net/{username}",
            f"https://nitter.it/{username}",
        ]
        for nitter_url in nitter_urls:
            html = self._fetch(nitter_url)
            if html:
                # Extract tweets from HTML
                tweet_blocks = re.findall(r'<div class="timeline-item">(.*?)</div>\s*</div>', html, re.DOTALL)
                for block in tweet_blocks[:count]:
                    content_match = re.search(r'<div class="tweet-content[^"]*">.*?<p[^>]*>(.*?)</p>', block, re.DOTALL)
                    content = re.sub(r'<[^>]+>', '', content_match.group(1) if content_match else "")
                    date_match = re.search(r'<span[^>]*title="([^"]+)"', block)
                    timestamp = date_match.group(1) if date_match else datetime.now().isoformat()
                    posts.append(SocialPost(
                        platform="twitter", author=username, content=content.strip(),
                        url=f"https://twitter.com/{username}", timestamp=timestamp,
                    ))
                break
        return posts

    def scrape_reddit(self, subreddit: str, sort: str = "hot", count: int = 5) -> List[SocialPost]:
        """Scrape Reddit posts via JSON API (no auth required for public)."""
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={count}"
        self.headers["Accept"] = "application/json"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                posts = []
                for child in data.get("data", {}).get("children", [])[:count]:
                    post = child.get("data", {})
                    posts.append(SocialPost(
                        platform="reddit", author=post.get("author", "unknown"),
                        content=post.get("title", "") + "\n" + post.get("selftext", ""),
                        url=f"https://reddit.com{post.get('permalink', '')}",
                        timestamp=datetime.fromtimestamp(post.get("created_utc", 0)).isoformat(),
                        likes=post.get("ups", 0), comments=post.get("num_comments", 0),
                    ))
                return posts
        except Exception:
            return []

    def scrape_bilibili(self, bvid: str) -> Dict[str, Any]:
        """Scrape Bilibili video info via public API."""
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        try:
            req = urllib.request.Request(api_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                if data.get("code") == 0:
                    d = data["data"]
                    return {
                        "title": d.get("title", ""),
                        "description": d.get("desc", ""),
                        "author": d.get("owner", {}).get("name", ""),
                        "views": d.get("stat", {}).get("view", 0),
                        "likes": d.get("stat", {}).get("like", 0),
                        "comments": d.get("stat", {}).get("reply", 0),
                        "duration": d.get("duration", 0),
                        "tags": [t.get("tag_name", "") for t in d.get("tags", [])],
                    }
        except Exception:
            pass
        return {}

    def scrape_xiaohongshu(self, note_id: str) -> Dict[str, Any]:
        """Scrape XiaoHongShu (Little Red Book) note via public web."""
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        html = self._fetch(url)
        if html:
            # Extract JSON-LD or embedded data
            json_match = re.search(r'<script>window\.__INITIAL_STATE__\s*=\s*({.*?})</script>', html, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    note = data.get("note", {}).get("noteDetailMap", {}).get(note_id, {})
                    return {
                        "title": note.get("title", ""),
                        "content": note.get("desc", ""),
                        "author": note.get("user", {}).get("nickname", ""),
                        "likes": note.get("interactInfo", {}).get("likedCount", 0),
                        "comments": note.get("interactInfo", {}).get("commentCount", 0),
                        "images": [img.get("url", "") for img in note.get("imageList", [])],
                    }
                except Exception:
                    pass
        return {}

    def search_github_repos(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """Search GitHub repositories via public search."""
        encoded = urllib.parse.quote(query)
        url = f"https://api.github.com/search/repositories?q={encoded}&per_page={count}"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                return [{
                    "name": item.get("full_name", ""),
                    "description": item.get("description", ""),
                    "url": item.get("html_url", ""),
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language", ""),
                    "updated": item.get("updated_at", ""),
                } for item in data.get("items", [])[:count]]
        except Exception:
            return []

    def to_dict(self) -> Dict[str, Any]:
        return {"platforms": ["twitter", "reddit", "bilibili", "xiaohongshu", "github"], "user_agent": self.user_agent}


__all__ = ["SocialMediaScraper", "SocialPost"]
