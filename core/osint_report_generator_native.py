"""OSINT Report Generator — Report compilation, risk scoring, timeline."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class OsintReport:
    report_id: str = ""
    title: str = ""
    target: str = ""
    created_at: float = 0.0
    sections: list[dict] = None
    risk_score: int = 0
    timeline: list[dict] = None
    findings: list[dict] = None

    def __post_init__(self):
        if self.sections is None:
            self.sections = []
        if self.timeline is None:
            self.timeline = []
        if self.findings is None:
            self.findings = []

class OsintReportGenerator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._reports: list[OsintReport] = []
        self._persist_path = self.root / "osint_reports.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._reports = [OsintReport(**r) for r in data.get("reports", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "reports": [r.__dict__ for r in self._reports]
        }, indent=2))

    def create_report(self, title: str, target: str) -> OsintReport:
        report = OsintReport(
            report_id=f"OSINT-{int(time.time())}",
            title=title,
            target=target,
            created_at=time.time()
        )
        self._reports.append(report)
        self._save()
        return report

    def add_section(self, report_id: str, section_name: str, data: dict) -> None:
        for report in self._reports:
            if report.report_id == report_id:
                report.sections.append({"name": section_name, "data": data, "added_at": time.time()})
                self._save()
                return

    def add_finding(self, report_id: str, severity: str, description: str, evidence: dict) -> None:
        for report in self._reports:
            if report.report_id == report_id:
                report.findings.append({"severity": severity, "description": description, "evidence": evidence, "timestamp": time.time()})
                self._save()
                return

    def calculate_risk(self, report_id: str) -> int:
        for report in self._reports:
            if report.report_id == report_id:
                score = 0
                for f in report.findings:
                    sev = f.get("severity", "low")
                    score += {"critical": 10, "high": 7, "medium": 4, "low": 1}.get(sev, 0)
                report.risk_score = min(score, 100)
                self._save()
                return report.risk_score
        return 0

    def build_timeline(self, report_id: str) -> list[dict]:
        for report in self._reports:
            if report.report_id == report_id:
                timeline = sorted(report.findings, key=lambda x: x.get("timestamp", 0))
                report.timeline = timeline
                self._save()
                return timeline
        return []

    def export_json(self, report_id: str) -> dict:
        for report in self._reports:
            if report.report_id == report_id:
                return report.__dict__
        return {}

    def to_dict(self) -> dict:
        return {"report_count": len(self._reports)}

    def get_stats(self) -> dict:
        return {"reports": len(self._reports), "avg_risk": sum(r.risk_score for r in self._reports) / len(self._reports) if self._reports else 0}

__all__ = ["OsintReportGenerator", "OsintReport"]
