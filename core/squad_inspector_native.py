"""Squad Inspector — Quality validation, review, flagging."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class InspectionResult:
    result_id: str = ""
    target_agent_id: str = ""
    target_task: str = ""
    status: str = "pending"  # pending | pass | fail | flag
    issues: list[dict] = None
    score: int = 0
    inspected_at: float = 0.0
    inspector_id: str = ""

    def __post_init__(self):
        if self.issues is None:
            self.issues = []

class SquadInspector:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._results: list[InspectionResult] = []
        self._checklist: list[str] = [
            "code_compiles",
            "tests_pass",
            "no_security_issues",
            "documentation_complete",
            "performance_acceptable",
            "no_hardcoded_secrets",
        ]
        self._persist_path = self.root / "squad_inspections.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._results = [InspectionResult(**r) for r in data.get("results", [])]
            self._checklist = data.get("checklist", self._checklist)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "results": [r.__dict__ for r in self._results],
            "checklist": self._checklist
        }, indent=2))

    def inspect(self, result_id: str, target_agent: str, task: str, output: str, inspector_id: str) -> InspectionResult:
        import time
        issues = []
        score = 100

        # Simulated checks
        if "error" in output.lower() or "exception" in output.lower():
            issues.append({"check": "no_errors", "severity": "high", "detail": "Output contains errors"})
            score -= 30
        if "TODO" in output or "FIXME" in output:
            issues.append({"check": "completeness", "severity": "medium", "detail": "Contains TODO/FIXME markers"})
            score -= 15
        if "password" in output.lower() or "secret" in output.lower():
            issues.append({"check": "no_secrets", "severity": "critical", "detail": "Possible hardcoded secret"})
            score -= 50
        if len(output) < 50:
            issues.append({"check": "documentation", "severity": "low", "detail": "Output too short"})
            score -= 10

        status = "pass" if score >= 80 else "fail" if score < 50 else "flag"
        result = InspectionResult(
            result_id=result_id, target_agent_id=target_agent, target_task=task,
            status=status, issues=issues, score=max(0, score),
            inspected_at=time.time(), inspector_id=inspector_id
        )
        self._results.append(result)
        self._save()
        return result

    def approve(self, result_id: str) -> bool:
        for r in self._results:
            if r.result_id == result_id:
                r.status = "pass"
                r.score = 100
                self._save()
                return True
        return False

    def reject(self, result_id: str, reason: str) -> bool:
        for r in self._results:
            if r.result_id == result_id:
                r.status = "fail"
                r.issues.append({"check": "manual", "severity": "high", "detail": reason})
                self._save()
                return True
        return False

    def get_results(self, target_agent: str) -> list[InspectionResult]:
        return [r for r in self._results if r.target_agent_id == target_agent]

    def add_check(self, check_name: str) -> None:
        if check_name not in self._checklist:
            self._checklist.append(check_name)
            self._save()

    def to_dict(self) -> dict:
        return {"inspection_count": len(self._results), "checklist_items": len(self._checklist)}

    def get_stats(self) -> dict:
        by_status = {}
        for r in self._results:
            by_status[r.status] = by_status.get(r.status, 0) + 1
        avg_score = sum(r.score for r in self._results) / len(self._results) if self._results else 0
        return {"inspections": len(self._results), "by_status": by_status, "avg_score": round(avg_score, 1)}

__all__ = ["SquadInspector", "InspectionResult"]
