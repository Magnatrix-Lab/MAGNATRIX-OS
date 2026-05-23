"""
MAGNATRIX — Bug Bounty Security Testing Framework
Native Python implementation of web application security testing methodology.
Observed from: fin1te/bugbounty methodology and industry best practices.

Pattern: AMATI-PELAJARI-TIRU — observe core patterns, reimplement as consolidated module.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import random
import re
import string
import time
import urllib.parse
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ═══════════════════════════════════════════════════════════════════════════════
# CORE DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnType(Enum):
    XSS = "Cross-Site Scripting"
    SQLI = "SQL Injection"
    CSRF = "Cross-Site Request Forgery"
    IDOR = "Insecure Direct Object Reference"
    SSRF = "Server-Side Request Forgery"
    LFI = "Local File Inclusion"
    RFI = "Remote File Inclusion"
    CMDI = "Command Injection"
    XXE = "XML External Entity"
    OPEN_REDIRECT = "Open Redirect"
    PATH_TRAVERSAL = "Path Traversal"
    INSECURE_DESERIALIZATION = "Insecure Deserialization"


@dataclass
class Target:
    """Target untuk security testing."""
    domain: str
    ip: Optional[str] = None
    ports: List[int] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)
    subdomains: List[str] = field(default_factory=list)
    endpoints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "ip": self.ip,
            "ports": self.ports,
            "tech_stack": self.tech_stack,
            "subdomains": len(self.subdomains),
            "endpoints": len(self.endpoints),
        }


@dataclass
class Vulnerability:
    """Hasil temuan vulnerability."""
    id: str = field(default_factory=lambda: f"VULN-{uuid.uuid4().hex[:8].upper()}")
    vuln_type: VulnType = VulnType.XSS
    severity: Severity = Severity.MEDIUM
    target: str = ""
    endpoint: str = ""
    parameter: str = ""
    payload: str = ""
    evidence: str = ""
    cvss_score: float = 0.0
    remediation: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.vuln_type.value,
            "severity": self.severity.value,
            "target": self.target,
            "endpoint": self.endpoint,
            "parameter": self.parameter,
            "cvss": self.cvss_score,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 1: ReconEngine
# ═══════════════════════════════════════════════════════════════════════════════

class ReconEngine:
    """Reconnaissance engine untuk target enumeration."""

    def __init__(self, target: Target) -> None:
        self.target = target
        self.wordlist: List[str] = []

    def load_wordlist(self, words: List[str]) -> None:
        self.wordlist = words

    async def enumerate_subdomains(self) -> List[str]:
        """Subdomain enumeration dengan brute-force dan permutation."""
        found = []
        prefixes = ["www", "api", "dev", "staging", "admin", "portal", "blog", "shop", "mail", "ftp"]
        
        for prefix in prefixes:
            subdomain = f"{prefix}.{self.target.domain}"
            # Mock: simulate DNS resolution
            await asyncio.sleep(0.01)
            if random.random() > 0.3:  # 70% chance exists
                found.append(subdomain)
        
        # Permutation dari wordlist
        if self.wordlist:
            for word in self.wordlist[:20]:  # Limit untuk demo
                subdomain = f"{word}.{self.target.domain}"
                await asyncio.sleep(0.01)
                if random.random() > 0.7:
                    found.append(subdomain)
        
        self.target.subdomains = list(set(found))
        return self.target.subdomains

    async def port_scan(self, ports: List[int] = None) -> Dict[int, str]:
        """TCP connect port scanning."""
        if ports is None:
            ports = [80, 443, 8080, 8443, 3000, 5000, 22, 21, 3306, 5432]
        
        results = {}
        for port in ports:
            await asyncio.sleep(0.02)
            # Mock: common ports open
            if port in [80, 443, 8080, 3000, 5000] and random.random() > 0.2:
                results[port] = "open"
                self.target.ports.append(port)
            else:
                results[port] = "closed"
        
        return results

    async def fingerprint_tech(self) -> List[str]:
        """Technology fingerprinting dari HTTP headers dan response."""
        tech_signatures = {
            "Server: nginx": "nginx",
            "Server: Apache": "Apache",
            "X-Powered-By: PHP": "PHP",
            "X-Powered-By: Express": "Node.js/Express",
            "Set-Cookie: PHPSESSID": "PHP",
            "X-AspNet-Version": "ASP.NET",
            "X-Generator: Drupal": "Drupal",
            "wp-content": "WordPress",
            "react": "React",
            "vue": "Vue.js",
            "django": "Django",
            "rails": "Ruby on Rails",
        }
        
        # Mock: detect random tech stack
        detected = []
        for signature, tech in tech_signatures.items():
            if random.random() > 0.6:
                detected.append(tech)
        
        self.target.tech_stack = list(set(detected))
        return self.target.tech_stack

    async def crawl_endpoints(self, max_depth: int = 2) -> List[str]:
        """Web crawling untuk endpoint discovery."""
        common_paths = [
            "/", "/admin", "/api", "/login", "/register", "/dashboard",
            "/upload", "/search", "/profile", "/settings", "/backup",
            "/.env", "/config.php", "/robots.txt", "/sitemap.xml",
            "/api/v1/users", "/api/v1/auth", "/graphql", "/swagger",
        ]
        
        found = []
        for path in common_paths:
            await asyncio.sleep(0.01)
            if random.random() > 0.4:
                found.append(f"https://{self.target.domain}{path}")
        
        self.target.endpoints = found
        return found

    def generate_favicon_hash(self, favicon_bytes: bytes) -> str:
        """Generate MurmurHash-style favicon hash untuk tech identification."""
        return hashlib.md5(favicon_bytes).hexdigest()[:16]

    async def full_recon(self) -> Target:
        """Run full reconnaissance suite."""
        await self.enumerate_subdomains()
        await self.port_scan()
        await self.fingerprint_tech()
        await self.crawl_endpoints()
        return self.target


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 2: PayloadManager
# ═══════════════════════════════════════════════════════════════════════════════

class PayloadManager:
    """Organized payload library untuk vulnerability testing."""

    def __init__(self) -> None:
        self.payloads: Dict[VulnType, List[str]] = {
            VulnType.XSS: [
                "<script>alert(1)</script>",
                "<img src=x onerror=alert(1)>",
                "javascript:alert(1)",
                "<svg onload=alert(1)>",
                "'\"><script>alert(1)</script>",
                "<body onload=alert(1)>",
            ],
            VulnType.SQLI: [
                "' OR '1'='1",
                "' UNION SELECT null,null--",
                "1 AND 1=1",
                "1' AND SLEEP(5)--",
                "1; DROP TABLE users--",
                "' OR 1=1--",
            ],
            VulnType.CMDI: [
                "; ls -la",
                "| cat /etc/passwd",
                "$(whoami)",
                "`id`",
                "; ping -c 4 attacker.com",
            ],
            VulnType.LFI: [
                "../../../etc/passwd",
                "....//....//etc/passwd",
                "%2e%2e%2fetc%2fpasswd",
                "php://filter/read=convert.base64-encode/resource=index.php",
            ],
            VulnType.SSRF: [
                "http://127.0.0.1:22",
                "http://169.254.169.254/latest/meta-data/",
                "file:///etc/passwd",
                "dict://127.0.0.1:11211",
            ],
            VulnType.OPEN_REDIRECT: [
                "https://evil.com",
                "//evil.com",
                "/\\evil.com",
                "https://target.com.evil.com",
            ],
        }

    def get_payloads(self, vuln_type: VulnType) -> List[str]:
        return self.payloads.get(vuln_type, [])

    def encode_payload(self, payload: str, encoding: str = "url") -> str:
        if encoding == "url":
            return urllib.parse.quote(payload)
        elif encoding == "base64":
            return base64.b64encode(payload.encode()).decode()
        elif encoding == "html":
            return payload.replace("<", "&lt;").replace(">", "&gt;")
        return payload

    def mutate_payload(self, payload: str) -> List[str]:
        """Generate payload variants dengan encoding dan case mutations."""
        variants = [payload]
        variants.append(self.encode_payload(payload, "url"))
        variants.append(payload.upper())
        variants.append(payload.replace(" ", "+"))
        return variants

    def add_custom_payload(self, vuln_type: VulnType, payload: str) -> None:
        if vuln_type not in self.payloads:
            self.payloads[vuln_type] = []
        self.payloads[vuln_type].append(payload)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 3: VulnScanner
# ═══════════════════════════════════════════════════════════════════════════════

class VulnScanner:
    """Vulnerability scanner dengan multiple test vectors."""

    def __init__(self, target: Target, payloads: PayloadManager) -> None:
        self.target = target
        self.payloads = payloads
        self.findings: List[Vulnerability] = []
        self.tested_params: Set[str] = set()

    async def scan_xss(self, endpoint: str, params: List[str]) -> List[Vulnerability]:
        """Test untuk reflected, stored, dan DOM-based XSS."""
        findings = []
        xss_payloads = self.payloads.get_payloads(VulnType.XSS)
        
        for param in params:
            for payload in xss_payloads[:3]:  # Limit untuk demo
                await asyncio.sleep(0.02)
                # Mock: detect XSS jika payload mengandung script tag
                if "<script>" in payload and random.random() > 0.5:
                    vuln = Vulnerability(
                        vuln_type=VulnType.XSS,
                        severity=Severity.HIGH,
                        target=self.target.domain,
                        endpoint=endpoint,
                        parameter=param,
                        payload=payload,
                        evidence=f"Payload reflected in response: {payload[:30]}",
                        cvss_score=6.1,
                        remediation="Implement proper output encoding and CSP headers.",
                    )
                    findings.append(vuln)
        
        self.findings.extend(findings)
        return findings

    async def scan_sqli(self, endpoint: str, params: List[str]) -> List[Vulnerability]:
        """Test untuk SQL injection (error-based, blind, time-based)."""
        findings = []
        sqli_payloads = self.payloads.get_payloads(VulnType.SQLI)
        
        for param in params:
            for payload in sqli_payloads[:3]:
                await asyncio.sleep(0.02)
                # Mock: detect SQL error keywords
                error_keywords = ["mysql", "syntax", "error", "ora-", "sqlite"]
                if random.random() > 0.6:
                    vuln = Vulnerability(
                        vuln_type=VulnType.SQLI,
                        severity=Severity.CRITICAL,
                        target=self.target.domain,
                        endpoint=endpoint,
                        parameter=param,
                        payload=payload,
                        evidence=f"Database error detected with payload: {payload[:30]}",
                        cvss_score=9.8,
                        remediation="Use parameterized queries/prepared statements.",
                    )
                    findings.append(vuln)
        
        self.findings.extend(findings)
        return findings

    async def scan_csrf(self, endpoint: str) -> List[Vulnerability]:
        """Test untuk CSRF vulnerability."""
        findings = []
        await asyncio.sleep(0.03)
        
        # Mock: check untuk missing CSRF token
        if random.random() > 0.5:
            vuln = Vulnerability(
                vuln_type=VulnType.CSRF,
                severity=Severity.MEDIUM,
                target=self.target.domain,
                endpoint=endpoint,
                parameter="form_submission",
                evidence="No CSRF token found in form submission",
                cvss_score=6.5,
                remediation="Implement CSRF tokens and SameSite cookie attributes.",
            )
            findings.append(vuln)
        
        self.findings.extend(findings)
        return findings

    async def scan_idor(self, endpoint: str, params: List[str]) -> List[Vulnerability]:
        """Test untuk IDOR dengan parameter fuzzing."""
        findings = []
        test_values = ["1", "2", "100", "999", "../other"]
        
        for param in params:
            for value in test_values:
                await asyncio.sleep(0.01)
                if random.random() > 0.7:
                    vuln = Vulnerability(
                        vuln_type=VulnType.IDOR,
                        severity=Severity.HIGH,
                        target=self.target.domain,
                        endpoint=endpoint,
                        parameter=param,
                        payload=f"{param}={value}",
                        evidence=f"Access granted to resource ID: {value}",
                        cvss_score=7.5,
                        remediation="Implement proper authorization checks for all resources.",
                    )
                    findings.append(vuln)
        
        self.findings.extend(findings)
        return findings

    async def scan_ssrf(self, endpoint: str, params: List[str]) -> List[Vulnerability]:
        """Test untuk Server-Side Request Forgery."""
        findings = []
        ssrf_payloads = self.payloads.get_payloads(VulnType.SSRF)
        
        for param in params:
            for payload in ssrf_payloads[:2]:
                await asyncio.sleep(0.02)
                if random.random() > 0.6:
                    vuln = Vulnerability(
                        vuln_type=VulnType.SSRF,
                        severity=Severity.HIGH,
                        target=self.target.domain,
                        endpoint=endpoint,
                        parameter=param,
                        payload=payload,
                        evidence=f"Internal resource accessed: {payload[:40]}",
                        cvss_score=8.5,
                        remediation="Validate and sanitize all user-supplied URLs.",
                    )
                    findings.append(vuln)
        
        self.findings.extend(findings)
        return findings

    async def scan_lfi(self, endpoint: str, params: List[str]) -> List[Vulnerability]:
        """Test untuk Local File Inclusion."""
        findings = []
        lfi_payloads = self.payloads.get_payloads(VulnType.LFI)
        
        for param in params:
            for payload in lfi_payloads[:2]:
                await asyncio.sleep(0.02)
                if random.random() > 0.6:
                    vuln = Vulnerability(
                        vuln_type=VulnType.LFI,
                        severity=Severity.HIGH,
                        target=self.target.domain,
                        endpoint=endpoint,
                        parameter=param,
                        payload=payload,
                        evidence=f"File content retrieved: {payload[:40]}",
                        cvss_score=7.5,
                        remediation="Avoid user input in file paths; use allowlists.",
                    )
                    findings.append(vuln)
        
        self.findings.extend(findings)
        return findings

    async def scan_cmdi(self, endpoint: str, params: List[str]) -> List[Vulnerability]:
        """Test untuk Command Injection."""
        findings = []
        cmdi_payloads = self.payloads.get_payloads(VulnType.CMDI)
        
        for param in params:
            for payload in cmdi_payloads[:2]:
                await asyncio.sleep(0.02)
                if random.random() > 0.7:
                    vuln = Vulnerability(
                        vuln_type=VulnType.CMDI,
                        severity=Severity.CRITICAL,
                        target=self.target.domain,
                        endpoint=endpoint,
                        parameter=param,
                        payload=payload,
                        evidence=f"Command execution detected: {payload[:40]}",
                        cvss_score=9.8,
                        remediation="Never pass user input to system commands; use parameterized APIs.",
                    )
                    findings.append(vuln)
        
        self.findings.extend(findings)
        return findings

    async def full_scan(self, endpoints: List[str]) -> List[Vulnerability]:
        """Run comprehensive vulnerability scan."""
        all_findings = []
        
        for endpoint in endpoints[:5]:  # Limit untuk demo
            params = ["id", "name", "search", "url", "file", "cmd", "input"]
            
            all_findings.extend(await self.scan_xss(endpoint, params))
            all_findings.extend(await self.scan_sqli(endpoint, params))
            all_findings.extend(await self.scan_csrf(endpoint))
            all_findings.extend(await self.scan_idor(endpoint, params))
            all_findings.extend(await self.scan_ssrf(endpoint, params))
            all_findings.extend(await self.scan_lfi(endpoint, params))
            all_findings.extend(await self.scan_cmdi(endpoint, params))
        
        return all_findings


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 4: ProxyStub
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HTTPMessage:
    """HTTP request atau response message."""
    method: str = "GET"
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    status_code: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "body_length": len(self.body),
            "status": self.status_code,
        }


class ProxyStub:
    """Burp-style HTTP intercept proxy stub."""

    def __init__(self) -> None:
        self.intercept_enabled = False
        self.history: List[HTTPMessage] = []
        self.modification_rules: List[Callable[[HTTPMessage], HTTPMessage]] = []
        self.repeater_queue: List[HTTPMessage] = []

    def enable_intercept(self) -> None:
        self.intercept_enabled = True

    def disable_intercept(self) -> None:
        self.intercept_enabled = False

    async def intercept_request(self, request: HTTPMessage) -> HTTPMessage:
        """Intercept dan modify outgoing request."""
        if self.intercept_enabled:
            # Apply modification rules
            for rule in self.modification_rules:
                request = rule(request)
        
        self.history.append(request)
        return request

    async def intercept_response(self, response: HTTPMessage) -> HTTPMessage:
        """Intercept dan modify incoming response."""
        self.history.append(response)
        return response

    def add_modification_rule(self, rule: Callable[[HTTPMessage], HTTPMessage]) -> None:
        self.modification_rules.append(rule)

    def add_header_to_all(self, header: str, value: str) -> None:
        """Add header ke semua requests."""
        def rule(msg: HTTPMessage) -> HTTPMessage:
            msg.headers[header] = value
            return msg
        self.add_modification_rule(rule)

    def get_history(self, limit: int = 100) -> List[HTTPMessage]:
        return self.history[-limit:]

    def send_to_repeater(self, request: HTTPMessage) -> None:
        self.repeater_queue.append(request)

    async def repeater_send(self, modified_request: HTTPMessage) -> HTTPMessage:
        """Send modified request (mock)."""
        await asyncio.sleep(0.05)
        return HTTPMessage(
            method=modified_request.method,
            url=modified_request.url,
            status_code=200,
            body="Modified request response",
        )

    def search_history(self, keyword: str) -> List[HTTPMessage]:
        return [msg for msg in self.history if keyword in msg.url or keyword in msg.body]


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 5: ReportGenerator
# ═══════════════════════════════════════════════════════════════════════════════

class ReportGenerator:
    """Generate structured vulnerability report."""

    def __init__(self) -> None:
        self.template = {
            "title": "Bug Bounty Security Assessment Report",
            "version": "1.0",
            "generated_at": time.time(),
        }

    def calculate_cvss(self, vuln: Vulnerability) -> float:
        """Simplified CVSS 3.1 scoring."""
        base_scores = {
            Severity.CRITICAL: 9.0 + random.random(),
            Severity.HIGH: 7.5 + random.random() * 1.5,
            Severity.MEDIUM: 4.0 + random.random() * 3.5,
            Severity.LOW: 1.0 + random.random() * 3.0,
            Severity.INFO: 0.0,
        }
        return min(base_scores.get(vuln.severity, 5.0), 10.0)

    def classify_severity(self, cvss: float) -> Severity:
        if cvss >= 9.0:
            return Severity.CRITICAL
        elif cvss >= 7.0:
            return Severity.HIGH
        elif cvss >= 4.0:
            return Severity.MEDIUM
        elif cvss >= 1.0:
            return Severity.LOW
        return Severity.INFO

    def generate_report(self, target: Target, findings: List[Vulnerability]) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        # Update CVSS scores
        for vuln in findings:
            vuln.cvss_score = self.calculate_cvss(vuln)
            vuln.severity = self.classify_severity(vuln.cvss_score)

        # Group by severity
        severity_counts = {sev: 0 for sev in Severity}
        for vuln in findings:
            severity_counts[vuln.severity] += 1

        # Group by type
        type_counts: Dict[str, int] = {}
        for vuln in findings:
            type_counts[vuln.vuln_type.value] = type_counts.get(vuln.vuln_type.value, 0) + 1

        report = {
            "report_metadata": {
                "title": self.template["title"],
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "target": target.to_dict(),
            },
            "executive_summary": {
                "total_findings": len(findings),
                "severity_distribution": {k.value: v for k, v in severity_counts.items()},
                "vulnerability_types": type_counts,
                "risk_rating": self._calculate_overall_risk(findings),
            },
            "detailed_findings": [vuln.to_dict() for vuln in findings],
            "remediation_priorities": self._prioritize_remediation(findings),
        }

        return report

    def _calculate_overall_risk(self, findings: List[Vulnerability]) -> str:
        if any(v.severity == Severity.CRITICAL for v in findings):
            return "CRITICAL - Immediate action required"
        elif any(v.severity == Severity.HIGH for v in findings):
            return "HIGH - Address within 7 days"
        elif any(v.severity == Severity.MEDIUM for v in findings):
            return "MEDIUM - Address within 30 days"
        elif findings:
            return "LOW - Address in next maintenance cycle"
        return "NO RISK - No vulnerabilities found"

    def _prioritize_remediation(self, findings: List[Vulnerability]) -> List[Dict[str, Any]]:
        """Prioritize remediation by severity and exploitability."""
        sorted_findings = sorted(findings, key=lambda v: v.cvss_score, reverse=True)
        return [
            {
                "priority": i + 1,
                "vuln_id": vuln.id,
                "type": vuln.vuln_type.value,
                "severity": vuln.severity.value,
                "cvss": round(vuln.cvss_score, 1),
                "endpoint": vuln.endpoint,
                "remediation": vuln.remediation,
            }
            for i, vuln in enumerate(sorted_findings[:10])
        ]

    def export_json(self, report: Dict[str, Any], filename: str = "report.json") -> str:
        """Export report ke JSON file."""
        json_str = json.dumps(report, indent=2)
        return json_str

    def export_markdown(self, report: Dict[str, Any]) -> str:
        """Export report ke Markdown format."""
        md = f"""# {report['report_metadata']['title']}

