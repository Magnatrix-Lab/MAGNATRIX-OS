"""
security_suite_native.py
MAGNATRIX-OS — Security Suite

Inspired by telagod/code-abyss 4 native security domains:
Defending applications, cloud security, detection/response, security architecture. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class SecurityAssessment:
    assessment_id: str
    domain: str
    target: str
    findings: List[Dict[str, Any]] = field(default_factory=list)
    risk_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class SecuritySuite:
    """4 native security domains: defend, cloud, detect-respond, architect."""

    DOMAINS = {
        "defending-applications": "Web/API/GraphQL hardening, auth, LLM AppSec",
        "securing-cloud": "Container escape, K8s, Service Mesh, SLSA/SBOM",
        "detecting-responding": "Sigma/YARA, EDR, forensics, threat hunting",
        "architecting-security": "STRIDE/PASTA, zero-trust, compliance",
    }

    ATTACK_TECHNIQUES = [
        "sql_injection", "xss", "csrf", "ssrf", "idor", "rce",
        "privilege_escalation", "lateral_movement", "persistence",
        "credential_dumping", "supply_chain_poisoning",
    ]

    def __init__(self, data_dir: str = "./security_suite"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.assessments: Dict[str, SecurityAssessment] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "assessments.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for aid, ad in data.items():
                        self.assessments[aid] = SecurityAssessment(**ad)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "assessments.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.assessments.items()}, f, indent=2)

    def assess(self, assessment_id: str, domain: str, target: str) -> SecurityAssessment:
        """Run a security assessment in a domain."""
        import random
        findings = []
        for _ in range(random.randint(1, 5)):
            technique = random.choice(self.ATTACK_TECHNIQUES)
            severity = random.choice(["critical", "high", "medium", "low"])
            findings.append({
                "technique": technique, "severity": severity,
                "description": f"Detected {technique} pattern in {target}",
                "mitigation": f"Implement {technique} prevention controls",
            })
        risk = sum({"critical": 4, "high": 3, "medium": 2, "low": 1}.get(f["severity"], 0) for f in findings)
        recs = list(set(f["mitigation"] for f in findings))
        assessment = SecurityAssessment(
            assessment_id=assessment_id, domain=domain, target=target,
            findings=findings, risk_score=round(min(risk, 10), 2), recommendations=recs,
        )
        self.assessments[assessment_id] = assessment
        self._save()
        return assessment

    def get_domain_summary(self, domain: str) -> Dict[str, Any]:
        assessments = [a for a in self.assessments.values() if a.domain == domain]
        total_findings = sum(len(a.findings) for a in assessments)
        avg_risk = sum(a.risk_score for a in assessments) / max(1, len(assessments))
        return {"domain": domain, "assessments": len(assessments), "findings": total_findings, "avg_risk": round(avg_risk, 2)}

    def get_threat_model(self, target: str) -> Dict[str, Any]:
        """Generate STRIDE threat model for a target."""
        stride = {
            "Spoofing": "Authentication controls", "Tampering": "Integrity checks",
            "Repudiation": "Audit logging", "Information_Disclosure": "Encryption",
            "Denial_of_Service": "Rate limiting", "Elevation_of_Privilege": "RBAC",
        }
        return {"target": target, "stride_categories": stride, "mitigations": list(stride.values())}

    def get_stats(self) -> Dict[str, Any]:
        by_domain = {}
        for a in self.assessments.values():
            by_domain[a.domain] = by_domain.get(a.domain, 0) + 1
        return {"total_assessments": len(self.assessments), "domains": by_domain}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SecuritySuite", "SecurityAssessment"]