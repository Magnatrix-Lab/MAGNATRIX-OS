"""
system_design_interviewer_native.py
MAGNATRIX-OS — System Design Interviewer

Inspired by donnemartin/system-design-primer interview questions:
Practice system design problems with structured analysis templates. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class DesignProblem:
    problem_id: str
    title: str
    description: str
    constraints: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    tradeoffs: List[str] = field(default_factory=list)
    difficulty: str = "medium"


@dataclass
class DesignSolution:
    problem_id: str
    approach: str
    architecture: List[str] = field(default_factory=list)
    bottlenecks: List[str] = field(default_factory=list)
    scaling_strategy: str = ""


class SystemDesignInterviewer:
    """Practice system design interview questions with structured analysis."""

    PROBLEM_LIBRARY = {
        "url_shortener": DesignProblem(
            problem_id="url_shortener", title="URL Shortener",
            description="Design a service like TinyURL or bit.ly that takes a long URL and returns a short alias.",
            constraints=["100M new URLs per day", "10B read requests per day", "Short URL must be unique"],
            requirements=["Generate short unique URL", "Redirect to original URL", "Analytics tracking"],
            components=["API Gateway", "Application Server", "Database", "Cache", "Analytics Pipeline"],
            tradeoffs=["Base62 encoding vs hash-based", "Read-heavy vs write-heavy"],
            difficulty="medium",
        ),
        "twitter": DesignProblem(
            problem_id="twitter", title="Twitter News Feed",
            description="Design a Twitter-like social network news feed system.",
            constraints=["300M daily active users", "1M tweets per minute", "Feed must be near real-time"],
            requirements=["Post tweet", "Generate timeline/feed", "Follow/unfollow users", "Search"],
            components=["Web Server", "Application Server", "Graph Database", "Timeline Service", "Search Index"],
            tradeoffs=["Fan-out on write vs fan-out on read", "Push vs pull model"],
            difficulty="hard",
        ),
        "youtube": DesignProblem(
            problem_id="youtube", title="YouTube Video Streaming",
            description="Design a video streaming service like YouTube.",
            constraints=["2B users", "500 hours of video uploaded per minute", "Global distribution"],
            requirements=["Upload video", "Stream video", "Search", "Recommendations"],
            components=["Upload Service", "Transcoder", "CDN", "Video Storage", "Recommendation Engine"],
            tradeoffs=["Storage vs compute", "Real-time vs batch processing for recommendations"],
            difficulty="hard",
        ),
        "chat_system": DesignProblem(
            problem_id="chat_system", title="Chat System",
            description="Design a real-time chat system like WhatsApp or Messenger.",
            constraints=["1B daily active users", "100B messages per day", "Message delivery within 200ms"],
            requirements=["1:1 chat", "Group chat", "Online status", "Message delivery receipts"],
            components=["WebSocket Server", "Message Queue", "Database", "Presence Service", "Push Notification"],
            tradeoffs=["WebSocket vs long polling", "Message storage vs ephemeral"],
            difficulty="medium",
        ),
        "web_crawler": DesignProblem(
            problem_id="web_crawler", title="Web Crawler",
            description="Design a web crawler that indexes the entire web.",
            constraints=["Billions of pages", "Respect robots.txt", "Deduplicate content"],
            requirements=["Crawl web pages", "Extract URLs", "Store content", "Deduplicate"],
            components=["URL Frontier", "Downloader", "Parser", "Deduplication Service", "Storage"],
            tradeoffs=["Breadth-first vs depth-first", "Politeness vs speed"],
            difficulty="medium",
        ),
    }

    def __init__(self, data_dir: str = "./system_design"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.solutions: Dict[str, DesignSolution] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "solutions.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, sd in data.items():
                        self.solutions[pid] = DesignSolution(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "solutions.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.solutions.items()}, f, indent=2)

    def get_problem(self, problem_id: str) -> Optional[DesignProblem]:
        return self.PROBLEM_LIBRARY.get(problem_id)

    def list_problems(self) -> List[str]:
        return list(self.PROBLEM_LIBRARY.keys())

    def submit_solution(self, problem_id: str, approach: str, architecture: List[str],
                        bottlenecks: List[str], scaling_strategy: str) -> DesignSolution:
        sol = DesignSolution(
            problem_id=problem_id, approach=approach, architecture=architecture,
            bottlenecks=bottlenecks, scaling_strategy=scaling_strategy,
        )
        self.solutions[problem_id] = sol
        self._save()
        return sol

    def evaluate(self, problem_id: str) -> Dict[str, Any]:
        problem = self.PROBLEM_LIBRARY.get(problem_id)
        solution = self.solutions.get(problem_id)
        if not problem or not solution:
            return {"error": "Problem or solution not found"}
        coverage = 0
        for comp in problem.components:
            if any(comp.lower() in arch.lower() for arch in solution.architecture):
                coverage += 1
        coverage_pct = round(coverage / max(1, len(problem.components)) * 100, 1)
        return {
            "problem": problem_id, "coverage_pct": coverage_pct,
            "components_covered": coverage, "total_components": len(problem.components),
            "bottlenecks_addressed": len(solution.bottlenecks),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"problems_available": len(self.PROBLEM_LIBRARY), "solutions_submitted": len(self.solutions)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SystemDesignInterviewer", "DesignProblem", "DesignSolution"]