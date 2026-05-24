#!/usr/bin/env python3
"""
MAGNATRIX-OS — Layer 13.5: Auto Repo Hunter / Discovery
Native Python, zero external dependencies.
Based on GitHub API + auto-discovery patterns — AMATI-PELAJARI-TIRU.
"""
from __future__ import annotations
import json, time, threading, hashlib, random, re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum


class RepoCategory(Enum):
    AI_AGENTIC = "ai_agentic"
    SECURITY = "security"
    QUANT_FINANCE = "quant_finance"
    DEVOPS_INFRA = "devops_infra"
    WEB_FRONTEND = "web_frontend"
    DATA_SCIENCE = "data_science"
    BLOCKCHAIN = "blockchain"
    GAME_DEV = "game_dev"
    UNKNOWN = "unknown"


@dataclass
class RepoInfo:
    owner: str
    name: str
    full_name: str
    url: str
    stars: int
    forks: int
    language: str
    last_activity: float
    license: str
    topics: List[str] = field(default_factory=list)
    readme_preview: str = ""
    score: float = 0.0
    category: RepoCategory = RepoCategory.UNKNOWN
    integration_plan: Dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"


class GitHubAPIStub:
    """GitHub REST API client stub with rate limit awareness."""

    def __init__(self, token: str = "", rate_limit: int = 60):
        self.token = token
        self.rate_limit = rate_limit
        self._requests = 0
        self._reset_time = time.time() + 3600
        self._lock = threading.Lock()

    def _check_rate(self) -> bool:
        with self._lock:
            if time.time() > self._reset_time:
                self._requests = 0
                self._reset_time = time.time() + 3600
            if self._requests >= self.rate_limit:
                return False
            self._requests += 1
            return True

    def search_repos(self, query: str, per_page: int = 30) -> List[RepoInfo]:
        if not self._check_rate():
            print("[GitHubAPI] Rate limit exceeded")
            return []
        # Generate mock results based on query
        results = []
        for i in range(min(per_page, 10)):
            repo = RepoInfo(
                owner=f"user_{random.randint(1, 1000)}",
                name=f"{query.replace(' ', '_')}_{i}",
                full_name="",
                url=f"https://github.com/user/repo_{i}",
                stars=random.randint(10, 50000),
                forks=random.randint(0, 5000),
                language=random.choice(["Python", "Rust", "Go", "TypeScript", "Java", "C++", ""]),
                last_activity=time.time() - random.randint(0, 7776000),
                license=random.choice(["MIT", "Apache-2.0", "GPL-3.0", "BSD", "proprietary", ""]),
                topics=[query] + [f"topic_{random.randint(1, 20)}" for _ in range(random.randint(0, 5))],
            )
            repo.full_name = f"{repo.owner}/{repo.name}"
            results.append(repo)
        return results

    def get_repo_metadata(self, owner: str, name: str) -> Optional[RepoInfo]:
        if not self._check_rate():
            return None
        return RepoInfo(
            owner=owner, name=name,
            full_name=f"{owner}/{name}",
            url=f"https://github.com/{owner}/{name}",
            stars=random.randint(100, 10000),
            forks=random.randint(10, 1000),
            language="Python",
            last_activity=time.time() - random.randint(0, 2592000),
            license="MIT",
        )

    def get_readme(self, owner: str, name: str) -> str:
        if not self._check_rate():
            return ""
        # Mock README
        return f"# {name}\n\nThis is a sample README for {owner}/{name}.\n\n## Features\n- Feature 1\n- Feature 2\n\n## Installation\n```bash\npip install {name}\n```"

    def list_releases(self, owner: str, name: str) -> List[Dict]:
        if not self._check_rate():
            return []
        return [{"tag": f"v{random.randint(1, 10)}.{random.randint(0, 9)}.{random.randint(0, 9)}", "date": time.time() - random.randint(0, 7776000)} for _ in range(random.randint(0, 5))]


class RepoScorer:
    """Score repo: stars (20%), activity (25%), quality (20%), relevance (20%), license (15%)."""

    def score(self, repo: RepoInfo, target_keywords: List[str] = None) -> float:
        # Stars score (logarithmic, max 20)
        star_score = min(20, 20 * math.log10(repo.stars + 1) / 5)

        # Activity score (max 25)
        days_since_activity = (time.time() - repo.last_activity) / 86400
        activity_score = max(0, 25 - days_since_activity / 7)

        # Quality score (max 20) — based on forks, language presence
        fork_score = min(20, 20 * math.log10(repo.forks + 1) / 4)
        quality_score = fork_score if repo.language else fork_score * 0.5

        # Relevance score (max 20) — keyword match
        relevance = 0
        if target_keywords:
            text = f"{repo.name} {repo.readme_preview} {' '.join(repo.topics)}".lower()
            matches = sum(1 for kw in target_keywords if kw.lower() in text)
            relevance = min(20, matches * 5)

        # License score (max 15)
        license_score = 15 if repo.license in ("MIT", "Apache-2.0", "BSD") else 5 if repo.license else 0

        total = star_score + activity_score + quality_score + relevance + license_score
        return round(total, 2)


