
"""
llm_security_framework_native.py
MAGNATRIX-OS — LLM Security Framework

Comprehensive security framework for LLM deployments.
Covers OWASP LLM Top 10, NIST AI RMF, and defense in depth.

Pure Python standard library.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class OWASPCategory(Enum):
    LLM01 = "Prompt Injection"
    LLM02 = "Insecure Output Handling"
    LLM03 = "Training Data Poisoning"
    LLM04 = "Model Denial of Service"
    LLM05 = "Supply Chain Vulnerabilities"
    LLM06 = "Sensitive Information Disclosure"
    LLM07 = "Insecure Plugin Design"
    LLM08 = "Excessive Agency"
    LLM09 = "Overreliance"
    LLM10 = "Model Theft"


@dataclass
class SecurityControl:
    control_id: str
    name: str
    category: str
    description: str
    implementation: str
    priority: str = "medium"
    status: str = "not_implemented"


@dataclass
class SecurityAssessment:
    overall_score: float
    category_scores: Dict[str, float]
    findings: List[Dict]
    recommendations: List[str]
    compliance_status: str


class LLMSecurityFramework:
    """Comprehensive LLM security framework and assessment."""

    def __init__(self):
        self.controls: Dict[str, SecurityControl] = {}
        self._init_controls()
        self.assessments: List[SecurityAssessment] = []

    def _init_controls(self) -> None:
        controls = [
            SecurityControl("LLM01-01", "Input Sanitization", "LLM01", "Sanitize all user inputs before processing", "Regex-based filtering + LLM guard", "high"),
            SecurityControl("LLM01-02", "Prompt Segregation", "LLM01", "Separate system and user prompt contexts", "Use distinct prompt templates with boundaries", "high"),
            SecurityControl("LLM02-01", "Output Encoding", "LLM02", "Encode LLM outputs before rendering", "HTML escape + markdown sanitization", "high"),
            SecurityControl("LLM02-02", "Content Moderation", "LLM02", "Filter harmful outputs", "Keyword + semantic content filter", "medium"),
            SecurityControl("LLM03-01", "Data Validation", "LLM03", "Validate training data integrity", "Checksum + source verification", "high"),
            SecurityControl("LLM04-01", "Rate Limiting", "LLM04", "Limit request rates per user/IP", "Token bucket algorithm", "high"),
            SecurityControl("LLM04-02", "Resource Quotas", "LLM04", "Limit compute resources per request", "Max tokens + timeout enforcement", "medium"),
            SecurityControl("LLM05-01", "Dependency Scanning", "LLM05", "Scan model and library dependencies", "SBOM + vulnerability database", "high"),
            SecurityControl("LLM06-01", "PII Detection", "LLM06", "Detect and redact PII in outputs", "Regex + NER-based PII scanner", "critical"),
            SecurityControl("LLM06-02", "Access Control", "LLM06", "Restrict access to sensitive data", "RBAC + need-to-know principle", "high"),
            SecurityControl("LLM07-01", "Plugin Validation", "LLM07", "Validate all plugin inputs/outputs", "Schema validation + sandboxing", "high"),
            SecurityControl("LLM07-02", "Plugin Isolation", "LLM07", "Run plugins in isolated environments", "Container + capability restrictions", "medium"),
            SecurityControl("LLM08-01", "Action Approval", "LLM08", "Require approval for impactful actions", "Human-in-the-loop for destructive ops", "high"),
            SecurityControl("LLM08-02", "Capability Limits", "LLM08", "Limit what actions LLM can trigger", "Whitelist-only action model", "high"),
            SecurityControl("LLM09-01", "Confidence Scoring", "LLM09", "Require confidence thresholds for critical outputs", "Enforce minimum confidence for decisions", "medium"),
            SecurityControl("LLM10-01", "Model Protection", "LLM10", "Protect model weights and architecture", "Encryption + access logging", "high"),
            SecurityControl("LLM10-02", "Watermarking", "LLM10", "Embed watermarks in model outputs", "Stegano + statistical watermarking", "medium"),
        ]
        for c in controls:
            self.controls[c.control_id] = c

    def assess(self, implemented_controls: List[str]) -> SecurityAssessment:
        """Assess security posture based on implemented controls."""
        category_scores: Dict[str, float] = {}
        category_totals: Dict[str, int] = {}
        findings = []
        recommendations = []

        for cat in OWASPCategory:
            cat_id = cat.name
            category_scores[cat_id] = 0.0
            category_totals[cat_id] = 0

        for ctrl_id, ctrl in self.controls.items():
            cat_id = ctrl.category
            category_totals[cat_id] = category_totals.get(cat_id, 0) + 1
            if ctrl_id in implemented_controls:
                ctrl.status = "implemented"
                category_scores[cat_id] = category_scores.get(cat_id, 0) + 1
            else:
                findings.append({
                    "control_id": ctrl_id,
                    "category": cat_id,
                    "name": ctrl.name,
                    "priority": ctrl.priority,
                    "message": f"Control not implemented: {ctrl.name}",
                })
                recommendations.append(f"Implement {ctrl.name} ({ctrl_id}) - Priority: {ctrl.priority}")

        # Calculate category scores
        for cat_id in category_scores:
            total = category_totals.get(cat_id, 1)
            category_scores[cat_id] = (category_scores[cat_id] / total) * 100

        overall = sum(category_scores.values()) / len(category_scores) if category_scores else 0.0

        compliance = "compliant" if overall >= 80 else "partial" if overall >= 50 else "non_compliant"

        assessment = SecurityAssessment(
            overall_score=overall,
            category_scores=category_scores,
            findings=findings,
            recommendations=recommendations,
            compliance_status=compliance,
        )
        self.assessments.append(assessment)
        return assessment

    def get_control(self, control_id: str) -> Optional[SecurityControl]:
        return self.controls.get(control_id)

    def get_controls_by_category(self, category: str) -> List[SecurityControl]:
        return [c for c in self.controls.values() if c.category == category]

    def get_implementation_guide(self, control_id: str) -> str:
        ctrl = self.controls.get(control_id)
        if ctrl:
            return f"""## {ctrl.name} ({control_id})
Category: {ctrl.category}
Priority: {ctrl.priority}

Description: {ctrl.description}
Implementation: {ctrl.implementation}

Status: {ctrl.status}"""
        return "Control not found"

    def to_dict(self) -> Dict:
        return {
            "total_controls": len(self.controls),
            "total_assessments": len(self.assessments),
            "latest_score": self.assessments[-1].overall_score if self.assessments else 0.0,
        }


__all__ = ["LLMSecurityFramework", "SecurityControl", "SecurityAssessment", "OWASPCategory"]
