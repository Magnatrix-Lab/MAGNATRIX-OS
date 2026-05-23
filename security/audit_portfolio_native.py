#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — Audit Portfolio Native Integration
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari kadenzipfel/audit-portfolio

Pola yang ditiru:
• Audit report portfolio — structured collection of smart-contract audit findings
• DREAD-inspired risk matrix — Damage × Reproducibility × Exploitability × Affected × Discoverability
• Severity classification — Critical / High / Medium / Low / Informational / Gas
• 5-phase audit methodology: Recon → Static/Dynamic Analysis → Fuzzing → Risk Assessment → Reporting
• Finding template — title, description, severity, impact, proof-of-concept, recommendation, fix verification
• Portfolio dashboard — stats, timeline, client index, finding search engine
• Integration dengan SCVS (smart_contract_vulnerability_scanner.py) untuk cross-reference CWE/SWC

Layer: Security (9) — Audit Portfolio Manager
Versi: Phase 5 — Audit Portfolio Native Engine
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable


# ─────────────────────────────────────────────────────────────────────────────
# 0. UTILITAS DASAR
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _slugify(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


# ─────────────────────────────────────────────────────────────────────────────
# 1. SEVERITY & RISK MODEL — DREAD-Inspired Matrix
# ─────────────────────────────────────────────────────────────────────────────


class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"
    GAS = "Gas"

    @property
    def score_weight(self) -> float:
        return {
            Severity.CRITICAL: 10.0,
            Severity.HIGH: 7.5,
            Severity.MEDIUM: 5.0,
            Severity.LOW: 2.5,
            Severity.INFORMATIONAL: 1.0,
            Severity.GAS: 0.5,
        }[self]

    @property
    def color(self) -> str:
        return {
            Severity.CRITICAL: "#FF0000",
            Severity.HIGH: "#FF4500",
            Severity.MEDIUM: "#FFA500",
            Severity.LOW: "#FFD700",
            Severity.INFORMATIONAL: "#87CEEB",
            Severity.GAS: "#90EE90",
        }[self]


@dataclass
class DREADVector:
    """DREAD scoring: 0–10 untuk tiap dimensi."""
    damage: float = 0.0           # Potential financial/reputational damage
    reproducibility: float = 0.0  # How easily can it be reproduced
    exploitability: float = 0.0   # Ease of exploitation (skill, access needed)
    affected_users: float = 0.0   # Number/percentage of users affected
    discoverability: float = 0.0  # How easy to discover for attacker

    @property
    def score(self) -> float:
        return (self.damage + self.reproducibility + self.exploitability +
                self.affected_users + self.discoverability) / 5.0

    @property
    def severity(self) -> Severity:
        s = self.score
        if s >= 9.0:
            return Severity.CRITICAL
        if s >= 7.0:
            return Severity.HIGH
        if s >= 5.0:
            return Severity.MEDIUM
        if s >= 3.0:
            return Severity.LOW
        if s >= 1.0:
            return Severity.INFORMATIONAL
        return Severity.GAS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "damage": self.damage,
            "reproducibility": self.reproducibility,
            "exploitability": self.exploitability,
            "affected_users": self.affected_users,
            "discoverability": self.discoverability,
            "score": round(self.score, 2),
            "severity": self.severity.value,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. FINDING — Single Audit Finding
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Finding:
    """
    Satu temuan audit smart contract.
    Meniru format report dari kadenzipfel/audit-portfolio & industry standards (Code4rena, Sherlock).
    """
    id: str
    title: str
    severity: Severity
    dread: DREADVector
    category: str  # e.g. "Reentrancy", "Access Control", "Oracle Manipulation"
    description: str
    impact: str
    proof_of_concept: str
    recommendation: str
    code_reference: str = ""       # File:line atau contract:function
    swc_id: Optional[str] = None    # SWC-xxx cross-reference
    cwe_id: Optional[str] = None    # CWE-xxx cross-reference
    status: str = "Open"            # Open / Fixed / Verified / Acknowledged / Disputed
    fix_commit: Optional[str] = None
    fix_verification: Optional[str] = None
    reported_by: str = "MAGNATRIX-Auditor"
    reported_at: str = field(default_factory=_now_iso)
    tags: List[str] = field(default_factory=list)
    cvss_score: Optional[float] = None

    @property
    def risk_score(self) -> float:
        base = self.dread.score
        if self.cvss_score:
            return round((base + self.cvss_score) / 2, 2)
        return round(base, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity.value,
            "severity_color": self.severity.color,
            "risk_score": self.risk_score,
            "dread": self.dread.to_dict(),
            "category": self.category,
            "description": self.description,
            "impact": self.impact,
            "proof_of_concept": self.proof_of_concept,
            "recommendation": self.recommendation,
            "code_reference": self.code_reference,
            "swc_id": self.swc_id,
            "cwe_id": self.cwe_id,
            "status": self.status,
            "fix_commit": self.fix_commit,
            "fix_verification": self.fix_verification,
            "reported_by": self.reported_by,
            "reported_at": self.reported_at,
            "tags": self.tags,
            "cvss_score": self.cvss_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Finding:
        d = data.get("dread", {})
        dread = DREADVector(
            damage=d.get("damage", 0),
            reproducibility=d.get("reproducibility", 0),
            exploitability=d.get("exploitability", 0),
            affected_users=d.get("affected_users", 0),
            discoverability=d.get("discoverability", 0),
        )
        return cls(
            id=data["id"],
            title=data["title"],
            severity=Severity(data.get("severity", "Medium")),
            dread=dread,
            category=data.get("category", "General"),
            description=data.get("description", ""),
            impact=data.get("impact", ""),
            proof_of_concept=data.get("proof_of_concept", ""),
            recommendation=data.get("recommendation", ""),
            code_reference=data.get("code_reference", ""),
            swc_id=data.get("swc_id"),
            cwe_id=data.get("cwe_id"),
            status=data.get("status", "Open"),
            fix_commit=data.get("fix_commit"),
            fix_verification=data.get("fix_verification"),
            reported_by=data.get("reported_by", "MAGNATRIX-Auditor"),
            reported_at=data.get("reported_at", _now_iso()),
            tags=data.get("tags", []),
            cvss_score=data.get("cvss_score"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. AUDIT ENGAGEMENT — Full Audit Report Container
# ─────────────────────────────────────────────────────────────────────────────


class AuditPhase(str, Enum):
    RECON = "Recon & Scope Review"
    STATIC_DYNAMIC = "Static & Dynamic Analysis"
    FUZZING = "Fuzzing & Simulation"
    RISK_ASSESSMENT = "Risk Assessment"
    REPORTING = "Reporting & Verification"


@dataclass
class AuditEngagement:
    """
    Satu engagement audit lengkap — mirip satu folder di audit-portfolio repo.
    Contains: metadata, scope, methodology phases, findings list, executive summary.
    """
    engagement_id: str
    client_name: str
    project_name: str
    contract_address: Optional[str] = None
    audit_dates: Tuple[str, str] = ("", "")  # (start, end)
    auditors: List[str] = field(default_factory=list)
    scope: List[str] = field(default_factory=list)  # File paths / contract names
    commit_hash: Optional[str] = None
    methodology: List[AuditPhase] = field(default_factory=lambda: list(AuditPhase))
    findings: List[Finding] = field(default_factory=list)
    executive_summary: str = ""
    overall_risk_rating: Optional[Severity] = None
    disclaimer: str = (
        "This audit report is not financial advice and does not guarantee security. "
        "It represents a point-in-time assessment of the smart contracts as reviewed."
    )
    tools_used: List[str] = field(default_factory=lambda: [
        "Slither", "Mythril", "Solhint", "Echidna", "Foundry"
    ])
    tags: List[str] = field(default_factory=list)
    status: str = "Draft"  # Draft / Final / Published / Archived

    @property
    def finding_count_by_severity(self) -> Dict[str, int]:
        counts: Dict[str, int] = {s.value: 0 for s in Severity}
        for f in self.findings:
            counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
        return counts

    @property
    def total_risk_score(self) -> float:
        if not self.findings:
            return 0.0
        return round(sum(f.risk_score for f in self.findings) / len(self.findings), 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engagement_id": self.engagement_id,
            "client_name": self.client_name,
            "project_name": self.project_name,
            "contract_address": self.contract_address,
            "audit_dates": self.audit_dates,
            "auditors": self.auditors,
            "scope": self.scope,
            "commit_hash": self.commit_hash,
            "methodology": [m.value for m in self.methodology],
            "findings": [f.to_dict() for f in self.findings],
            "executive_summary": self.executive_summary,
            "overall_risk_rating": self.overall_risk_rating.value if self.overall_risk_rating else None,
            "disclaimer": self.disclaimer,
            "tools_used": self.tools_used,
            "finding_count_by_severity": self.finding_count_by_severity,
            "total_risk_score": self.total_risk_score,
            "tags": self.tags,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuditEngagement:
        return cls(
            engagement_id=data["engagement_id"],
            client_name=data["client_name"],
            project_name=data["project_name"],
            contract_address=data.get("contract_address"),
            audit_dates=tuple(data.get("audit_dates", ("", ""))),
            auditors=data.get("auditors", []),
            scope=data.get("scope", []),
            commit_hash=data.get("commit_hash"),
            methodology=[AuditPhase(m) for m in data.get("methodology", [])],
            findings=[Finding.from_dict(f) for f in data.get("findings", [])],
            executive_summary=data.get("executive_summary", ""),
            overall_risk_rating=Severity(data["overall_risk_rating"]) if data.get("overall_risk_rating") else None,
            disclaimer=data.get("disclaimer", cls.disclaimer),
            tools_used=data.get("tools_used", []),
            tags=data.get("tags", []),
            status=data.get("status", "Draft"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. AUDIT PORTFOLIO DATABASE — Persistent Storage Engine
# ─────────────────────────────────────────────────────────────────────────────


class AuditPortfolioDatabase:
    """
    Database lokal untuk menyimpan seluruh audit portfolio.
    JSON-based, content-addressable, dengan full-text search index.
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = (root or Path.home() / ".magnatrix" / "audit-portfolio").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.engagements_dir = self.root / "engagements"
        self.engagements_dir.mkdir(exist_ok=True)
        self.index_path = self.root / "portfolio-index.json"
        self._index: Dict[str, Dict[str, Any]] = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_index(self) -> None:
        self.index_path.write_text(json.dumps(self._index, indent=2, ensure_ascii=False), encoding="utf-8")

    def save_engagement(self, engagement: AuditEngagement) -> None:
        path = self.engagements_dir / f"{engagement.engagement_id}.json"
        path.write_text(json.dumps(engagement.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        self._index[engagement.engagement_id] = {
            "client_name": engagement.client_name,
            "project_name": engagement.project_name,
            "status": engagement.status,
            "total_findings": len(engagement.findings),
            "severity_counts": engagement.finding_count_by_severity,
            "total_risk_score": engagement.total_risk_score,
            "updated_at": _now_iso(),
            "tags": engagement.tags,
        }
        self._save_index()

    def load_engagement(self, engagement_id: str) -> Optional[AuditEngagement]:
        path = self.engagements_dir / f"{engagement_id}.json"
        if path.exists():
            return AuditEngagement.from_dict(json.loads(path.read_text(encoding="utf-8")))
        return None

    def list_engagements(self, status_filter: Optional[str] = None,
                         tag_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for eid, meta in self._index.items():
            if status_filter and meta.get("status") != status_filter:
                continue
            if tag_filter and tag_filter not in meta.get("tags", []):
                continue
            results.append({"engagement_id": eid, **meta})
        return sorted(results, key=lambda x: x.get("updated_at", ""), reverse=True)

    def delete_engagement(self, engagement_id: str) -> bool:
        path = self.engagements_dir / f"{engagement_id}.json"
        if path.exists():
            path.unlink()
            self._index.pop(engagement_id, None)
            self._save_index()
            return True
        return False

    def search_findings(self, query: str, severity_filter: Optional[Severity] = None,
                        category_filter: Optional[str] = None) -> List[Tuple[str, Finding]]:
        """Full-text search across all engagements' findings."""
        query_lower = query.lower()
        results: List[Tuple[str, Finding]] = []
        for eid in self._index:
            eng = self.load_engagement(eid)
            if not eng:
                continue
            for f in eng.findings:
                if severity_filter and f.severity != severity_filter:
                    continue
                if category_filter and f.category != category_filter:
                    continue
                text = f"{f.title} {f.description} {f.impact} {f.category} {' '.join(f.tags)}".lower()
                if query_lower in text:
                    results.append((eid, f))
        return results

    def get_stats(self) -> Dict[str, Any]:
        total_engagements = len(self._index)
        total_findings = sum(m.get("total_findings", 0) for m in self._index.values())
        severity_totals: Dict[str, int] = {s.value: 0 for s in Severity}
        for m in self._index.values():
            for s, c in m.get("severity_counts", {}).items():
                severity_totals[s] = severity_totals.get(s, 0) + c
        return {
            "total_engagements": total_engagements,
            "total_findings": total_findings,
            "severity_distribution": severity_totals,
            "storage_root": str(self.root),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 5. REPORT GENERATOR — Markdown & JSON Export
# ─────────────────────────────────────────────────────────────────────────────


class ReportGenerator:
    """
    Generate audit report dalam format Markdown (industry standard)
    dan JSON (machine-readable). Meniru style Code4rena / Sherlock / Spearbit.
    """

    def __init__(self, db: AuditPortfolioDatabase) -> None:
        self.db = db

    def generate_markdown(self, engagement_id: str) -> str:
        eng = self.db.load_engagement(engagement_id)
        if not eng:
            raise ValueError(f"Engagement {engagement_id} not found")

        lines: List[str] = []
        lines.append(f"# Audit Report: {eng.project_name}")
        lines.append("")
        lines.append(f"**Client:** {eng.client_name}")
        lines.append(f"**Engagement ID:** `{eng.engagement_id}`")
        if eng.contract_address:
            lines.append(f"**Contract Address:** `{eng.contract_address}`")
        lines.append(f"**Audit Period:** {eng.audit_dates[0]} – {eng.audit_dates[1]}")
        lines.append(f"**Auditors:** {', '.join(eng.auditors)}")
        if eng.commit_hash:
            lines.append(f"**Commit Hash:** `{eng.commit_hash}`")
        lines.append(f"**Status:** {eng.status}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(eng.executive_summary or "_No executive summary provided._")
        lines.append("")
        lines.append("### Severity Summary")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFORMATIONAL, Severity.GAS]:
            c = eng.finding_count_by_severity.get(sev.value, 0)
            lines.append(f"| {sev.value} | {c} |")
        lines.append("")
        lines.append(f"**Overall Risk Rating:** {eng.overall_risk_rating.value if eng.overall_risk_rating else 'N/A'}")
        lines.append(f"**Total Risk Score:** {eng.total_risk_score}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Scope")
        lines.append("")
        for item in eng.scope:
            lines.append(f"- `{item}`")
        lines.append("")
        lines.append("## Methodology")
        lines.append("")
        for phase in eng.methodology:
            lines.append(f"1. **{phase.value}**")
        lines.append("")
        lines.append(f"**Tools Used:** {', '.join(eng.tools_used)}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Findings")
        lines.append("")

        for f in sorted(eng.findings, key=lambda x: x.risk_score, reverse=True):
            lines.append(f"### [{f.severity.value}] {f.title}")
            lines.append("")
            lines.append(f"- **ID:** `{f.id}`")
            lines.append(f"- **Severity:** {f.severity.value} (Score: {f.risk_score})")
            lines.append(f"- **Category:** {f.category}")
            lines.append(f"- **Status:** {f.status}")
            if f.code_reference:
                lines.append(f"- **Location:** `{f.code_reference}`")
            if f.swc_id:
                lines.append(f"- **SWC:** [{f.swc_id}](https://swcregistry.io/docs/{f.swc_id})")
            if f.cwe_id:
                lines.append(f"- **CWE:** [{f.cwe_id}](https://cwe.mitre.org/data/definitions/{f.cwe_id.replace('CWE-', '')}.html)")
            lines.append("")
            lines.append("#### Description")
            lines.append(f.description)
            lines.append("")
            lines.append("#### Impact")
            lines.append(f.impact)
            lines.append("")
            lines.append("#### Proof of Concept")
            lines.append("```solidity")
            lines.append(f.proof_of_concept)
            lines.append("```")
            lines.append("")
            lines.append("#### Recommendation")
            lines.append(f.recommendation)
            lines.append("")
            if f.fix_commit:
                lines.append(f"**Fix Commit:** `{f.fix_commit}`")
            if f.fix_verification:
                lines.append(f"**Fix Verification:** {f.fix_verification}")
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("## Disclaimer")
        lines.append("")
        lines.append(eng.disclaimer)
        lines.append("")

        return "\n".join(lines)

    def generate_json(self, engagement_id: str) -> str:
        eng = self.db.load_engagement(engagement_id)
        if not eng:
            raise ValueError(f"Engagement {engagement_id} not found")
        return json.dumps(eng.to_dict(), indent=2, ensure_ascii=False)

    def export_markdown(self, engagement_id: str, output_path: Path) -> Path:
        md = self.generate_markdown(engagement_id)
        output_path.write_text(md, encoding="utf-8")
        return output_path


# ─────────────────────────────────────────────────────────────────────────────
# 6. AUDIT METHODOLOGY ENGINE — 5-Phase Workflow Runner
# ─────────────────────────────────────────────────────────────────────────────


class MethodologyEngine:
    """
    Runner untuk 5-phase audit methodology.
    Tiap phase bisa dipasang hooks (static analyzer, fuzzer, etc).
    """

    def __init__(self, engagement: AuditEngagement) -> None:
        self.engagement = engagement
        self._phase_hooks: Dict[AuditPhase, List[Callable[[AuditEngagement], List[Finding]]]] = {
            phase: [] for phase in AuditPhase
        }
        self._findings_buffer: List[Finding] = []

    def register_hook(self, phase: AuditPhase, fn: Callable[[AuditEngagement], List[Finding]]) -> None:
        self._phase_hooks[phase].append(fn)

    def run_phase(self, phase: AuditPhase) -> List[Finding]:
        findings: List[Finding] = []
        for hook in self._phase_hooks.get(phase, []):
            found = hook(self.engagement)
            findings.extend(found)
        self._findings_buffer.extend(findings)
        return findings

    def run_all(self) -> List[Finding]:
        for phase in self.engagement.methodology:
            self.run_phase(phase)
        self.engagement.findings = self._findings_buffer
        return self._findings_buffer

    def auto_classify(self) -> None:
        """Re-run DREAD scoring untuk semua findings dan update severity."""
        for f in self.engagement.findings:
            f.severity = f.dread.severity


# ─────────────────────────────────────────────────────────────────────────────
# 7. TEMPLATE LIBRARY — Pre-built Finding Templates
# ─────────────────────────────────────────────────────────────────────────────


class FindingTemplateLibrary:
    """
    Library template temuan audit umum — mirip checklist dari kadenzipfel resources.
    Auditor bisa instantiate dari template, lalu customize.
    """

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "reentrancy-eth": {
            "title": "Reentrancy in ETH transfer",
            "category": "Reentrancy",
            "description": "External call to untrusted contract before state update allows recursive re-entry.",
            "impact": "Attacker can drain contract ETH balance via recursive calls.",
            "proof_of_concept": "// Attacker calls withdraw() recursively before balance reset\nfunction withdraw() external {\n    uint256 amount = balances[msg.sender];\n    (bool ok, ) = msg.sender.call{value: amount}('');\n    require(ok);\n    balances[msg.sender] = 0;  // state updated AFTER external call\n}",
            "recommendation": "Follow checks-effects-interactions pattern. Update state before external call. Use ReentrancyGuard.",
            "dread": {"damage": 9.0, "reproducibility": 8.0, "exploitability": 7.0, "affected_users": 8.0, "discoverability": 6.0},
            "swc_id": "SWC-107",
            "cwe_id": "CWE-841",
            "tags": ["reentrancy", "eth-transfer", "state-update"],
        },
        "access-control-missing": {
            "title": "Missing access control on critical function",
            "category": "Access Control",
            "description": "Privileged function lacks modifier/authorization check, callable by any address.",
            "impact": "Unauthorized users can execute admin-only actions, including fund drainage or parameter manipulation.",
            "proof_of_concept": "function emergencyWithdraw() external {\n    // No onlyOwner or role check\n    payable(msg.sender).transfer(address(this).balance);\n}",
            "recommendation": "Add onlyOwner / OpenZeppelin AccessControl. Validate msg.sender against authorized roles.",
            "dread": {"damage": 9.0, "reproducibility": 9.0, "exploitability": 9.0, "affected_users": 9.0, "discoverability": 5.0},
            "swc_id": "SWC-106",
            "cwe_id": "CWE-284",
            "tags": ["access-control", "missing-check", "privilege-escalation"],
        },
        "oracle-manipulation": {
            "title": "Oracle price manipulation risk",
            "category": "Oracle Manipulation",
            "description": "Protocol uses spot price from single DEX as price oracle, susceptible to flash loan manipulation.",
            "impact": "Attacker can distort price feed to liquidate positions or borrow undercollateralized.",
            "proof_of_concept": "// Spot price from Uniswap V2\nuint256 price = pair.getReserves();\n// Manipulate with flash loan, then trigger liquidation",
            "recommendation": "Use Chainlink / TWAP / multi-source oracle. Add manipulation detection / circuit breaker.",
            "dread": {"damage": 8.0, "reproducibility": 6.0, "exploitability": 5.0, "affected_users": 7.0, "discoverability": 4.0},
            "swc_id": "SWC-116",
            "cwe_id": "CWE-20",
            "tags": ["oracle", "price-manipulation", "flash-loan"],
        },
        "integer-overflow": {
            "title": "Integer overflow in arithmetic operation",
            "category": "Arithmetic",
            "description": "Solidity <0.8.0 lacks built-in overflow checks. Manual check missing.",
            "impact": "Overflow can wrap around to small values, bypassing balance or limit checks.",
            "proof_of_concept": "uint8 x = 255;\nuint8 y = x + 1;  // y == 0 (overflow)",
            "recommendation": "Use Solidity >=0.8.0 or OpenZeppelin SafeMath for all arithmetic.",
            "dread": {"damage": 6.0, "reproducibility": 7.0, "exploitability": 6.0, "affected_users": 5.0, "discoverability": 5.0},
            "swc_id": "SWC-101",
            "cwe_id": "CWE-190",
            "tags": ["arithmetic", "overflow", "safemath"],
        },
        "unchecked-low-level-call": {
            "title": "Unchecked low-level call return value",
            "category": "Error Handling",
            "description": "Low-level call (call, delegatecall, staticcall) return value not checked.",
            "impact": "Failed call silently ignored, causing inconsistent state or lost funds.",
            "proof_of_concept": "address(target).call(abi.encodeWithSelector(SIG, amount));  // return value ignored",
            "recommendation": "Always check (bool success, ) = ... ; require(success, \"Call failed\");",
            "dread": {"damage": 7.0, "reproducibility": 8.0, "exploitability": 7.0, "affected_users": 6.0, "discoverability": 5.0},
            "swc_id": "SWC-104",
            "cwe_id": "CWE-252",
            "tags": ["low-level-call", "unchecked-return", "error-handling"],
        },
        "timestamp-dependency": {
            "title": "Dangerous use of block.timestamp",
            "category": "Time Manipulation",
            "description": "block.timestamp digunakan untuk randomness atau time-critical logic.",
            "impact": "Miner dapat manipulate timestamp ±15 detik untuk mempengaruhi outcome.",
            "proof_of_concept": "uint256 random = uint256(keccak256(abi.encodePacked(block.timestamp))) % 100;",
            "recommendation": "Gunakan VRF (Chainlink) untuk randomness. Untuk time logic, gunakan block.number dengan buffer.",
            "dread": {"damage": 5.0, "reproducibility": 4.0, "exploitability": 3.0, "affected_users": 4.0, "discoverability": 3.0},
            "swc_id": "SWC-116",
            "cwe_id": "CWE-20",
            "tags": ["timestamp", "miner-manipulation", "randomness"],
        },
        "gas-optimization-loop": {
            "title": "Gas optimization: storage variable in loop",
            "category": "Gas Optimization",
            "description": "Storage variable read/written dalam loop tanpa caching ke memory.",
            "impact": "Increased gas cost per iteration, potentially exceeding block gas limit.",
            "proof_of_concept": "for (uint i = 0; i < array.length; i++) {\n    total += array[i];  // array.length read from storage setiap iterasi\n}",
            "recommendation": "Cache storage variables ke memory sebelum loop. Use ++i instead of i++.",
            "dread": {"damage": 1.0, "reproducibility": 9.0, "exploitability": 1.0, "affected_users": 3.0, "discoverability": 7.0},
            "swc_id": None,
            "cwe_id": None,
            "tags": ["gas", "optimization", "storage", "loop"],
        },
    }

    @classmethod
    def list_templates(cls) -> List[str]:
        return list(cls.TEMPLATES.keys())

    @classmethod
    def instantiate(cls, template_key: str, engagement_id: str,
                    code_reference: str = "", custom_title: Optional[str] = None) -> Finding:
        t = cls.TEMPLATES.get(template_key)
        if not t:
            raise ValueError(f"Template '{template_key}' not found. Available: {cls.list_templates()}")
        dread_data = t.get("dread", {})
        dread = DREADVector(
            damage=dread_data.get("damage", 5),
            reproducibility=dread_data.get("reproducibility", 5),
            exploitability=dread_data.get("exploitability", 5),
            affected_users=dread_data.get("affected_users", 5),
            discoverability=dread_data.get("discoverability", 5),
        )
        finding_id = f"{engagement_id}-{_sha256(template_key + code_reference + str(time.time()))}"
        return Finding(
            id=finding_id,
            title=custom_title or t["title"],
            severity=dread.severity,
            dread=dread,
            category=t["category"],
            description=t["description"],
            impact=t["impact"],
            proof_of_concept=t["proof_of_concept"],
            recommendation=t["recommendation"],
            code_reference=code_reference,
            swc_id=t.get("swc_id"),
            cwe_id=t.get("cwe_id"),
            tags=list(t.get("tags", [])),
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8. PORTFOLIO DASHBOARD — Aggregated Analytics
# ─────────────────────────────────────────────────────────────────────────────


class PortfolioDashboard:
    """
    Dashboard analytics untuk seluruh audit portfolio.
    Menghasilkan summary stats, trend, dan leaderboard.
    """

    def __init__(self, db: AuditPortfolioDatabase) -> None:
        self.db = db

    def generate_summary(self) -> Dict[str, Any]:
        stats = self.db.get_stats()
        engagements = self.db.list_engagements()
        return {
            **stats,
            "engagements": engagements[:10],
            "generated_at": _now_iso(),
        }

    def severity_pie_data(self) -> List[Dict[str, Any]]:
        stats = self.db.get_stats()
        dist = stats.get("severity_distribution", {})
        return [{"severity": k, "count": v} for k, v in dist.items()]

    def auditor_leaderboard(self) -> Dict[str, Any]:
        """Aggregate findings by reported_by across all engagements."""
        leaderboard: Dict[str, Dict[str, Any]] = {}
        for eid in self.db._index:
            eng = self.db.load_engagement(eid)
            if not eng:
                continue
            for f in eng.findings:
                auditor = f.reported_by
                if auditor not in leaderboard:
                    leaderboard[auditor] = {"total": 0, "by_severity": {s.value: 0 for s in Severity}}
                leaderboard[auditor]["total"] += 1
                leaderboard[auditor]["by_severity"][f.severity.value] = \
                    leaderboard[auditor]["by_severity"].get(f.severity.value, 0) + 1
        return {
            "leaderboard": sorted(leaderboard.items(), key=lambda x: x[1]["total"], reverse=True),
            "generated_at": _now_iso(),
        }

    def category_distribution(self) -> Dict[str, int]:
        cats: Dict[str, int] = {}
        for eid in self.db._index:
            eng = self.db.load_engagement(eid)
            if not eng:
                continue
            for f in eng.findings:
                cats[f.category] = cats.get(f.category, 0) + 1
        return dict(sorted(cats.items(), key=lambda x: x[1], reverse=True))

    def trend_over_time(self) -> List[Dict[str, Any]]:
        """Count engagements and findings per month."""
        monthly: Dict[str, Dict[str, int]] = {}
        for eid, meta in self.db._index.items():
            ts = meta.get("updated_at", "")
            if len(ts) >= 7:
                month = ts[:7]  # YYYY-MM
                if month not in monthly:
                    monthly[month] = {"engagements": 0, "findings": 0}
                monthly[month]["engagements"] += 1
                monthly[month]["findings"] += meta.get("total_findings", 0)
        return [{"month": m, **v} for m, v in sorted(monthly.items())]


# ─────────────────────────────────────────────────────────────────────────────
# 9. SCVS INTEGRATION BRIDGE — Cross-reference dengan existing scanner
# ─────────────────────────────────────────────────────────────────────────────


class SCVSIntegrationBridge:
    """
    Bridge untuk mengintegrasikan Audit Portfolio dengan SCVS
    (smart_contract_vulnerability_scanner.py) yang sudah ada di MAGNATRIX.
    • Convert SCVS scan results → Audit Finding objects
    • Cross-reference SWC/CWE IDs antara portfolio dan vulnerability database
    • Batch import findings dari automated scanner ke engagement draft
    """

    def __init__(self, db: AuditPortfolioDatabase) -> None:
        self.db = db

    def finding_from_scvs_result(self, scvs_result: Dict[str, Any],
                                  engagement_id: str,
                                  code_reference: str = "") -> Finding:
        """Convert SCVS scanner output ke Finding object."""
        vuln_name = scvs_result.get("vulnerability", "Unknown")
        severity_val = scvs_result.get("severity", "Medium")
        # Map SCVS severity ke Severity enum
        sev_map = {
            "critical": Severity.CRITICAL, "high": Severity.HIGH,
            "medium": Severity.MEDIUM, "low": Severity.LOW,
            "info": Severity.INFORMATIONAL, "gas": Severity.GAS,
        }
        severity = sev_map.get(severity_val.lower(), Severity.MEDIUM)
        return Finding(
            id=f"{engagement_id}-SCVS-{_sha256(vuln_name + code_reference)}",
            title=f"[Auto] {vuln_name}",
            severity=severity,
            dread=DREADVector(
                damage=8.0 if severity in (Severity.CRITICAL, Severity.HIGH) else 5.0,
                reproducibility=7.0, exploitability=6.0,
                affected_users=5.0, discoverability=6.0,
            ),
            category=scvs_result.get("category", "Auto-Scan"),
            description=scvs_result.get("description", ""),
            impact=scvs_result.get("impact", "Automated scan detected this vulnerability."),
            proof_of_concept=scvs_result.get("proof_of_concept", scvs_result.get("code_snippet", "")),
            recommendation=scvs_result.get("recommendation", scvs_result.get("mitigation", "Review and fix.")),
            code_reference=code_reference,
            swc_id=scvs_result.get("swc_id"),
            cwe_id=scvs_result.get("cwe_id"),
            status="Open",
            reported_by="MAGNATRIX-SCVS",
            tags=scvs_result.get("tags", ["auto-scanned"]),
        )

    def import_scvs_batch(self, scvs_results: List[Dict[str, Any]],
                          engagement_id: str) -> List[Finding]:
        """Batch import multiple SCVS results ke satu engagement."""
        eng = self.db.load_engagement(engagement_id)
        if not eng:
            raise ValueError(f"Engagement {engagement_id} not found")
        findings: List[Finding] = []
        for result in scvs_results:
            f = self.finding_from_scvs_result(result, engagement_id)
            findings.append(f)
            eng.findings.append(f)
        self.db.save_engagement(eng)
        return findings

    def cross_reference_swc(self, swc_id: str) -> List[Tuple[str, Finding]]:
        """Cari semua findings di portfolio dengan SWC ID tertentu."""
        return self.db.search_findings(swc_id, category_filter=None)


# ─────────────────────────────────────────────────────────────────────────────
# 10. UNIFIED API — AuditPortfolioManager (Entry Point)
# ─────────────────────────────────────────────────────────────────────────────


class AuditPortfolioManager:
    """
    Unified manager untuk seluruh audit portfolio system.
    Entry point bagi MAGNATRIX agents & control plane.
    """

    def __init__(self, db_root: Optional[Path] = None) -> None:
        self.db = AuditPortfolioDatabase(db_root)
        self.reports = ReportGenerator(self.db)
        self.dashboard = PortfolioDashboard(self.db)
        self.templates = FindingTemplateLibrary()
        self.scvs_bridge = SCVSIntegrationBridge(self.db)

    # ── Engagement CRUD ─────────────────────────────────────────────────────

    def create_engagement(self, client: str, project: str, scope: List[str],
                          auditors: Optional[List[str]] = None,
                          contract_address: Optional[str] = None) -> AuditEngagement:
        eid = f"{_slugify(client)}-{_slugify(project)}-{_sha256(str(time.time()))[:8]}"
        eng = AuditEngagement(
            engagement_id=eid,
            client_name=client,
            project_name=project,
            contract_address=contract_address,
            audit_dates=(_now_iso()[:10], ""),
            auditors=auditors or ["MAGNATRIX-Auditor"],
            scope=scope,
        )
        self.db.save_engagement(eng)
        return eng

    def get_engagement(self, eid: str) -> Optional[AuditEngagement]:
        return self.db.load_engagement(eid)

    def add_finding(self, eid: str, finding: Finding) -> None:
        eng = self.db.load_engagement(eid)
        if not eng:
            raise ValueError(f"Engagement {eid} not found")
        eng.findings.append(finding)
        self.db.save_engagement(eng)

    def add_finding_from_template(self, eid: str, template_key: str,
                                   code_reference: str = "",
                                   custom_title: Optional[str] = None) -> Finding:
        f = self.templates.instantiate(template_key, eid, code_reference, custom_title)
        self.add_finding(eid, f)
        return f

    def update_finding_status(self, eid: str, finding_id: str, status: str,
                               fix_commit: Optional[str] = None,
                               fix_verification: Optional[str] = None) -> None:
        eng = self.db.load_engagement(eid)
        if not eng:
            raise ValueError(f"Engagement {eid} not found")
        for f in eng.findings:
            if f.id == finding_id:
                f.status = status
                if fix_commit:
                    f.fix_commit = fix_commit
                if fix_verification:
                    f.fix_verification = fix_verification
                break
        self.db.save_engagement(eng)

    def finalize_engagement(self, eid: str, executive_summary: str,
                            overall_risk: Severity) -> None:
        eng = self.db.load_engagement(eid)
        if not eng:
            raise ValueError(f"Engagement {eid} not found")
        eng.executive_summary = executive_summary
        eng.overall_risk_rating = overall_risk
        eng.status = "Final"
        eng.audit_dates = (eng.audit_dates[0], _now_iso()[:10])
        self.db.save_engagement(eng)

    # ── Reports ─────────────────────────────────────────────────────────────

    def export_markdown(self, eid: str, output_path: Optional[Path] = None) -> Path:
        if output_path is None:
            output_path = Path.cwd() / f"audit-report-{eid}.md"
        return self.reports.export_markdown(eid, output_path)

    def export_json(self, eid: str) -> str:
        return self.reports.generate_json(eid)

    # ── Search & Stats ──────────────────────────────────────────────────────

    def search(self, query: str, severity: Optional[str] = None,
               category: Optional[str] = None) -> List[Dict[str, Any]]:
        sev = Severity(severity) if severity else None
        raw = self.db.search_findings(query, sev, category)
        return [{"engagement_id": eid, **f.to_dict()} for eid, f in raw]

    def stats(self) -> Dict[str, Any]:
        return self.db.get_stats()

    def dashboard_summary(self) -> Dict[str, Any]:
        return self.dashboard.generate_summary()

    # ── SCVS Bridge ─────────────────────────────────────────────────────────

    def import_scvs_results(self, eid: str, scvs_results: List[Dict[str, Any]]) -> List[Finding]:
        return self.scvs_bridge.import_scvs_batch(scvs_results, eid)

    # ── Batch Demo / Seed ───────────────────────────────────────────────────

    def seed_demo_portfolio(self) -> List[str]:
        """Seed portfolio dengan demo engagements untuk testing."""
        ids: List[str] = []
        # Demo 1: DeFi Lending Protocol
        e1 = self.create_engagement(
            client="DemoDeFi Labs", project="LendCore Protocol",
            scope=["src/LendingPool.sol", "src/InterestRateModel.sol", "src/PriceOracle.sol"],
            auditors=["MAGNATRIX-Auditor-A", "MAGNATRIX-Auditor-B"],
            contract_address="0xDeFi...",
        )
        self.add_finding_from_template(e1.engagement_id, "reentrancy-eth", "LendingPool.sol:142")
        self.add_finding_from_template(e1.engagement_id, "oracle-manipulation", "PriceOracle.sol:88")
        self.add_finding_from_template(e1.engagement_id, "access-control-missing", "LendingPool.sol:55")
        ids.append(e1.engagement_id)

        # Demo 2: NFT Marketplace
        e2 = self.create_engagement(
            client="PixelMart", project="NFT Marketplace",
            scope=["src/Marketplace.sol", "src/RoyaltyEngine.sol"],
            auditors=["MAGNATRIX-Auditor-C"],
        )
        self.add_finding_from_template(e2.engagement_id, "integer-overflow", "Marketplace.sol:201")
        self.add_finding_from_template(e2.engagement_id, "unchecked-low-level-call", "RoyaltyEngine.sol:77")
        ids.append(e2.engagement_id)

        # Demo 3: DAO Governance
        e3 = self.create_engagement(
            client="GovDAO", project="Governance Token",
            scope=["src/Governance.sol", "src/Token.sol", "src/Timelock.sol"],
            auditors=["MAGNATRIX-Auditor-A"],
        )
        self.add_finding_from_template(e3.engagement_id, "timestamp-dependency", "Governance.sol:134")
        self.add_finding_from_template(e3.engagement_id, "gas-optimization-loop", "Token.sol:45")
        ids.append(e3.engagement_id)

        return ids


def main() -> None:
    """CLI demo untuk Audit Portfolio."""
    print("═══════════════════════════════════════════════════════════════")
    print("  MAGNATRIX-OS — Audit Portfolio Native Integration")
    print("  AMATI-PELAJARI-TIRU dari kadenzipfel/audit-portfolio")
    print("═══════════════════════════════════════════════════════════════")
    print()

    mgr = AuditPortfolioManager()
    ids = mgr.seed_demo_portfolio()

    print(f"Seeded {len(ids)} demo engagements:")
    for eid in ids:
        eng = mgr.get_engagement(eid)
        if eng:
            counts = eng.finding_count_by_severity
            print(f"  • {eng.project_name} ({eng.client_name})")
            print(f"    Findings: {len(eng.findings)} | Risk Score: {eng.total_risk_score}")
            print(f"    Severity: C:{counts['Critical']} H:{counts['High']} M:{counts['Medium']} L:{counts['Low']}")
    print()

    stats = mgr.stats()
    print(f"Portfolio Stats:")
    print(f"  Total Engagements: {stats['total_engagements']}")
    print(f"  Total Findings: {stats['total_findings']}")
    print(f"  Severity Distribution: {stats['severity_distribution']}")
    print()

    # Search demo
    results = mgr.search("reentrancy")
    print(f"Search 'reentrancy' → {len(results)} findings")
    for r in results:
        print(f"  • [{r['severity']}] {r['title']} in {r['engagement_id']}")
    print()

    # Export demo
    md_path = mgr.export_markdown(ids[0])
    print(f"Exported Markdown report: {md_path}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
