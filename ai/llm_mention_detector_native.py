"""LLM Mention Detector — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime

@dataclass
class Mention:
    username: str
    content_id: str
    timestamp: str
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class MentionDetector:
    def __init__(self) -> None:
        self._mentions: List[Mention] = []
        self._user_mentions: Dict[str, List[Mention]] = {}

    def detect(self, text: str, content_id: str, timestamp: str) -> List[Mention]:
        found = re.findall(r'@(\w+)', text)
        mentions = []
        for username in found:
            m = Mention(username, content_id, timestamp, text)
            mentions.append(m)
            self._mentions.append(m)
            if username not in self._user_mentions:
                self._user_mentions[username] = []
            self._user_mentions[username].append(m)
        return mentions

    def get_mentions_for_user(self, username: str) -> List[Mention]:
        return self._user_mentions.get(username, [])

    def get_mention_count(self, username: str) -> int:
        return len(self._user_mentions.get(username, []))

    def get_top_mentioned(self, n: int = 5) -> List[tuple]:
        counts = [(user, len(mentions)) for user, mentions in self._user_mentions.items()]
        counts.sort(key=lambda x: x[1], reverse=True)
        return counts[:n]

    def get_stats(self) -> Dict[str, Any]:
        return {"total_mentions": len(self._mentions), "unique_users": len(self._user_mentions), "avg_mentions_per_user": len(self._mentions) / len(self._user_mentions) if self._user_mentions else 0}

def run() -> None:
    print("Mention Detector test")
    e = MentionDetector()
    e.detect("@alice and @bob are here", "post_1", "2024-01-01T00:00:00")
    e.detect("@alice check this out", "post_2", "2024-01-01T00:00:00")
    e.detect("@charlie @alice @alice", "post_3", "2024-01-01T00:00:00")
    print("  Alice mentions: " + str(e.get_mention_count("alice")))
    print("  Top mentioned: " + str(e.get_top_mentioned(3)))
    print("  Stats: " + str(e.get_stats()))
    print("Mention Detector test complete.")

if __name__ == "__main__":
    run()
