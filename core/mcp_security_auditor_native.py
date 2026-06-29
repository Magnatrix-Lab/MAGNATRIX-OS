
"""
mcp_security_auditor_native.py
MAGNATRIX-OS — MCP Security Auditor

Security audit for MCP (Model Context Protocol) connections,
inspired by the Agentic AI & MCP Security phase in the pentesting roadmap.

Pure Python standard library.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class MCPSecurityLevel(Enum):
    SAFE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class MCPAuditResult:
    connection_id: str
    overall_level: str
    findings: List[Dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    score: float = 0.0


class MCPSecurityAuditor:
    """Audit MCP connections for security vulnerabilities."""

    def __init__(self):
        self.checks = [
            "authentication",
            "authorization",
            "input_validation",
            "output_sanitization",
            "rate_limiting",
            "tool_exposure",
            "prompt_injection_risk",
            "data_exfiltration",
            "session_management",
            "logging",
        ]
        self.history: List[Dict] = []

    def audit(self, connection_config: Dict) -> MCPAuditResult:
        findings = []
        recommendations = []
        score = 100.0

        # Check 1: Authentication
        if not connection_config.get("auth"):
            findings.append({
                "check": "authentication",
                "severity": "critical",
                "message": "No authentication configured for MCP connection",
            })
            score -= 25
            recommendations.append("Implement API key or OAuth authentication")
        elif connection_config.get("auth", {}).get("type") == "none":
            findings.append({
                "check": "authentication",
                "severity": "critical",
                "message": "Authentication explicitly disabled",
            })
            score -= 30

        # Check 2: Tool exposure
        exposed_tools = connection_config.get("exposed_tools", [])
        dangerous_tools = ["execute_command", "file_write", "network_request", "shell", "eval"]
        for tool in exposed_tools:
            if any(dt in tool.lower() for dt in dangerous_tools):
                findings.append({
                    "check": "tool_exposure",
                    "severity": "high",
                    "message": f"Dangerous tool exposed: {tool}",
                })
                score -= 15
                recommendations.append(f"Review necessity of exposing tool: {tool}")

        # Check 3: Input validation
        if not connection_config.get("input_validation", False):
            findings.append({
                "check": "input_validation",
                "severity": "high",
                "message": "Input validation not enforced",
            })
            score -= 10
            recommendations.append("Enable strict input validation on MCP endpoints")

        # Check 4: Rate limiting
        if not connection_config.get("rate_limit"):
            findings.append({
                "check": "rate_limiting",
                "severity": "medium",
                "message": "No rate limiting configured",
            })
            score -= 5
            recommendations.append("Implement rate limiting to prevent abuse")

        # Check 5: Prompt injection risk
        if connection_config.get("allow_user_prompts", True):
            findings.append({
                "check": "prompt_injection_risk",
                "severity": "medium",
                "message": "User prompts forwarded without sanitization",
            })
            score -= 5
            recommendations.append("Sanitize user prompts before forwarding to MCP tools")

        # Check 6: Data exfiltration
        if connection_config.get("allow_file_access", False):
            findings.append({
                "check": "data_exfiltration",
                "severity": "high",
                "message": "File access enabled — potential data exfiltration risk",
            })
            score -= 15
            recommendations.append("Restrict file access to specific directories")

        # Check 7: Logging
        if not connection_config.get("logging", False):
            findings.append({
                "check": "logging",
                "severity": "low",
                "message": "Logging disabled",
            })
            score -= 3
            recommendations.append("Enable audit logging for all MCP interactions")

        score = max(0.0, score)
        level = self._score_to_level(score)

        result = MCPAuditResult(
            connection_id=connection_config.get("id", "unknown"),
            overall_level=level,
            findings=findings,
            recommendations=recommendations,
            score=score,
        )
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "connection_id": result.connection_id,
            "score": score,
            "findings": len(findings),
        })
        return result

    def _score_to_level(self, score: float) -> str:
        if score >= 90:
            return "safe"
        elif score >= 70:
            return "low"
        elif score >= 50:
            return "medium"
        elif score >= 30:
            return "high"
        return "critical"

    def audit_multiple(self, configs: List[Dict]) -> List[MCPAuditResult]:
        return [self.audit(c) for c in configs]

    def get_risk_summary(self) -> Dict:
        if not self.history:
            return {}
        scores = [h["score"] for h in self.history]
        return {
            "total_audited": len(self.history),
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "critical_count": sum(1 for s in scores if s < 30),
        }

    def to_dict(self) -> Dict:
        return self.get_risk_summary()


__all__ = ["MCPSecurityAuditor", "MCPAuditResult", "MCPSecurityLevel"]
