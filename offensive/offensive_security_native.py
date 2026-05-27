"""
openhack_native_audit.py
==========================
MAGNATRIX Native Whitebox Security Audit Engine
Layer 9: Security / Layer 13: Offensive

Pola AMATI-PELAJARI-TIRU dari hadriansecurity/OpenHack:
- Amati:  12-expert OWASP/MITRE 2025 whitebox audit families,
          full lifecycle: init_run → recon → scenarios → backlog →
          expert proof → triage → findings
- Pelajari: Core pattern: (1) ExpertFamily = specialized auditor per category,
            (2) ReconScanner = automated attack surface mapping,
            (3) VulnerabilityChaining = exploit path analysis,
            (4) RiskScoring = CVSS + custom weights,
            (5) ReportGenerator = findings + remediation
- Tiru:   Native Python dengan asyncio, recursive audit DAG,
          MAGNATRIX-specific risk weights (swarm safety, knowledge integrity,
          resource access), mesh broadcast untuk critical findings
"""

import asyncio
import json
import time
import uuid
import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from collections import defaultdict


class RiskLevel(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFO = 1


class ExpertFamily(Enum):
    INJECTION = "injection"              # SQL, NoSQL, OS command, LDAP injection
    AUTH = "auth"                       # Broken authentication
    SENSITIVE_DATA = "sensitive_data"   # Exposed sensitive data
    XXE = "xxe"                         # XML external entities
    BROKEN_ACCESS = "broken_access"     # Broken access control
    SECURITY_MISCONFIG = "security_misconfig"  # Security misconfiguration
    XSS = "xss"                         # Cross-site scripting
    DESERIALIZATION = "deserialization" # Insecure deserialization
    COMPONENTS = "components"           # Vulnerable components
    LOGGING = "logging"                 # Insufficient logging
    SSRF = "ssrf"                       # Server-side request forgery
    MAGNATRIX_SPECIFIC = "magnatrix"    # MAGNATRIX-specific: mesh hijack, skill poisoning


@dataclass
class AttackSurface:
    """Discovered attack surface dari recon"""
    endpoints: List[Dict] = field(default_factory=list)
    parameters: List[Dict] = field(default_factory=list)
    headers: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    data_flows: List[Dict] = field(default_factory=list)
    trust_boundaries: List[Dict] = field(default_factory=list)


@dataclass
class Vulnerability:
    """Single vulnerability finding"""
    id: str = field(default_factory=lambda: f"VULN-{uuid.uuid4().hex[:8].upper()}")
    expert_family: str = ""
    title: str = ""
    description: str = ""
    affected_component: str = ""
    location: str = ""  # file:line atau endpoint
    cvss_score: float = 0.0
    cvss_vector: str = ""
    risk_level: RiskLevel = RiskLevel.INFO
    evidence: List[str] = field(default_factory=list)
    remediation: str = ""
    references: List[str] = field(default_factory=list)
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    # MAGNATRIX-specific
    swarm_impact: bool = False  # Apakah vulnerability bisa compromise swarm?
    knowledge_integrity_risk: bool = False
    mesh_exploitability: float = 0.0  # 0-1, seberapa mudah di-exploit via mesh
    # Metadata
    discovered_at: float = field(default_factory=time.time)
    verified: bool = False
    false_positive: bool = False
    chained_from: Optional[str] = None  # Vuln ID yang di-chain

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "risk_level": self.risk_level.name,
            "risk_score": self.calculate_risk_score()
        }

    def calculate_risk_score(self) -> float:
        """MAGNATRIX hybrid risk score"""
        base = self.cvss_score
        # Swarm impact multiplier
        if self.swarm_impact:
            base *= 1.5
        # Mesh exploitability boost
        base += self.mesh_exploitability * 3
        # Knowledge integrity boost
        if self.knowledge_integrity_risk:
            base *= 1.3
        return min(base, 10.0)


