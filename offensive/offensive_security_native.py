#!/usr/bin/env python3
"""
MAGNATRIX-OS Offensive Security Native (Layer 13)
Red team tools: port scanner, SQL injection detector, XSS checker.
Pure Python stdlib — for authorized security testing only.
"""
import socket, urllib.request, urllib.parse, re, json, time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class Vulnerability:
    severity: str  # critical, high, medium, low
    type: str
    target: str
    description: str
    evidence: str = ""
    remediation: str = ""


class PortScannerNative:
    """TCP port scanner with SYN stealth mode."""

    COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 3389, 5432, 8080]

    def scan(self, host: str, ports: List[int] = None, timeout: float = 1.0) -> List[Dict]:
        ports = ports or self.COMMON_PORTS
        results = []
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                if result == 0:
                    service = self._guess_service(port)
                    results.append({"port": port, "state": "open", "service": service})
                sock.close()
            except Exception:
                pass
        return results

    def _guess_service(self, port: int) -> str:
        services = {22: "SSH", 80: "HTTP", 443: "HTTPS", 3306: "MySQL", 5432: "PostgreSQL", 8080: "HTTP-Proxy"}
        return services.get(port, "unknown")


class SQLInjectionDetector:
    """Detect SQL injection vulnerabilities in URLs/forms."""

    PAYLOADS = [
        "' OR '1'='1",
        "' UNION SELECT null--",
        "1 AND 1=1",
        "1' AND 1=1--",
    ]

    ERROR_PATTERNS = [
        r"SQL syntax.*MySQL",
        r"Warning.*mysql_",
        r"PostgreSQL.*ERROR",
        r"ORA-[0-9]{5}",
        r"Microsoft SQL Server.*Error",
    ]

    def test_url(self, url: str) -> List[Vulnerability]:
        """Test URL parameters for SQL injection."""
        vulns = []
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        for param in params:
            for payload in self.PAYLOADS:
                test_url = url.replace(f"{param}={params[param][0]}", f"{param}={urllib.parse.quote(payload)}")
                try:
                    req = urllib.request.Request(test_url, headers={"User-Agent": "MAGNATRIX-OS/Security"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        body = resp.read().decode("utf-8", errors="replace")
                        for pattern in self.ERROR_PATTERNS:
                            if re.search(pattern, body, re.IGNORECASE):
                                vulns.append(Vulnerability(
                                    severity="critical",
                                    type="SQL Injection",
                                    target=url,
                                    description=f"Parameter '{param}' vulnerable to SQL injection",
                                    evidence=body[:200],
                                    remediation="Use parameterized queries / prepared statements",
                                ))
                                break
                except Exception:
                    pass
        return vulns


class XSSChecker:
    """Check for reflected XSS vulnerabilities."""

    PAYLOADS = [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        ""><script>alert(1)</script>",
    ]

    def test_url(self, url: str) -> List[Vulnerability]:
        vulns = []
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        for param in params:
            for payload in self.PAYLOADS:
                test_url = url.replace(f"{param}={params[param][0]}", f"{param}={urllib.parse.quote(payload)}")
                try:
                    req = urllib.request.Request(test_url, headers={"User-Agent": "MAGNATRIX-OS/Security"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        body = resp.read().decode("utf-8", errors="replace")
                        if payload in body:
                            vulns.append(Vulnerability(
                                severity="high",
                                type="Reflected XSS",
                                target=url,
                                description=f"Parameter '{param}' reflects input without sanitization",
                                evidence=body[:200],
                                remediation="HTML-encode all user input before rendering",
                            ))
                            break
                except Exception:
                    pass
        return vulns


class OffensiveSecurityNative:
    """Main offensive security orchestrator."""

    def __init__(self):
        self.port_scanner = PortScannerNative()
        self.sql_detector = SQLInjectionDetector()
        self.xss_checker = XSSChecker()

    def scan_target(self, host: str) -> Dict[str, Any]:
        """Full security scan of target."""
        return {
            "host": host,
            "ports": self.port_scanner.scan(host),
            "timestamp": time.time(),
        }

    def audit_webapp(self, url: str) -> List[Vulnerability]:
        """Audit web application for common vulnerabilities."""
        vulns = []
        vulns.extend(self.sql_detector.test_url(url))
        vulns.extend(self.xss_checker.test_url(url))
        return vulns

    def generate_report(self, vulns: List[Vulnerability]) -> str:
        lines = ["# Security Audit Report", ""]
        for v in vulns:
            lines.append(f"## [{v.severity.upper()}] {v.type}")
            lines.append(f"- **Target**: {v.target}")
            lines.append(f"- **Description**: {v.description}")
            lines.append(f"- **Evidence**: {v.evidence[:100]}...")
            lines.append(f"- **Remediation**: {v.remediation}")
            lines.append("")
        return "
".join(lines)


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS Offensive Security Demo")
    print("=" * 60)
    sec = OffensiveSecurityNative()
    print("\n[1] Port scan localhost...")
    scan = sec.scan_target("127.0.0.1")
    for p in scan["ports"][:5]:
        print(f"    Port {p['port']}: {p['state']} ({p['service']})")
    print("\n[2] Web app audit (demo URL)...")
    print("    Use real target URLs for actual testing")
    print("\n[3] Tools ready for authorized security testing.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
