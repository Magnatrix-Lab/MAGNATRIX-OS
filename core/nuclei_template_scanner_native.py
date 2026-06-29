"""
nuclei_template_scanner_native.py
MAGNATRIX-OS — Nuclei Template Scanner

Execute Nuclei templates against targets and report findings. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ScanFinding:
    finding_id: str
    template_id: str
    target: str
    severity: str
    matched: bool
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class NucleiTemplateScanner:
    """Execute Nuclei templates against targets and report findings."""

    def __init__(self, cache_dir: str = "./nuclei_scanner"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.findings: Dict[str, List[ScanFinding]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "findings.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for fid, flist in data.items():
                        self.findings[fid] = [ScanFinding(**f) for f in flist]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "findings.json", "w", encoding="utf-8") as f:
            json.dump(
                {fid: [asdict(f) for f in flist] for fid, flist in self.findings.items()}, f, indent=2,
            )

    def scan(self, scan_id: str, template: Dict[str, Any], target: str, simulated_response: Dict[str, Any]) -> ScanFinding:
        """Execute a template against a simulated response."""
        from core.nuclei_matcher_engine_native import NucleiMatcherEngine
        from core.nuclei_extractor_engine_native import NucleiExtractorEngine

        matcher_engine = NucleiMatcherEngine()
        extractor_engine = NucleiExtractorEngine()

        matchers = template.get("matchers", [])
        condition = template.get("matchers-condition", "and")
        extractors = template.get("extractors", [])
        severity = template.get("info", {}).get("severity", "info")
        template_id = template.get("id", "unknown")

        matched = matcher_engine.match(f"{scan_id}_match", simulated_response, matchers, condition)
        extracted = {}
        if matched:
            ext_results = extractor_engine.extract(f"{scan_id}_extract", simulated_response, extractors)
            for er in ext_results:
                extracted[er.name] = er.extracted

        finding = ScanFinding(
            finding_id=f"{scan_id}_{template_id}", template_id=template_id,
            target=target, severity=severity, matched=matched, extracted_data=extracted,
        )
        self.findings.setdefault(scan_id, []).append(finding)
        self._save()
        return finding

    def batch_scan(self, scan_id: str, templates: List[Dict[str, Any]], targets: List[str]) -> Dict[str, Any]:
        """Scan multiple targets with multiple templates."""
        total = 0
        matched = 0
        for target in targets:
            for template in templates:
                # Simulate response based on target
                sim_response = {
                    "status_code": 200, "body": f"Response from {target}",
                    "headers": {"Content-Type": "text/html"}, "duration": 100,
                }
                result = self.scan(f"{scan_id}_{target}", template, target, sim_response)
                total += 1
                if result.matched:
                    matched += 1
        return {"scan_id": scan_id, "total": total, "matched": matched, "missed": total - matched}

    def get_findings(self, scan_id: str) -> List[ScanFinding]:
        return self.findings.get(scan_id, [])

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(f) for f in self.findings.values())
        matched = sum(1 for flist in self.findings.values() for f in flist if f.matched)
        return {"total_scans": len(self.findings), "total_findings": total, "matched": matched}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["NucleiTemplateScanner", "ScanFinding"]