## Executive Summary

- **Target**: {report['report_metadata']['target']['domain']}
- **Total Findings**: {report['executive_summary']['total_findings']}
- **Risk Rating**: {report['executive_summary']['risk_rating']}

### Severity Distribution

"""
        for sev, count in report['executive_summary']['severity_distribution'].items():
            md += f"- **{sev.upper()}**: {count}\n"

        md += "\n## Detailed Findings\n\n"
        for finding in report['detailed_findings']:
            md += f"""### {finding['id']} - {finding['type']}

- **Severity**: {finding['severity']}
- **CVSS**: {finding['cvss']}
- **Endpoint**: {finding['endpoint']}
- **Parameter**: {finding['parameter']}

"""

        return md


# ═══════════════════════════════════════════════════════════════════════════════
# MAGNATRIX INTEGRATION: SecurityOrchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityOrchestrator:
    """Orchestrator untuk security testing workflow."""

    def __init__(self, domain: str) -> None:
        self.target = Target(domain=domain)
        self.recon = ReconEngine(self.target)
        self.payloads = PayloadManager()
        self.scanner = VulnScanner(self.target, self.payloads)
        self.proxy = ProxyStub()
        self.reporter = ReportGenerator()

    async def run_full_assessment(self) -> Dict[str, Any]:
        """Run complete security assessment."""
        print(f"[*] Starting security assessment for: {self.target.domain}")
        
        # Phase 1: Reconnaissance
        print("[*] Phase 1: Reconnaissance")
        await self.recon.full_recon()
        print(f"[+] Found {len(self.target.subdomains)} subdomains")
        print(f"[+] Open ports: {self.target.ports}")
        print(f"[+] Tech stack: {self.target.tech_stack}")
        
        # Phase 2: Vulnerability Scanning
        print("[*] Phase 2: Vulnerability Scanning")
        findings = await self.scanner.full_scan(self.target.endpoints)
        print(f"[+] Found {len(findings)} vulnerabilities")
        
        # Phase 3: Report Generation
        print("[*] Phase 3: Report Generation")
        report = self.reporter.generate_report(self.target, findings)
        
        return {
            "target": self.target.to_dict(),
            "findings_count": len(findings),
            "report": report,
        }

    def get_findings_by_severity(self, severity: Severity) -> List[Vulnerability]:
        return [v for v in self.scanner.findings if v.severity == severity]

    def get_findings_by_type(self, vuln_type: VulnType) -> List[Vulnerability]:
        return [v for v in self.scanner.findings if v.vuln_type == vuln_type]


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO / __main__
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    async def demo() -> None:
        print("=" * 70)
        print("MAGNATRIX — Bug Bounty Security Framework Demo")
        print("=" * 70)

        # Initialize orchestrator
        orchestrator = SecurityOrchestrator("example.com")
        
        # Load wordlist untuk subdomain enum
        orchestrator.recon.load_wordlist([
            "dev", "test", "api", "staging", "prod", "internal",
            "admin", "portal", "secure", "vpn", "mail", "ftp",
        ])

        # Run full assessment
        result = await orchestrator.run_full_assessment()
        
        print("\n" + "=" * 70)
        print("ASSESSMENT COMPLETE")
        print("=" * 70)
        
        # Summary
        report = result["report"]
        print(f"\nTarget: {report['report_metadata']['target']['domain']}")
        print(f"Total Findings: {report['executive_summary']['total_findings']}")
        print(f"Risk Rating: {report['executive_summary']['risk_rating']}")
        
        # Severity breakdown
        print("\nSeverity Distribution:")
        for sev, count in report['executive_summary']['severity_distribution'].items():
            if count > 0:
                print(f"  {sev.upper()}: {count}")
        
        # Top findings
        print("\nTop 5 Findings:")
        for finding in report['detailed_findings'][:5]:
            print(f"  [{finding['id']}] {finding['type']} ({finding['severity']}) - CVSS: {finding['cvss']}")
        
        # Export formats
        print("\n" + "=" * 70)
        json_report = orchestrator.reporter.export_json(report)
        print(f"JSON Report: {len(json_report)} bytes")
        
        md_report = orchestrator.reporter.export_markdown(report)
        print(f"Markdown Report: {len(md_report)} bytes")
        
        # Proxy demo
        print("\nProxy Stub Demo:")
        req = HTTPMessage(
            method="POST",
            url="https://example.com/api/login",
            headers={"Content-Type": "application/json"},
            body='{"username":"admin","password":"test"}',
        )
        orchestrator.proxy.add_header_to_all("X-BugBounty-Scan", "true")
        modified = await orchestrator.proxy.intercept_request(req)
        print(f"Modified request headers: {modified.headers}")
        
        print("\n" + "=" * 70)
        print("Demo complete.")
        print("=" * 70)

    asyncio.run(demo())
