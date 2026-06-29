"""
cve_tracker_native.py
MAGNATRIX-OS — CVE Tracker

Track CVE status, PoC availability, and remediation state. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class CVEEntry:
    cve_id: str
    description: str
    cvss_score: float
    severity: str
    status: str  # unreported, reported, patched, disputed
    affected_products: List[str] = field(default_factory=list)
    poc_available: bool = False
    poc_id: str = ""
    reported_at: str = ""
    patched_at: str = ""


class CVETracker:
    """Track CVE status, PoC availability, and remediation."""

    def __init__(self, cache_dir: str = "./cve_tracker"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cves: Dict[str, CVEEntry] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "cves.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid, cd in data.items():
                        self.cves[cid] = CVEEntry(**cd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "cves.json", "w", encoding="utf-8") as f:
            json.dump({cid: asdict(c) for cid, c in self.cves.items()}, f, indent=2)

    def register(self, cve_id: str, description: str, cvss_score: float, affected_products: List[str],
                 poc_available: bool = False, poc_id: str = "") -> CVEEntry:
        severity = "low"
        if cvss_score >= 9.0:
            severity = "critical"
        elif cvss_score >= 7.0:
            severity = "high"
        elif cvss_score >= 4.0:
            severity = "medium"
        entry = CVEEntry(
            cve_id=cve_id, description=description, cvss_score=cvss_score,
            severity=severity, status="unreported", affected_products=affected_products,
            poc_available=poc_available, poc_id=poc_id,
        )
        self.cves[cve_id] = entry
        self._save()
        return entry

    def report(self, cve_id: str) -> bool:
        cve = self.cves.get(cve_id)
        if cve:
            cve.status = "reported"
            cve.reported_at = datetime.now().isoformat()
            self._save()
            return True
        return False

    def patch(self, cve_id: str) -> bool:
        cve = self.cves.get(cve_id)
        if cve:
            cve.status = "patched"
            cve.patched_at = datetime.now().isoformat()
            self._save()
            return True
        return False

    def get_cve(self, cve_id: str) -> Optional[CVEEntry]:
        return self.cves.get(cve_id)

    def list_by_status(self, status: str) -> List[CVEEntry]:
        return [c for c in self.cves.values() if c.status == status]

    def list_with_poc(self) -> List[CVEEntry]:
        return [c for c in self.cves.values() if c.poc_available]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.cves)
        with_poc = sum(1 for c in self.cves.values() if c.poc_available)
        statuses = {}
        for c in self.cves.values():
            statuses[c.status] = statuses.get(c.status, 0) + 1
        return {"total": total, "with_poc": with_poc, "statuses": statuses}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CVETracker", "CVEEntry"]