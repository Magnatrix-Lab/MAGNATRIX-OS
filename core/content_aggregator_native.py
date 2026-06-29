
"""
content_aggregator_native.py
MAGNATRIX-OS — Content Aggregator

Aggregate content from multiple sources (social media, web, video)
into unified search results. Inspired by Agent-Reach.
Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class AggregatedResult:
    query: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    total_results: int = 0
    aggregated_at: str = ""

    def __post_init__(self):
        if not self.aggregated_at:
            self.aggregated_at = datetime.now().isoformat()


class ContentAggregator:
    """Aggregate search results from multiple internet sources."""

    def __init__(self, output_dir: str = "./aggregated"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.sources: Dict[str, Any] = {}
        self.history: List[AggregatedResult] = []

    def register_source(self, name: str, source_fn: Any) -> None:
        """Register a content source function."""
        self.sources[name] = source_fn

    def search(self, query: str, sources: Optional[List[str]] = None, count_per_source: int = 5) -> AggregatedResult:
        """Search across multiple sources and aggregate results."""
        sources = sources or list(self.sources.keys())
        result = AggregatedResult(query=query)
        for src_name in sources:
            if src_name in self.sources:
                try:
                    source_fn = self.sources[src_name]
                    if src_name == "web":
                        items = source_fn.search_duckduckgo(query, count_per_source)
                    elif src_name == "reddit":
                        items = [{"title": p.content[:100], "url": p.url, "author": p.author}
                                for p in source_fn.scrape_reddit(query, count=count_per_source)]
                    elif src_name == "github":
                        items = source_fn.search_github_repos(query, count_per_source)
                    elif src_name == "youtube":
                        # YouTube search via DuckDuckGo
                        web = self.sources.get("web")
                        items = web.search_duckduckgo(f"site:youtube.com {query}", count_per_source) if web else []
                    else:
                        items = []
                    if items:
                        result.sources.append({
                            "source": src_name,
                            "count": len(items),
                            "items": items,
                        })
                except Exception:
                    continue
        result.total_results = sum(s["count"] for s in result.sources)
        self.history.append(result)
        self._save(result)
        return result

    def _save(self, result: AggregatedResult) -> None:
        filename = f"agg_{result.query.replace(' ', '_')[:30]}_{int(datetime.now().timestamp())}.json"
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, indent=2)

    def get_recent(self, limit: int = 10) -> List[AggregatedResult]:
        return self.history[-limit:]

    def get_source_stats(self) -> Dict[str, int]:
        stats = {}
        for r in self.history:
            for s in r.sources:
                stats[s["source"]] = stats.get(s["source"], 0) + s["count"]
        return stats

    def to_dict(self) -> Dict[str, Any]:
        return {
            "registered_sources": list(self.sources.keys()),
            "total_queries": len(self.history),
            "source_stats": self.get_source_stats(),
        }


__all__ = ["ContentAggregator", "AggregatedResult"]
