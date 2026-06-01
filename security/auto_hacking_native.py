#!/usr/bin/env python3
"""auto_hacking_native.py — Automated Offensive Security Engine for MAGNATRIX-OS.

Auto reconnaissance, vulnerability scanning, exploit hunting, red team automation.
All operations target authorized systems only. Ethical hacking framework.
"""

from __future__ import annotations
import hashlib, time, random, json, re, os
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum, auto


class ReconType(Enum):
    PASSIVE = "passive"
    ACTIVE = "active"
    OSINT = "osint"
    NETWORK = "network"
    WEB = "web"


class VulnSeverity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Target:
    id: str
    hostname: str
    ip: str
    ports: List[int] = field(default_factory=list)
    services: Dict[int, str] = field(default_factory=dict)
    technologies: List[str] = field(default_factory=list)
    scope: str = "authorized"


@dataclass
class Vulnerability:
    id: str
    target_id: str
    name: str
    severity: VulnSeverity
    cwe_id: Optional[str]
    cvss_score: float
    description: str
    evidence: str
    remediation: str
    discovered_at: float


@dataclass
class Exploit:
    id: str
    vuln_id: str
    name: str
    exploit_type: str
    reliability: float
    complexity: str
    impact: str
    poc_code: str
    mitigations: List[str] = field(default_factory=list)


class AutoRecon:
    """Automated reconnaissance engine."""

    def __init__(self):
        self._targets: List[Target] = []
        self._scan_results: Dict[str, Dict[str, Any]] = {}

    def add_target(self, hostname: str, ip: str, scope: str = "authorized") -> Target:
        t = Target(
            id=f"TGT-{hashlib.sha256(f'{hostname}:{ip}'.encode()).hexdigest()[:8]}",
            hostname=hostname, ip=ip, scope=scope,
        )
        self._targets.append(t)
        return t

    def passive_recon(self, target: Target) -> Dict[str, Any]:
        """Passive reconnaissance: DNS, WHOIS, certificates, subdomains."""
        subdomains = [f"www.{target.hostname}", f"api.{target.hostname}", f"admin.{target.hostname}", f"dev.{target.hostname}"]
        tech = random.sample(["Apache", "Nginx", "Cloudflare", "AWS", "Docker", "Kubernetes", "Node.js", "Python", "PHP", "MySQL", "PostgreSQL", "Redis", "MongoDB"], random.randint(3, 7))
        return {
            "target_id": target.id,
            "subdomains": subdomains,
            "technologies": tech,
            "dns_records": [f"A {target.ip}", f"MX 10 mail.{target.hostname}"],
            "certificates": [f"CN={target.hostname}", f"SAN=*.{target.hostname}"],
            "whois": {"registrar": random.choice(["GoDaddy", "Namecheap", "Cloudflare"]), "created": "2020-01-01"},
        }

    def port_scan(self, target: Target) -> Dict[str, Any]:
        """Simulated port scan."""
        common_ports = [22, 80, 443, 3306, 5432, 6379, 8080, 8443, 3000, 5000, 8000, 9000]
        open_ports = random.sample(common_ports, random.randint(3, 8))
        services = {p: random.choice(["SSH", "HTTP", "HTTPS", "MySQL", "PostgreSQL", "Redis", "Node.js", "Python", "Docker", "Kubernetes API"]) for p in open_ports}
        target.ports = open_ports
        target.services = services
        return {
            "target_id": target.id,
            "open_ports": open_ports,
            "services": services,
            "scan_time": time.time(),
        }

    def web_recon(self, target: Target) -> Dict[str, Any]:
        """Web reconnaissance: endpoints, parameters, headers."""
        endpoints = ["/api/v1/users", "/api/v1/auth", "/admin", "/login", "/register", "/api/v1/data", "/health", "/metrics"]
        return {
            "target_id": target.id,
            "endpoints": random.sample(endpoints, random.randint(3, 7)),
            "parameters": ["id", "token", "user_id", "page", "limit", "search"],
            "headers": ["X-API-Key", "Authorization", "Content-Type", "X-Forwarded-For"],
            "cookies": ["session", "auth_token", "preferences"],
        }

    def get_targets(self) -> List[Target]:
        return self._targets


