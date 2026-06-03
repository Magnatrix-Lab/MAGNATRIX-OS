"""LLM Hashtag Tracker — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime

@dataclass
class HashtagMention:
    hashtag: str
    content_id: str
    timestamp: str
    user_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class HashtagTracker:
    def __init__(self) -> None:
        self._mentions: List[HashtagMention] = []
        self._counts: Dict[str, int] = {}
        self._trending: Dict[str, List[tuple]] = {}

    def add_mention(self, mention: HashtagMention) -> None:
        self._mentions.append(mention)
        tag = mention.hashtag.lower()
        self._counts[tag] = self._counts.get(tag, 0) + 1
        if tag not in self._trending:
            self._trending[tag] = []
        self._trending[tag].append((mention.timestamp, mention.content_id))

    def extract_from_text(self, text: str, content_id: str, user_id: str, timestamp: str) -> List[str]:
        hashtags = re.findall(r'#(\w+)', text)
        for tag in hashtags:
            self.add_mention(HashtagMention(tag, content_id, timestamp, user_id))
        return hashtags

    def get_top_hashtags(self, n: int = 10) -> List[tuple]:
        sorted_tags = sorted(self._counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_tags[:n]

    def get_hashtag_history(self, hashtag: str) -> List[tuple]:
        return self._trending.get(hashtag.lower(), [])

    def get_related_hashtags(self, hashtag: str, min_cooccurrence: int = 1) -> Dict[str, int]:
        tag = hashtag.lower()
        content_with_tag = set(m.content_id for m in self._mentions if m.hashtag.lower() == tag)
        related = {}
        for m in self._mentions:
            if m.content_id in content_with_tag and m.hashtag.lower() != tag:
                related[m.hashtag.lower()] = related.get(m.hashtag.lower(), 0) + 1
        return {k: v for k, v in related.items() if v >= min_cooccurrence}

    def get_stats(self) -> Dict[str, Any]:
        return {"mentions": len(self._mentions), "unique_hashtags": len(self._counts), "total_counts": sum(self._counts.values())}

def run() -> None:
    print("Hashtag Tracker test")
    e = HashtagTracker()
    e.extract_from_text("Love #AI and #MachineLearning! #AI is the future.", "post_1", "u1", "2024-01-01T00:00:00")
    e.extract_from_text("#AI is changing #Tech industry. #MachineLearning too!", "post_2", "u2", "2024-01-01T00:00:00")
    e.extract_from_text("#Python is great for #AI and #DataScience", "post_3", "u3", "2024-01-01T00:00:00")
    print("  Top hashtags: " + str(e.get_top_hashtags(5)))
    print("  Related to AI: " + str(e.get_related_hashtags("AI", 1)))
    print("  Stats: " + str(e.get_stats()))
    print("Hashtag Tracker test complete.")

if __name__ == "__main__":
    run()
