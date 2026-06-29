
"""
skill_marketplace_native.py
MAGNATRIX-OS — Skill Marketplace

Inspired by SkillKit marketplace: skill discovery, ranking,
caching, and community sharing. REST API + MCP server compatible.

Pure Python standard library.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class SkillListing:
    skill_id: str
    name: str
    description: str
    author: str
    tags: List[str] = field(default_factory=list)
    rating: float = 0.0
    downloads: int = 0
    version: str = "1.0.0"
    published_at: str = ""
    updated_at: str = ""
    formats: List[str] = field(default_factory=list)
    is_verified: bool = False

    def __post_init__(self):
        if not self.published_at:
            self.published_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.published_at


class SkillMarketplace:
    """Skill marketplace with discovery, ranking, and caching."""

    def __init__(self, cache_dir: str = "./marketplace_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.listings: Dict[str, SkillListing] = {}
        self.cache: Dict[str, Any] = {}
        self.cache_expiry: Dict[str, float] = {}
        self.CACHE_TTL = 3600  # 1 hour
        self._load_cache()

    def _load_cache(self) -> None:
        cache_file = self.cache_dir / "listings.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for lid, ld in data.items():
                    self.listings[lid] = SkillListing(**ld)

    def _save_cache(self) -> None:
        cache_file = self.cache_dir / "listings.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({lid: asdict(l) for lid, l in self.listings.items()}, f, indent=2)

    def publish(self, listing: SkillListing) -> bool:
        self.listings[listing.skill_id] = listing
        listing.updated_at = datetime.now().isoformat()
        self._save_cache()
        return True

    def unpublish(self, skill_id: str) -> bool:
        if skill_id in self.listings:
            del self.listings[skill_id]
            self._save_cache()
            return True
        return False

    def search(self, query: str, limit: int = 10) -> List[SkillListing]:
        q = query.lower()
        results = []
        for listing in self.listings.values():
            score = 0
            if q in listing.name.lower():
                score += 10
            if q in listing.description.lower():
                score += 5
            if q in listing.author.lower():
                score += 3
            for tag in listing.tags:
                if q in tag.lower():
                    score += 8
            if score > 0:
                results.append((score, listing))
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def rank(self, metric: str = "rating", limit: int = 10) -> List[SkillListing]:
        """Rank listings by metric."""
        listings = list(self.listings.values())
        if metric == "rating":
            listings.sort(key=lambda x: (x.rating, x.downloads), reverse=True)
        elif metric == "downloads":
            listings.sort(key=lambda x: x.downloads, reverse=True)
        elif metric == "recent":
            listings.sort(key=lambda x: x.updated_at, reverse=True)
        elif metric == "trending":
            # Composite: rating * downloads / age in days
            now = datetime.now()
            def trending_score(l):
                age = max(1, (now - datetime.fromisoformat(l.published_at)).days)
                return (l.rating * l.downloads) / age
            listings.sort(key=trending_score, reverse=True)
        return listings[:limit]

    def get_by_tag(self, tag: str, limit: int = 10) -> List[SkillListing]:
        results = [l for l in self.listings.values() if tag in l.tags]
        results.sort(key=lambda x: x.rating, reverse=True)
        return results[:limit]

    def download(self, skill_id: str) -> Optional[SkillListing]:
        listing = self.listings.get(skill_id)
        if listing:
            listing.downloads += 1
            self._save_cache()
        return listing

    def get_cache(self, key: str) -> Optional[Any]:
        if key in self.cache:
            if time.time() < self.cache_expiry.get(key, 0):
                return self.cache[key]
            del self.cache[key]
            del self.cache_expiry[key]
        return None

    def set_cache(self, key: str, value: Any, ttl: int = 3600) -> None:
        self.cache[key] = value
        self.cache_expiry[key] = time.time() + ttl

    def to_dict(self) -> Dict:
        return {
            "total_listings": len(self.listings),
            "cache_entries": len(self.cache),
            "top_rated": [l.name for l in self.rank("rating", 5)],
        }


__all__ = ["SkillMarketplace", "SkillListing"]