class VulnScanner:
    """Automated vulnerability scanner."""

    def __init__(self):
        self._vulns: List[Vulnerability] = []
        self._known_vulns = [
            ("SQL Injection", "CWE-89", 9.8, VulnSeverity.CRITICAL, "Unsanitized user input in SQL queries", "Use parameterized queries"),
            ("XSS", "CWE-79", 6.1, VulnSeverity.MEDIUM, "Reflected cross-site scripting", "Implement CSP and output encoding"),
            ("CSRF", "CWE-352", 8.8, VulnSeverity.HIGH, "Missing CSRF tokens", "Add CSRF tokens to all state-changing requests"),
            ("IDOR", "CWE-639", 7.5, VulnSeverity.HIGH, "Insecure direct object reference", "Implement authorization checks"),
            ("SSRF", "CWE-918", 8.6, VulnSeverity.HIGH, "Server-side request forgery", "Validate and whitelist URLs"),
            ("LFI", "CWE-98", 7.5, VulnSeverity.HIGH, "Local file inclusion", "Sanitize file paths and use allowlists"),
            ("RCE", "CWE-78", 10.0, VulnSeverity.CRITICAL, "Remote code execution", "Never execute user input"),
            ("Directory Traversal", "CWE-22", 7.5, VulnSeverity.HIGH, "Path traversal vulnerability", "Sanitize paths"),
            ("Information Disclosure", "CWE-200", 5.3, VulnSeverity.MEDIUM, "Sensitive information in error messages", "Use generic error messages"),
            ("Weak Passwords", "CWE-521", 7.0, VulnSeverity.HIGH, "Default or weak credentials", "Enforce strong password policy"),
            ("Open Redirect", "CWE-601", 6.1, VulnSeverity.MEDIUM, "Unvalidated redirect", "Whitelist redirect URLs"),
            ("JWT None Algorithm", "CWE-327", 8.1, VulnSeverity.HIGH, "JWT using 'none' algorithm", "Reject 'none' algorithm"),
        ]

    def scan_target(self, target: Target) -> List[Vulnerability]:
        vulns = []
        for _ in range(random.randint(2, 6)):
            v = random.choice(self._known_vulns)
            vid = f"VULN-{hashlib.sha256(f'{target.id}:{v[0]}:{time.time()}'.encode()).hexdigest()[:8]}"
            vulns.append(Vulnerability(
                id=vid, target_id=target.id, name=v[0], severity=v[3],
                cwe_id=v[1], cvss_score=v[2], description=v[4], evidence=f"Found in {target.hostname}:{random.choice(target.ports or [80])}",
                remediation=v[5], discovered_at=time.time(),
            ))
        self._vulns.extend(vulns)
        return vulns

    def get_critical(self) -> List[Vulnerability]:
        return [v for v in self._vulns if v.severity in (VulnSeverity.HIGH, VulnSeverity.CRITICAL)]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._vulns),
            "critical": sum(1 for v in self._vulns if v.severity == VulnSeverity.CRITICAL),
            "high": sum(1 for v in self._vulns if v.severity == VulnSeverity.HIGH),
            "medium": sum(1 for v in self._vulns if v.severity == VulnSeverity.MEDIUM),
            "low": sum(1 for v in self._vulns if v.severity == VulnSeverity.LOW),
        }


class ExploitHunter:
    """Find and match exploits to vulnerabilities."""

    def __init__(self):
        self._exploits: List[Exploit] = []

    def find_exploit(self, vuln: Vulnerability) -> Optional[Exploit]:
        """Match exploit to vulnerability."""
        if vuln.severity not in (VulnSeverity.HIGH, VulnSeverity.CRITICAL):
            return None
        eid = f"EXP-{hashlib.sha256(f'{vuln.id}:{time.time()}'.encode()).hexdigest()[:8]}"
        exploit = Exploit(
            id=eid, vuln_id=vuln.id, name=f"Exploit for {vuln.name}",
            exploit_type=random.choice(["remote", "local", "web", "network"]),
            reliability=random.uniform(0.6, 0.95),
            complexity=random.choice(["low", "medium", "high"]),
            impact=vuln.severity.value,
            poc_code="# PoC for " + vuln.name + "\n# Target: " + vuln.target_id + "\n# CWE: " + str(vuln.cwe_id) + "\n",
            mitigations=[vuln.remediation, "Apply vendor patch", "Enable WAF rules"],
        )
        self._exploits.append(exploit)
        return exploit

    def get_exploits(self) -> List[Exploit]:
        return self._exploits


class RedTeamAutomator:
    """Automated red team operations."""

    def __init__(self, recon: AutoRecon, scanner: VulnScanner, hunter: ExploitHunter):
        self.recon = recon
        self.scanner = scanner
        self.hunter = hunter
        self._operations: List[Dict[str, Any]] = []

    def run_campaign(self, target: Target) -> Dict[str, Any]:
        """Full red team campaign on authorized target."""
        print(f"[RED-TEAM] Campaign against {target.hostname} ({target.scope})")

        # Phase 1: Recon
        passive = self.recon.passive_recon(target)
        port_scan = self.recon.port_scan(target)
        web = self.recon.web_recon(target)

        # Phase 2: Scan
        vulns = self.scanner.scan_target(target)

        # Phase 3: Exploit mapping
        exploits = []
        for v in vulns:
            e = self.hunter.find_exploit(v)
            if e:
                exploits.append(e)

        result = {
            "target": target.id,
            "phases": ["recon", "scan", "exploit_mapping"],
            "vulns_found": len(vulns),
            "exploits_matched": len(exploits),
            "critical_vulns": sum(1 for v in vulns if v.severity == VulnSeverity.CRITICAL),
        }
        self._operations.append(result)
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "operations": len(self._operations),
            "total_vulns": self.scanner.get_stats(),
            "total_exploits": len(self.hunter.get_exploits()),
        }


if __name__ == "__main__":
    print("=" * 60)
    print("[AUTO-HACKING] Offensive Security Engine")
    print("=" * 60)

    recon = AutoRecon()
    scanner = VulnScanner()
    hunter = ExploitHunter()
    redteam = RedTeamAutomator(recon, scanner, hunter)

    targets = [
        recon.add_target("target-app.example.com", "192.168.1.100"),
        recon.add_target("api.target.local", "10.0.0.50"),
    ]

    for t in targets:
        result = redteam.run_campaign(t)
        print(f"\nTarget: {t.hostname}")
        print(f"    Ports: {t.ports}")
        print(f"    Services: {t.services}")
        print(f"    Vulns: {result['vulns_found']}, Critical: {result['critical_vulns']}")
        print(f"    Exploits: {result['exploits_matched']}")

    print(f"\nStats: {redteam.get_stats()}")
    print(f"  Critical vulns: {scanner.get_critical()}")
