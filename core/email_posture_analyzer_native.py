"""
email_posture_analyzer_native.py
MAGNATRIX-OS — Email Posture Analyzer

Inspired by Frogy2.0: Email security posture analysis (SPF, DMARC, DKIM, MX records). Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class EmailPosture:
    domain: str
    has_spf: bool
    has_dkim: bool
    has_dmarc: bool
    spf_policy: str
    dmarc_policy: str
    mx_records: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class EmailPostureAnalyzer:
    """Analyze email security posture for target domains."""

    def __init__(self, data_dir: str = "./email_posture"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.results: Dict[str, EmailPosture] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "posture.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for domain, pd in data.items():
                        self.results[domain] = EmailPosture(**pd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "posture.json", "w", encoding="utf-8") as f:
            json.dump({d: asdict(p) for d, p in self.results.items()}, f, indent=2)

    def analyze(self, domain: str) -> EmailPosture:
        """Simulate email posture analysis."""
        import random
        has_spf = random.random() > 0.2
        has_dkim = random.random() > 0.3
        has_dmarc = random.random() > 0.4
        spf = random.choice(["~all", "-all", "+all", "?all"]) if has_spf else "none"
        dmarc = random.choice(["p=none", "p=quarantine", "p=reject"]) if has_dmarc else "none"
        mx = [f"mail{i}.{domain}" for i in range(1, random.randint(1, 4))]
        risk = 0.0
        recs = []
        if not has_spf:
            risk += 2.5; recs.append("Add SPF record")
        if not has_dkim:
            risk += 2.5; recs.append("Add DKIM record")
        if not has_dmarc:
            risk += 2.5; recs.append("Add DMARC record")
        if "+all" in spf or "?all" in spf:
            risk += 1.5; recs.append("Harden SPF policy")
        if "p=none" in dmarc:
            risk += 1.0; recs.append("Harden DMARC policy to quarantine or reject")
        posture = EmailPosture(
            domain=domain, has_spf=has_spf, has_dkim=has_dkim, has_dmarc=has_dmarc,
            spf_policy=spf, dmarc_policy=dmarc, mx_records=mx,
            risk_score=round(min(risk, 10), 2), recommendations=recs,
        )
        self.results[domain] = posture
        self._save()
        return posture

    def get_weak_domains(self) -> List[EmailPosture]:
        return [p for p in self.results.values() if p.risk_score >= 5.0]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        weak = len(self.get_weak_domains())
        spf_pct = sum(1 for p in self.results.values() if p.has_spf) / max(1, total) * 100
        dmarc_pct = sum(1 for p in self.results.values() if p.has_dmarc) / max(1, total) * 100
        return {"domains": total, "weak": weak, "spf_pct": round(spf_pct, 1), "dmarc_pct": round(dmarc_pct, 1)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["EmailPostureAnalyzer", "EmailPosture"]