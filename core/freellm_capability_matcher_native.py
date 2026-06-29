"""Free LLM Capability Matcher -- Match tasks to best free model."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class TaskRequirement:
    task_id: str = ""
    description: str = ""
    needs_tools: bool = False
    needs_vision: bool = False
    needs_streaming: bool = False
    min_context: int = 0
    max_latency_ms: int = 0
    preferred_providers: list[str] = None

    def __post_init__(self):
        if self.preferred_providers is None:
            self.preferred_providers = []

@dataclass
class MatchResult:
    model_id: str = ""
    score: float = 0.0
    reasons: list[str] = None

    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []

class FreellmCapabilityMatcher:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._matches: list[dict] = []
        self._persist_path = self.root / "freellm_matcher.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._matches = data.get("matches", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({"matches": self._matches}, indent=2))

    def match(self, task: TaskRequirement, models: list[dict]) -> list[MatchResult]:
        results = []
        for m in models:
            score = 0.0
            reasons = []

            if m.get("context_window", 0) >= task.min_context:
                score += 30
                reasons.append("Context sufficient: " + str(m.get("context_window")))
            else:
                score -= 50
                reasons.append("Context too small: " + str(m.get("context_window")))

            if task.needs_tools and m.get("supports_tools", False):
                score += 20
                reasons.append("Supports tools")
            elif task.needs_tools:
                score -= 20
                reasons.append("No tool support")

            if task.needs_vision and "image" in m.get("modalities", []):
                score += 20
                reasons.append("Supports vision")
            elif task.needs_vision:
                score -= 20
                reasons.append("No vision support")

            if task.needs_streaming and m.get("supports_streaming", False):
                score += 10
                reasons.append("Supports streaming")

            if m.get("free_tier", False):
                score += 20
                reasons.append("Free tier available")

            if m.get("provider", "") in task.preferred_providers:
                score += 10
                reasons.append("Preferred provider")

            results.append(MatchResult(model_id=m.get("model_id", ""), score=score, reasons=reasons))

        results.sort(key=lambda x: x.score, reverse=True)
        self._matches.append({"task": task.task_id, "top_model": results[0].model_id if results else None})
        self._save()
        return results

    def recommend(self, task: TaskRequirement, models: list[dict]) -> MatchResult | None:
        results = self.match(task, models)
        return results[0] if results else None

    def to_dict(self) -> dict:
        return {"match_count": len(self._matches)}

    def get_stats(self) -> dict:
        return {"matches": len(self._matches)}

__all__ = ["FreellmCapabilityMatcher", "TaskRequirement", "MatchResult"]