@dataclass
class AuditReport:
    """Final audit report"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    target: str = ""
    scope: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    attack_surface: Optional[AttackSurface] = None
    expert_coverage: Dict[str, bool] = field(default_factory=dict)
    # Metrics
    total_vulnerabilities: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    false_positive_count: int = 0
    # Remediation
    prioritized_fixes: List[Dict] = field(default_factory=list)
    estimated_remediation_effort_hours: float = 0.0
    # MAGNATRIX
    mesh_broadcast: bool = True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "target": self.target,
            "scope": self.scope,
            "duration_seconds": (self.end_time or time.time()) - self.start_time,
            "summary": {
                "total": len(self.vulnerabilities),
                "critical": sum(1 for v in self.vulnerabilities if v.risk_level == RiskLevel.CRITICAL),
                "high": sum(1 for v in self.vulnerabilities if v.risk_level == RiskLevel.HIGH),
                "medium": sum(1 for v in self.vulnerabilities if v.risk_level == RiskLevel.MEDIUM),
                "low": sum(1 for v in self.vulnerabilities if v.risk_level == RiskLevel.LOW),
                "info": sum(1 for v in self.vulnerabilities if v.risk_level == RiskLevel.INFO),
            },
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "prioritized_fixes": self.prioritized_fixes,
            "expert_coverage": self.expert_coverage
        }


class ReconScanner:
    """Automated attack surface mapping"""

    def __init__(self):
        self._patterns = {
            "endpoints": re.compile(r"(?:GET|POST|PUT|DELETE|PATCH)\s+[\"']?(/[^\"'\s]+)"),
            "api_keys": re.compile(r"(?:api[_-]?key|token|secret)\s*[:=]\s*[\"']?([a-zA-Z0-9_-]{16,})"),
            "urls": re.compile(r'https?://[^\s"'']+'),
            "dependencies": re.compile(r'(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)'),
        }

    async def scan(self, target: str, source_code: str = "",
                   config_files: List[str] = None) -> AttackSurface:
        """Scan target untuk attack surface"""
        surface = AttackSurface()

        # Parse endpoints dari source
        if source_code:
            endpoints = self._patterns["endpoints"].findall(source_code)
            for ep in set(endpoints):
                surface.endpoints.append({
                    "path": ep,
                    "methods": ["GET", "POST"],  # Would infer from context
                    "auth_required": "auth" in source_code.lower() or "jwt" in source_code.lower()
                })

            # Parse dependencies
            deps = self._patterns["dependencies"].findall(source_code)
            surface.dependencies = list(set(deps))

            # Parse data flows (simplified)
            if "input" in source_code or "request" in source_code:
                surface.data_flows.append({
                    "source": "user_input",
                    "sink": "database",
                    "sanitized": "sanitize" in source_code or "escape" in source_code
                })

        return surface


class ExpertAuditor:
    """Single expert family auditor"""

    def __init__(self, family: ExpertFamily):
        self.family = family
        self._patterns = self._load_patterns()

    def _load_patterns(self) -> List[Dict]:
        """Load detection patterns untuk expert family"""
        patterns = {
            ExpertFamily.INJECTION: [
                {"pattern": r'execute\s*\(.*\+', "title": "SQL Injection via concatenation", "cvss": 9.8},
                {"pattern": r'\.format\s*\(.*query', "title": "String formatting in query", "cvss": 8.5},
                {"pattern": r'f["'].*SELECT.*\{.*\}', "title": "f-string in SQL", "cvss": 9.1},
            ],
            ExpertFamily.AUTH: [
                {"pattern": r'password\s*=\s*["'][^"']+["']', "title": "Hardcoded password", "cvss": 7.5},
                {"pattern": r'jwt\.decode\(.*verify\s*=\s*False', "title": "JWT verification disabled", "cvss": 8.0},
                {"pattern": r'secret_key\s*=\s*["'][^"']+["']', "title": "Hardcoded secret", "cvss": 7.0},
            ],
            ExpertFamily.SENSITIVE_DATA: [
                {"pattern": r'print\s*\(.*password|log.*password', "title": "Sensitive data logged", "cvss": 6.5},
            ],
            ExpertFamily.XXE: [
                {"pattern": r'xml\.etree\.ElementTree\.parse', "title": "Potential XXE", "cvss": 7.8},
            ],
            ExpertFamily.BROKEN_ACCESS: [
                {"pattern": r'def\s+admin|role.*admin', "title": "Admin function without RBAC check", "cvss": 6.8},
            ],
            ExpertFamily.SECURITY_MISCONFIG: [
                {"pattern": r'debug\s*=\s*True', "title": "Debug mode enabled", "cvss": 5.3},
                {"pattern": r'CORS.*\*', "title": "Permissive CORS", "cvss": 5.0},
            ],
            ExpertFamily.XSS: [
                {"pattern": r'return\s+.*\+\s*request', "title": "Reflected XSS", "cvss": 6.1},
                {"pattern": r'innerHTML\s*=.*user', "title": "DOM-based XSS", "cvss": 6.1},
            ],
            ExpertFamily.DESERIALIZATION: [
                {"pattern": r'pickle\.loads|yaml\.load\s*\(', "title": "Unsafe deserialization", "cvss": 8.1},
                {"pattern": r'eval\s*\(|exec\s*\(', "title": "Dangerous eval/exec", "cvss": 9.3},
            ],
            ExpertFamily.COMPONENTS: [
                {"pattern": r'requests==|urllib3==', "title": "Potentially outdated HTTP library", "cvss": 5.5},
            ],
            ExpertFamily.LOGGING: [
                {"pattern": r'try:.*except.*pass', "title": "Silent exception handling", "cvss": 4.0},
            ],
            ExpertFamily.SSRF: [
                {"pattern": r'requests\.get\(.*url\s*=.*param', "title": "Potential SSRF", "cvss": 7.5},
            ],
            ExpertFamily.MAGNATRIX_SPECIFIC: [
                {"pattern": r'mesh\.broadcast.*HALT', "title": "Unauthorized HALT broadcast", "cvss": 9.5, "swarm_impact": True},
                {"pattern": r'skill_registry.*inject', "title": "Potential skill poisoning", "cvss": 9.0, "knowledge_integrity": True},
                {"pattern": r'agent.*credentials.*plaintext', "title": "Agent credentials exposed", "cvss": 8.5, "swarm_impact": True},
            ],
        }
        return patterns.get(self.family, [])

    async def audit(self, source_code: str, attack_surface: AttackSurface) -> List[Vulnerability]:
        """Execute expert audit"""
        findings = []

        for pattern_def in self._patterns:
            regex = re.compile(pattern_def["pattern"], re.IGNORECASE)
            matches = regex.finditer(source_code)

            for match in matches:
                vuln = Vulnerability(
                    expert_family=self.family.value,
                    title=pattern_def["title"],
                    description=f"Pattern detected at position {match.start()}",
                    location=f"line:{source_code[:match.start()].count(chr(10))+1}",
                    cvss_score=pattern_def.get("cvss", 5.0),
                    risk_level=self._cvss_to_level(pattern_def.get("cvss", 5.0)),
                    evidence=[match.group(0)],
                    remediation=self._get_remediation(pattern_def["title"]),
                    cwe_id=self._get_cwe(pattern_def["title"]),
                    owasp_category=self._get_owasp(pattern_def["title"]),
                    swarm_impact=pattern_def.get("swarm_impact", False),
                    knowledge_integrity_risk=pattern_def.get("knowledge_integrity", False),
                    mesh_exploitability=pattern_def.get("mesh_exploitability", 0.0)
                )
                findings.append(vuln)

        return findings

    def _cvss_to_level(self, score: float) -> RiskLevel:
        if score >= 9.0: return RiskLevel.CRITICAL
        if score >= 7.0: return RiskLevel.HIGH
        if score >= 4.0: return RiskLevel.MEDIUM
        if score >= 2.0: return RiskLevel.LOW
        return RiskLevel.INFO

    def _get_remediation(self, title: str) -> str:
        """Get remediation advice"""
        remediations = {
            "SQL Injection": "Use parameterized queries/prepared statements. Never concatenate user input into SQL.",
            "Hardcoded password": "Use environment variables or secrets manager. Rotate exposed credentials immediately.",
            "JWT verification disabled": "Always verify JWT signatures. Set verify=True and specify algorithms.",
            "Debug mode enabled": "Disable debug mode in production. Set DEBUG=False.",
            "Unsafe deserialization": "Use safe alternatives: json.loads, yaml.safe_load. Avoid pickle/eval on untrusted data.",
            "Unauthorized HALT broadcast": "Implement mesh message signing dan guardian validation sebelum HALT execution.",
            "Skill poisoning": "Validate skill sources via hash/signature. Use sandboxed skill execution environment.",
        }
        for key, value in remediations.items():
            if key in title:
                return value
        return "Review and apply security best practices for this vulnerability category."

    def _get_cwe(self, title: str) -> Optional[str]:
        cwe_map = {
            "SQL Injection": "CWE-89",
            "Hardcoded": "CWE-798",
            "JWT": "CWE-287",
            "XSS": "CWE-79",
            "deserialization": "CWE-502",
            "eval": "CWE-95",
            "SSRF": "CWE-918",
        }
        for key, cwe in cwe_map.items():
            if key in title:
                return cwe
        return None

    def _get_owasp(self, title: str) -> Optional[str]:
        owasp_map = {
            "Injection": "A03:2021 – Injection",
            "JWT": "A07:2021 – Identification and Authentication Failures",
            "XSS": "A03:2021 – Injection",
            "deserialization": "A08:2021 – Software and Data Integrity Failures",
            "CORS": "A05:2021 – Security Misconfiguration",
            "debug": "A05:2021 – Security Misconfiguration",
        }
        for key, owasp in owasp_map.items():
            if key in title:
                return owasp
        return None


class VulnerabilityChainer:
    """Exploit path chaining analysis"""

    def __init__(self):
        self._chain_rules = [
            # [trigger_vuln_family, -> enables_vuln_family]
            (ExpertFamily.INJECTION, ExpertFamily.BROKEN_ACCESS),
            (ExpertFamily.AUTH, ExpertFamily.SENSITIVE_DATA),
            (ExpertFamily.MAGNATRIX_SPECIFIC, ExpertFamily.MAGNATRIX_SPECIFIC),
        ]

    async def analyze_chains(self, vulnerabilities: List[Vulnerability]) -> List[Dict]:
        """Find vulnerability chains"""
        chains = []

        for i, vuln_a in enumerate(vulnerabilities):
            for vuln_b in vulnerabilities[i+1:]:
                if self._can_chain(vuln_a, vuln_b):
                    chains.append({
                        "chain_id": f"CHAIN-{i}-{i+1}",
                        "start": vuln_a.id,
                        "end": vuln_b.id,
                        "path": f"{vuln_a.expert_family} -> {vuln_b.expert_family}",
                        "combined_cvss": min(vuln_a.cvss_score + vuln_b.cvss_score * 0.5, 10.0),
                        "description": f"{vuln_a.title} can enable {vuln_b.title}"
                    })

        return chains

    def _can_chain(self, a: Vulnerability, b: Vulnerability) -> bool:
        """Check if two vulnerabilities can chain"""
        # Simple heuristic: if they're in same file and a is higher severity
        if a.location == b.location and a.cvss_score > b.cvss_score:
            return True
        # MAGNATRIX-specific chains
        if a.expert_family == ExpertFamily.AUTH.value and b.swarm_impact:
            return True
        return False


class AuditEngine:
    """
    Main audit engine - orchestrator untuk full lifecycle.
    Tiru OpenHack: init_run → recon → scenarios → backlog → expert proof → triage → findings
    """

    def __init__(self, mesh_broadcast: Optional[Callable] = None):
        self.mesh_broadcast = mesh_broadcast
        self.recon = ReconScanner()
        self.experts = {family: ExpertAuditor(family) for family in ExpertFamily}
        self.chainer = VulnerabilityChainer()
        self._audit_history: List[AuditReport] = []

    async def audit(self, target: str, source_code: str = "",
                    config_files: List[str] = None,
                    scope: List[str] = None) -> AuditReport:
        """Full audit lifecycle"""
        report = AuditReport(
            target=target,
            scope=scope or ["source_code", "configuration", "dependencies"]
        )

        # Phase 1: Reconnaissance
        attack_surface = await self.recon.scan(target, source_code, config_files)
        report.attack_surface = attack_surface

        # Phase 2: Expert Audit (parallel)
        expert_tasks = []
        for family, expert in self.experts.items():
            task = expert.audit(source_code, attack_surface)
            expert_tasks.append((family, task))

        all_findings = []
        for family, task in expert_tasks:
            findings = await task
            report.expert_coverage[family.value] = len(findings) > 0
            all_findings.extend(findings)

        # Phase 3: Vulnerability Chaining
        chains = await self.chainer.analyze_chains(all_findings)

        # Phase 4: Triage (deduplicate, score)
        report.vulnerabilities = self._triage(all_findings)

        # Add chain info
        for chain in chains:
            # Boost scores untuk chained vulns
            for vuln in report.vulnerabilities:
                if vuln.id in (chain["start"], chain["end"]):
                    vuln.cvss_score = min(vuln.cvss_score * 1.2, 10.0)
                    vuln.risk_level = self._cvss_to_level(vuln.cvss_score)

        # Phase 5: Prioritize fixes
        report.prioritized_fixes = self._prioritize_fixes(report.vulnerabilities)

        # Calculate metrics
        report.total_vulnerabilities = len(report.vulnerabilities)
        report.critical_count = sum(1 for v in report.vulnerabilities if v.risk_level == RiskLevel.CRITICAL)
        report.high_count = sum(1 for v in report.vulnerabilities if v.risk_level == RiskLevel.HIGH)
        report.medium_count = sum(1 for v in report.vulnerabilities if v.risk_level == RiskLevel.MEDIUM)
        report.low_count = sum(1 for v in report.vulnerabilities if v.risk_level == RiskLevel.LOW)
        report.end_time = time.time()

        # Mesh broadcast critical findings
        if self.mesh_broadcast and report.critical_count > 0:
            self.mesh_broadcast({
                "type": "SECURITY_AUDIT_CRITICAL",
                "channel": "security.audits",
                "audit_id": report.id,
                "target": target,
                "critical_count": report.critical_count,
                "high_count": report.high_count,
                "findings": [v.title for v in report.vulnerabilities if v.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH)]
            })

        self._audit_history.append(report)
        return report

    def _triage(self, findings: List[Vulnerability]) -> List[Vulnerability]:
        """Deduplicate dan sort findings"""
        # Deduplicate by title+location
        seen = set()
        unique = []
        for f in findings:
            key = f"{f.title}:{f.location}"
            if key not in seen:
                seen.add(key)
                unique.append(f)

        # Sort by risk score (descending)
        unique.sort(key=lambda v: v.calculate_risk_score(), reverse=True)
        return unique

    def _prioritize_fixes(self, vulnerabilities: List[Vulnerability]) -> List[Dict]:
        """Generate prioritized fix list"""
        fixes = []
        for v in vulnerabilities:
            if v.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                fixes.append({
                    "vuln_id": v.id,
                    "priority": "IMMEDIATE" if v.risk_level == RiskLevel.CRITICAL else "URGENT",
                    "title": v.title,
                    "effort_hours": 2 if v.risk_level == RiskLevel.CRITICAL else 4,
                    "remediation": v.remediation
                })
        return fixes

    def _cvss_to_level(self, score: float) -> RiskLevel:
        if score >= 9.0: return RiskLevel.CRITICAL
        if score >= 7.0: return RiskLevel.HIGH
        if score >= 4.0: return RiskLevel.MEDIUM
        if score >= 2.0: return RiskLevel.LOW
        return RiskLevel.INFO

    def get_history(self) -> List[Dict]:
        return [r.to_dict() for r in self._audit_history]

    def get_expert_summary(self) -> Dict:
        """Summary coverage per expert family"""
        return {
            family.value: {
                "total_audits": sum(1 for r in self._audit_history if r.expert_coverage.get(family.value, False)),
                "total_findings": sum(
                    len([v for v in r.vulnerabilities if v.expert_family == family.value])
                    for r in self._audit_history
                )
            }
            for family in ExpertFamily
        }


# ==================== DEMO ====================

if __name__ == "__main__":
    async def demo():
        engine = AuditEngine()

        # Demo code to audit
        demo_code = """
def login(request):
    username = request.GET.get('username')
    password = request.GET.get('password')
    query = "SELECT * FROM users WHERE username='" + username + "' AND password='" + password + "'"
    result = db.execute(query)
    jwt_token = jwt.decode(token, verify=False)
    DEBUG = True
    return result

def admin_panel(request):
    if request.user.is_admin:
        mesh.broadcast({"type": "HALT", "target": "all"})
    return render(request, "admin.html")
"""

        report = await engine.audit("demo_app", demo_code)
        print(json.dumps(report.to_dict(), indent=2, default=str))

    asyncio.run(demo())
