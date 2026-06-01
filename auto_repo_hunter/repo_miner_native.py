"""auto_repo_hunter/repo_miner_native.py — Repo mining engine"""
from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional

class RepoMiner:
    """Mine GitHub repositories for patterns and analysis."""

    def __init__(self):
        self.repos: List[Dict[str, Any]] = []

    def analyze_repo(self, url: str, stars: int = 0, forks: int = 0, language: str = "") -> Dict[str, Any]:
        """Analyze a repository."""
        return {
            "url": url,
            "stars": stars,
            "forks": forks,
            "language": language,
            "score": stars * 2 + forks,
            "trending": stars > 100 and forks > 20,
        }

    def extract_patterns(self, code: str) -> List[str]:
        """Extract common patterns from code."""
        patterns = []
        if "class " in code:
            patterns.append("oop")
        if "def " in code:
            patterns.append("functions")
        if "import " in code:
            patterns.append("imports")
        if "async " in code:
            patterns.append("async")
        if "threading" in code:
            patterns.append("threading")
        return patterns

    def categorize(self, repo: Dict[str, Any]) -> str:
        if repo.get("language") == "Python":
            return "python"
        elif repo.get("language") == "JavaScript":
            return "javascript"
        elif repo.get("language") == "Go":
            return "golang"
        return "other"

    def search(self, query: str, repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [r for r in repos if query.lower() in r.get("url", "").lower()]

if __name__ == "__main__":
    print("RepoMiner self-test")
    rm = RepoMiner()
    repo = rm.analyze_repo("https://github.com/test/repo", 150, 30, "Python")
    assert repo["trending"]
    print("All tests pass")