class CategoryClassifier:
    """Classify repo into MAGNATRIX categories."""

    CATEGORY_KEYWORDS = {
        RepoCategory.AI_AGENTIC: ["agent", "ai", "llm", "gpt", "autonomous", "mcp", "rag", "langchain", "crewai"],
        RepoCategory.SECURITY: ["security", "pentest", "vulnerability", "scanner", "exploit", "c2", "redteam"],
        RepoCategory.QUANT_FINANCE: ["trading", "quant", "finance", "backtest", "strategy", "hft", "portfolio"],
        RepoCategory.DEVOPS_INFRA: ["kubernetes", "docker", "terraform", "ansible", "ci/cd", "monitoring"],
        RepoCategory.WEB_FRONTEND: ["react", "vue", "angular", "frontend", "ui", "component"],
        RepoCategory.DATA_SCIENCE: ["ml", "dataframe", "jupyter", "pandas", "numpy", "visualization"],
        RepoCategory.BLOCKCHAIN: ["blockchain", "crypto", "ethereum", "web3", "smart contract", "defi"],
        RepoCategory.GAME_DEV: ["game", "unity", "godot", "engine", "renderer", "physics"],
    }

    def classify(self, repo: RepoInfo) -> RepoCategory:
        text = f"{repo.name} {repo.readme_preview} {' '.join(repo.topics)} {repo.language or ''}".lower()
        scores = {}
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            scores[cat] = sum(2 if kw in text else 0 for kw in keywords)
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                return best
        return RepoCategory.UNKNOWN


class PatternExtractor:
    """Extract core pattern: language, entry points, key classes, architecture."""

    def extract(self, repo: RepoInfo, readme: str) -> Dict:
        patterns = {
            "language": repo.language,
            "has_cli": "cli" in readme.lower() or "command" in readme.lower(),
            "has_api": "api" in readme.lower() or "rest" in readme.lower(),
            "has_tests": "test" in readme.lower() or "pytest" in readme.lower(),
            "has_docker": "docker" in readme.lower() or "dockerfile" in readme.lower(),
            "architecture": self._detect_architecture(readme),
            "entry_points": self._detect_entry_points(readme),
        }
        return patterns

    def _detect_architecture(self, readme: str) -> str:
        if "microservice" in readme.lower():
            return "microservices"
        if "event-driven" in readme.lower() or "event sourcing" in readme.lower():
            return "event_driven"
        if "serverless" in readme.lower():
            return "serverless"
        if "monolith" in readme.lower():
            return "monolithic"
        if "layered" in readme.lower() or "layer" in readme.lower():
            return "layered"
        return "unknown"

    def _detect_entry_points(self, readme: str) -> List[str]:
        entries = []
        if "main.py" in readme.lower() or "__main__" in readme.lower():
            entries.append("main.py")
        if "app.py" in readme.lower():
            entries.append("app.py")
        if "setup.py" in readme.lower() or "pyproject.toml" in readme.lower():
            entries.append("package")
        return entries


class PriorityQueue:
    """Priority queue for repos, sort by score and category."""

    def __init__(self):
        self._queue: List[RepoInfo] = []
        self._lock = threading.Lock()

    def add(self, repo: RepoInfo):
        with self._lock:
            self._queue.append(repo)
            self._queue.sort(key=lambda r: r.score, reverse=True)

    def get_top(self, n: int = 10) -> List[RepoInfo]:
        with self._lock:
            return self._queue[:n]

    def get_by_category(self, category: RepoCategory, n: int = 10) -> List[RepoInfo]:
        with self._lock:
            filtered = [r for r in self._queue if r.category == category]
            return filtered[:n]

    def size(self) -> int:
        with self._lock:
            return len(self._queue)


class DependencyResolver:
    """Detect if repo is prerequisite for others."""

    def analyze(self, repos: List[RepoInfo]) -> Dict[str, List[str]]:
        # Stub: no real dependency analysis
        return {r.slug: [] for r in repos}


class AutoIntegratorStub:
    """Auto-generate integration plan."""

    LAYER_MAP = {
        RepoCategory.AI_AGENTIC: 6,
        RepoCategory.SECURITY: 9,
        RepoCategory.QUANT_FINANCE: 8,
        RepoCategory.DEVOPS_INFRA: 0,
        RepoCategory.DATA_SCIENCE: 5,
        RepoCategory.WEB_FRONTEND: 7,
        RepoCategory.BLOCKCHAIN: 8,
        RepoCategory.GAME_DEV: 12,
    }

    def plan(self, repo: RepoInfo, patterns: Dict) -> Dict:
        target_layer = self.LAYER_MAP.get(repo.category, 6)
        estimated_lines = random.randint(300, 1500)
        return {
            "target_layer": target_layer,
            "target_file": f"{repo.category.value}/{repo.name}_native.py",
            "estimated_lines": estimated_lines,
            "classes_needed": random.randint(5, 20),
            "bridge_required": True,
            "patterns_to_extract": list(patterns.keys()),
            "priority": "high" if repo.score > 60 else "medium" if repo.score > 30 else "low",
        }


