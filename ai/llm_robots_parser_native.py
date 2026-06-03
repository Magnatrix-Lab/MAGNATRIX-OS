"""LLM Robots Parser — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class RuleType(Enum):
    ALLOW = auto()
    DISALLOW = auto()
    CRAWL_DELAY = auto()
    SITEMAP = auto()

@dataclass
class RobotRule:
    user_agent: str
    rule_type: RuleType
    value: str

class RobotsParser:
    def __init__(self) -> None:
        self._rules: List[RobotRule] = []
        self._sitemaps: List[str] = []
        self._crawl_delays: Dict[str, float] = {}

    def parse(self, content: str) -> None:
        lines = content.splitlines()
        current_user_agent = "*"
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key == "user-agent":
                current_user_agent = value
            elif key == "disallow":
                self._rules.append(RobotRule(current_user_agent, RuleType.DISALLOW, value))
            elif key == "allow":
                self._rules.append(RobotRule(current_user_agent, RuleType.ALLOW, value))
            elif key == "crawl-delay":
                self._crawl_delays[current_user_agent] = float(value)
            elif key == "sitemap":
                self._sitemaps.append(value)

    def can_fetch(self, user_agent: str, path: str) -> bool:
        rules = [r for r in self._rules if r.user_agent == user_agent or r.user_agent == "*"]
        if not rules:
            return True
        allowed = True
        for rule in rules:
            if rule.rule_type == RuleType.DISALLOW and path.startswith(rule.value):
                allowed = False
            if rule.rule_type == RuleType.ALLOW and path.startswith(rule.value):
                allowed = True
        return allowed

    def get_crawl_delay(self, user_agent: str) -> float:
        return self._crawl_delays.get(user_agent, self._crawl_delays.get("*", 0.0))

    def get_sitemaps(self) -> List[str]:
        return list(self._sitemaps)

    def get_stats(self) -> Dict[str, Any]:
        return {"rules": len(self._rules), "sitemaps": len(self._sitemaps), "delays": len(self._crawl_delays)}

def run() -> None:
    print("Robots Parser test")
    e = RobotsParser()
    robots = """User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /public/
Crawl-delay: 1.5
Sitemap: http://example.com/sitemap.xml

User-agent: Googlebot
Disallow: /nogoogle/
"""
    e.parse(robots)
    print("  Can fetch /public/page: " + str(e.can_fetch("*", "/public/page")))
    print("  Can fetch /admin/: " + str(e.can_fetch("*", "/admin/")))
    print("  Can fetch /nogoogle/: " + str(e.can_fetch("Googlebot", "/nogoogle/")))
    print("  Crawl delay: " + str(e.get_crawl_delay("*")))
    print("  Sitemaps: " + str(e.get_sitemaps()))
    print("  Stats: " + str(e.get_stats()))
    print("Robots Parser test complete.")

if __name__ == "__main__":
    run()
