
"""
browser_automation_agent_native.py
MAGNATRIX-OS — Browser Automation Agent

AI-powered browser automation agent that can navigate, extract,
interact, and reason about web pages. Integrates with browser
extension for visual feedback and control.

Pure Python standard library.
"""

import json
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
import urllib.request
import urllib.parse


class ActionType(Enum):
    NAVIGATE = auto()
    CLICK = auto()
    TYPE = auto()
    SCROLL = auto()
    EXTRACT = auto()
    WAIT = auto()
    SCREENSHOT = auto()
    BACK = auto()
    REFRESH = auto()


@dataclass
class BrowserAction:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class BrowserState:
    url: str = ""
    title: str = ""
    content: str = ""
    elements: List[Dict] = field(default_factory=list)
    timestamp: str = ""


class BrowserAutomationAgent:
    """AI-powered browser automation agent."""

    def __init__(self, user_agent: str = "MAGNATRIX-BrowserAgent/1.0"):
        self.user_agent = user_agent
        self.history: List[BrowserAction] = []
        self.current_state = BrowserState()
        self._http_headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "identity",
        }
        self.allowed_domains: List[str] = []
        self.blocked_domains: List[str] = ["localhost", "127.0.0.1", "0.0.0.0"]

    def _is_allowed(self, url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        if domain in self.blocked_domains:
            return False
        if self.allowed_domains and domain not in self.allowed_domains:
            return False
        return True

    def fetch(self, url: str) -> BrowserState:
        if not self._is_allowed(url):
            return BrowserState(url=url, title="[BLOCKED]", content="Domain not allowed.")
        try:
            req = urllib.request.Request(url, headers=self._http_headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                self.current_state = BrowserState(
                    url=url,
                    title=self._extract_title(content),
                    content=content[:50000],  # Limit content size
                    timestamp=datetime.now().isoformat(),
                )
                return self.current_state
        except Exception as e:
            return BrowserState(url=url, title="[ERROR]", content=str(e))

    def _extract_title(self, html: str) -> str:
        import re
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        return m.group(1).strip() if m else "Untitled"

    def _extract_links(self, html: str) -> List[Dict]:
        import re
        links = []
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html, re.IGNORECASE):
            links.append({"href": m.group(1), "text": m.group(2).strip()})
        return links[:50]

    def _extract_text(self, html: str) -> str:
        import re
        # Strip tags and get visible text
        text = re.sub(r'<script[^>]*>[^<]*</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<style[^>]*>[^<]*</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:10000]

    def navigate(self, url: str) -> Dict:
        action = BrowserAction(action="navigate", params={"url": url})
        self.history.append(action)
        state = self.fetch(url)
        return {
            "action": "navigate",
            "url": url,
            "title": state.title,
            "content_length": len(state.content),
        }

    def extract(self, selector: Optional[str] = None) -> Dict:
        action = BrowserAction(action="extract", params={"selector": selector})
        self.history.append(action)
        content = self.current_state.content
        if not content:
            return {"text": "", "links": [], "headings": []}
        text = self._extract_text(content)
        links = self._extract_links(content)
        return {
            "text": text[:5000],
            "links": links[:20],
            "headings": self._extract_headings(content),
        }

    def _extract_headings(self, html: str) -> List[str]:
        import re
        headings = []
        for m in re.finditer(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', html, re.IGNORECASE):
            headings.append(m.group(1).strip())
        return headings[:20]

    def search_content(self, query: str) -> List[Dict]:
        text = self._extract_text(self.current_state.content)
        results = []
        query_lower = query.lower()
        for i, line in enumerate(text.split(". ")):
            if query_lower in line.lower():
                results.append({"index": i, "text": line[:200]})
        return results[:10]

    def summarize_page(self) -> str:
        extract = self.extract()
        text = extract.get("text", "")
        headings = extract.get("headings", [])
        if not text:
            return "No content to summarize."
        summary = f"## {self.current_state.title}\n\n"
        if headings:
            summary += "**Key Topics:**\n" + "\n".join([f"- {h}" for h in headings[:5]]) + "\n\n"
        sentences = text.split(". ")
        summary += "**Summary:**\n" + ". ".join(sentences[:5]) + "...\n"
        return summary

    def execute_plan(self, plan: List[Dict]) -> List[Dict]:
        results = []
        for step in plan:
            action = step.get("action")
            if action == "navigate":
                result = self.navigate(step.get("url", ""))
            elif action == "extract":
                result = self.extract(step.get("selector"))
            elif action == "search":
                result = {"results": self.search_content(step.get("query", ""))}
            elif action == "summarize":
                result = {"summary": self.summarize_page()}
            elif action == "wait":
                time.sleep(step.get("seconds", 1))
                result = {"waited": step.get("seconds", 1)}
            else:
                result = {"error": f"Unknown action: {action}"}
            results.append(result)
        return results

    def to_dict(self) -> Dict:
        return {
            "current_url": self.current_state.url,
            "current_title": self.current_state.title,
            "history_count": len(self.history),
            "user_agent": self.user_agent,
        }


__all__ = ["BrowserAutomationAgent", "BrowserAction", "BrowserState", "ActionType"]