class HunterScheduler:
    """Scheduled hunts: daily/weekly, incremental, target categories."""

    def __init__(self):
        self._schedules: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def schedule(self, name: str, interval_hours: float, target_categories: List[RepoCategory] = None):
        with self._lock:
            self._schedules[name] = {
                "interval": interval_hours * 3600,
                "target_categories": target_categories or list(RepoCategory),
                "last_run": 0,
            }

    def is_due(self, name: str) -> bool:
        with self._lock:
            s = self._schedules.get(name)
            if not s:
                return False
            return time.time() - s["last_run"] >= s["interval"]

    def mark_run(self, name: str):
        with self._lock:
            if name in self._schedules:
                self._schedules[name]["last_run"] = time.time()

    def get_schedules(self) -> Dict:
        with self._lock:
            return dict(self._schedules)


class HunterKernelBridge:
    """Bridge to event_bus and service_registry."""

    def __init__(self, event_bus=None, service_registry=None):
        self.event_bus = event_bus
        self.service_registry = service_registry

    def publish(self, event_type: str, data: Dict):
        if self.event_bus:
            try:
                self.event_bus.publish(f"repo_hunter.{event_type}", data)
            except Exception:
                pass

    def register(self):
        if self.service_registry:
            try:
                self.service_registry.register("repo_hunter", {"status": "ready"})
            except Exception:
                pass


class RepoHunter:
    """Main orchestrator — compose all, run hunt, score, classify, queue."""

    def __init__(self):
        self.api = GitHubAPIStub()
        self.scorer = RepoScorer()
        self.classifier = CategoryClassifier()
        self.extractor = PatternExtractor()
        self.queue = PriorityQueue()
        self.dependency = DependencyResolver()
        self.integrator = AutoIntegratorStub()
        self.scheduler = HunterScheduler()
        self.bridge = HunterKernelBridge()
        self._hunt_history: List[Dict] = []

    def boot(self):
        self.bridge.register()
        self.scheduler.schedule("daily_hunt", 24, [RepoCategory.AI_AGENTIC, RepoCategory.SECURITY, RepoCategory.QUANT_FINANCE])
        print("[RepoHunter] Booted")

    def hunt(self, query: str, per_page: int = 10, target_keywords: List[str] = None) -> List[RepoInfo]:
        print(f"\n[Hunt] Searching: '{query}'")
        repos = self.api.search_repos(query, per_page)

        for repo in repos:
            # Score
            repo.score = self.scorer.score(repo, target_keywords or [query])
            # Classify
            repo.category = self.classifier.classify(repo)
            # Extract patterns
            readme = self.api.get_readme(repo.owner, repo.name)
            repo.readme_preview = readme[:500]
            patterns = self.extractor.extract(repo, readme)
            # Generate plan
            repo.integration_plan = self.integrator.plan(repo, patterns)
            # Add to queue
            self.queue.add(repo)

        self._hunt_history.append({"query": query, "results": len(repos), "timestamp": time.time()})
        self.bridge.publish("hunt_complete", {"query": query, "found": len(repos)})

        return repos

    def get_top_repos(self, n: int = 5) -> List[RepoInfo]:
        return self.queue.get_top(n)

    def get_stats(self) -> Dict:
        return {
            "total_queued": self.queue.size(),
            "total_hunts": len(self._hunt_history),
            "by_category": {cat.value: len(self.queue.get_by_category(cat)) for cat in RepoCategory},
        }

    def shutdown(self):
        print("[RepoHunter] Shutdown")


def run_demo():
    print("=" * 60)
    print("MAGNATRIX-OS Repo Hunter Demo")
    print("=" * 60)

    hunter = RepoHunter()
    hunter.boot()

    # Hunt multiple categories
    queries = [
        "AI agent framework",
        "trading bot",
        "security scanner",
        "terminal multiplexer",
    ]

    for q in queries:
        repos = hunter.hunt(q, per_page=5, target_keywords=[q.split()[0]])
        print(f"  Found {len(repos)} repos")
        if repos:
            top = max(repos, key=lambda r: r.score)
            print(f"  Top: {top.slug} | Score: {top.score} | Category: {top.category.value}")

    # Show top 5 overall
    print("\n--- Top 5 Repos ---")
    for i, repo in enumerate(hunter.get_top_repos(5), 1):
        print(f"  {i}. {repo.slug} ({repo.stars}⭐) | Score: {repo.score} | {repo.category.value}")
        if repo.integration_plan:
            plan = repo.integration_plan
            print(f"     → Layer {plan['target_layer']} | File: {plan['target_file']} | Priority: {plan['priority']}")

    # Stats
    print("\n--- Stats ---")
    stats = hunter.get_stats()
    for k, v in stats.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                if vv > 0:
                    print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")

    hunter.shutdown()
    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
