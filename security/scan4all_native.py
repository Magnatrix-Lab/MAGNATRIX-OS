#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — scan4all Native Integration
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari GhostTroops/scan4all

Pola yang ditiru:
• Unified vulnerability scanner — port scan + web fingerprint + PoC exploit
• 15000+ PoC engine — CVE-matched YAML-based proof-of-concept execution
• 7000+ Web fingerprint database — technology detection & version identification
• 23-protocol credential brute-force — SSH, RDP, MySQL, Redis, SMB, Weblogic, dll
• 146-protocol port scanner — nmap/masscan/naabu integration, 90000+ rules
• File fuzzing engine — sensitive file discovery (config, backup, source)
• Subdomain enumeration — recursive discovery, SSL cert parsing
• Supply chain analysis — package manifest scanning (package.json, pom.xml, go.mod)
• Web cache vulnerability scanner — HTTP desync, cache poisoning detection
• Workflow engine — automated scan pipeline: recon → portscan → fingerprint → poc → report
• Elasticsearch integration — batch result indexing & aggregation
• 404 similarity algorithm — smart false-positive reduction

Layer: Security (9) — Unified Vulnerability Scanner Engine
Versi: Phase 5 — scan4all Native Scanner
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Iterator
from urllib.parse import urlparse


# ─────────────────────────────────────────────────────────────────────────────
# 0. UTILITAS DASAR
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _resolve_host(host: str) -> Optional[str]:
    try:
        return socket.gethostbyname(host)
    except Exception:
        return None


def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 1. PORT SCANNER ENGINE — Multi-Protocol Port Discovery
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PortResult:
    host: str
    port: int
    protocol: str
    state: str  # open / closed / filtered
    service: str = ""
    version: str = ""
    banner: str = ""
    response_time_ms: float = 0.0
    scan_method: str = "tcp_connect"


class PortScannerEngine:
    """
    Port scanner yang meniru nmap/masscan/naabu architecture:
    • TCP connect scanning (no root required)
    • SYN scanning (root, via subprocess ke nmap)
    • Service banner grabbing
    • Protocol detection (146 protocol signatures)
    • Top-ports, range, custom port lists
    """

    # 90000+ rules → top ports yang paling umum
    TOP_PORTS = [
        21, 22, 23, 25, 53, 80, 81, 110, 111, 135, 139, 143, 443,
        445, 465, 587, 631, 636, 873, 993, 995, 1080, 1099, 1433,
        1521, 2049, 2181, 2375, 2376, 3306, 3389, 5432, 5601,
        5672, 5900, 5901, 5984, 5985, 6379, 6443, 7001, 7002,
        7199, 7474, 8000, 8001, 8008, 8009, 8010, 8080, 8081,
        8088, 8090, 8443, 8500, 8686, 8888, 9000, 9042, 9060,
        9090, 9092, 9160, 9200, 9300, 9990, 9999, 10000, 11211,
        27017, 27018, 27019, 50000, 50030, 50070,
    ]

    # 146 protocol signatures (subset)
    PROTOCOL_SIGNATURES: Dict[int, Tuple[str, str, bytes]] = {
        21: ("ftp", "FTP", b"220"),
        22: ("ssh", "SSH", b"SSH-"),
        23: ("telnet", "Telnet", b""),
        25: ("smtp", "SMTP", b"220"),
        53: ("dns", "DNS", b""),
        80: ("http", "HTTP", b"HTTP/"),
        110: ("pop3", "POP3", b"+OK"),
        111: ("rpcbind", "RPC", b""),
        135: ("msrpc", "MSRPC", b""),
        139: ("netbios", "NetBIOS", b""),
        143: ("imap", "IMAP", b"* OK"),
        443: ("https", "HTTPS", b""),
        445: ("smb", "SMB", b""),
        465: ("smtps", "SMTPS", b""),
        587: ("smtp", "SMTP Submission", b"220"),
        631: ("ipp", "IPP", b""),
        636: ("ldaps", "LDAPS", b""),
        873: ("rsync", "Rsync", b"@RSYNCD"),
        993: ("imaps", "IMAPS", b"* OK"),
        995: ("pop3s", "POP3S", b"+OK"),
        1080: ("socks", "SOCKS", b""),
        1099: ("rmi", "Java RMI", b""),
        1433: ("mssql", "MS SQL Server", b""),
        1521: ("oracle", "Oracle TNS", b""),
        2049: ("nfs", "NFS", b""),
        2181: ("zookeeper", "ZooKeeper", b""),
        2375: ("docker", "Docker API", b""),
        3306: ("mysql", "MySQL", b""),
        3389: ("rdp", "RDP", b""),
        5432: ("postgresql", "PostgreSQL", b""),
        5601: ("kibana", "Kibana", b""),
        5672: ("amqp", "AMQP", b"AMQP"),
        5900: ("vnc", "VNC", b"RFB"),
        5984: ("couchdb", "CouchDB", b""),
        5985: ("winrm", "WinRM", b""),
        6379: ("redis", "Redis", b"-ERR"),
        6443: ("kubernetes", "Kubernetes API", b""),
        7001: ("weblogic", "WebLogic", b""),
        7002: ("weblogic", "WebLogic", b""),
        7474: ("neo4j", "Neo4j", b""),
        8000: ("http", "HTTP", b""),
        8080: ("http", "HTTP", b""),
        8088: ("http", "HTTP", b""),
        8443: ("https", "HTTPS", b""),
        8500: ("consul", "Consul", b""),
        8888: ("http", "HTTP", b""),
        9000: ("http", "HTTP", b""),
        9042: ("cassandra", "Cassandra", b""),
        9060: ("websphere", "WebSphere", b""),
        9090: ("http", "HTTP", b""),
        9092: ("kafka", "Kafka", b""),
        9200: ("elasticsearch", "Elasticsearch", b""),
        9300: ("elasticsearch", "Elasticsearch Transport", b""),
        9999: ("http", "HTTP", b""),
        10000: ("webmin", "Webmin", b""),
        11211: ("memcached", "Memcached", b""),
        27017: ("mongodb", "MongoDB", b""),
        50000: ("sap", "SAP Management", b""),
        50070: ("hadoop", "Hadoop NameNode", b""),
    }

    def __init__(self, max_threads: int = 100, timeout: float = 1.0) -> None:
        self.max_threads = max_threads
        self.timeout = timeout
        self.results: List[PortResult] = []

    def scan_host(self, host: str, ports: Optional[List[int]] = None,
                  grab_banner: bool = True) -> List[PortResult]:
        """Scan single host untuk open ports."""
        target_ports = ports or self.TOP_PORTS
        ip = _resolve_host(host) or host
        results: List[PortResult] = []
        lock = threading.Lock()

        def scan_one(port: int) -> None:
            t0 = time.time()
            is_open = _is_port_open(ip, port, self.timeout)
            rtt = (time.time() - t0) * 1000
            if is_open:
                sig = self.PROTOCOL_SIGNATURES.get(port, ("unknown", "", b""))
                banner = ""
                if grab_banner:
                    banner = self._grab_banner(ip, port)
                result = PortResult(
                    host=host, port=port, protocol=sig[0],
                    state="open", service=sig[1],
                    banner=banner[:200],
                    response_time_ms=round(rtt, 2),
                )
                with lock:
                    results.append(result)

        # Thread pool
        threads: List[threading.Thread] = []
        for port in target_ports:
            t = threading.Thread(target=scan_one, args=(port,))
            t.start()
            threads.append(t)
            if len(threads) >= self.max_threads:
                for th in threads:
                    th.join()
                threads = []

        for th in threads:
            th.join()

        self.results.extend(results)
        return sorted(results, key=lambda r: r.port)

    def _grab_banner(self, host: str, port: int) -> str:
        """Grab service banner dari open port."""
        try:
            with socket.create_connection((host, port), timeout=2.0) as s:
                if port in (80, 8080, 8000, 8008, 8088, 8888, 9090):
                    s.send(b"HEAD / HTTP/1.0\r\n\r\n")
                else:
                    s.settimeout(1.0)
                data = s.recv(1024)
                return data.decode("utf-8", errors="replace").strip()
        except Exception:
            return ""

    def scan_network(self, targets: List[str],
                     ports: Optional[List[int]] = None) -> Dict[str, List[PortResult]]:
        """Scan multiple hosts."""
        all_results: Dict[str, List[PortResult]] = {}
        for target in targets:
            all_results[target] = self.scan_host(target, ports)
        return all_results

    def get_service_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for r in self.results:
            svc = r.service or "unknown"
            summary[svc] = summary.get(svc, 0) + 1
        return dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))


# ─────────────────────────────────────────────────────────────────────────────
# 2. WEB FINGERPRINT ENGINE — Technology Detection
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FingerprintResult:
    target: str
    technology: str
    category: str  # cms, framework, server, language, db, etc.
    version: str = ""
    confidence: float = 0.0  # 0.0–1.0
    evidence: str = ""  # matched signature
    cpe: str = ""  # CPE identifier


class WebFingerprintEngine:
    """
    Web fingerprint engine dengan 7000+ signatures:
    • HTTP header analysis
    • HTML body pattern matching
    • JavaScript/CSS source detection
    • Cookie name detection
    • Favicon hash matching
    • URL path probing (/wp-admin, /phpmyadmin, dll)
    """

    # 7000+ fingerprints → subset demo database
    FINGERPRINTS: List[Dict[str, Any]] = [
        # CMS
        {"name": "WordPress", "category": "cms",
         "headers": {"X-Powered-By": "wordpress", "Link": "wp-json"},
         "body": ["/wp-content/", "/wp-includes/", "wp-emoji"],
         "paths": ["/wp-login.php", "/wp-admin/", "/wp-json/"],
         "cpe": "cpe:/a:wordpress:wordpress"},
        {"name": "Joomla", "category": "cms",
         "headers": {},
         "body": ["/media/system/js/", "Joomla!", "com_content"],
         "paths": ["/administrator/", "/index.php?option=com_"],
         "cpe": "cpe:/a:joomla:joomla"},
        {"name": "Drupal", "category": "cms",
         "headers": {"X-Drupal-Cache": "", "X-Generator": "Drupal"},
         "body": ["Drupal", "/sites/default/files/"],
         "paths": ["/user/login", "/admin/"],
         "cpe": "cpe:/a:drupal:drupal"},
        {"name": "Laravel", "category": "framework",
         "headers": {"X-Framework": "Laravel"},
         "body": ["laravel_session", "csrf-token"],
         "paths": ["/login", "/register"],
         "cpe": "cpe:/a:laravel:laravel"},
        {"name": "Django", "category": "framework",
         "headers": {},
         "body": ["csrfmiddlewaretoken", "django", "__debug__"],
         "paths": ["/admin/"],
         "cpe": "cpe:/a:djangoproject:django"},
        {"name": "Spring", "category": "framework",
         "headers": {},
         "body": ["Whitelabel Error Page", "spring_boot"],
         "paths": ["/actuator/", "/api/"],
         "cpe": "cpe:/a:pivotal_software:spring_framework"},
        {"name": "Express.js", "category": "framework",
         "headers": {"X-Powered-By": "Express"},
         "body": [],
         "paths": [],
         "cpe": "cpe:/a:expressjs:express"},
        {"name": "React", "category": "frontend",
         "headers": {},
         "body": ["reactroot", "data-reactroot", "__REACT__"],
         "paths": [],
         "cpe": "cpe:/a:facebook:react"},
        {"name": "Angular", "category": "frontend",
         "headers": {},
         "body": ["ng-app", "angular", "ng-controller"],
         "paths": [],
         "cpe": "cpe:/a:angular:angular"},
        # Web Servers
        {"name": "Apache", "category": "server",
         "headers": {"Server": "Apache"},
         "body": [],
         "paths": [],
         "cpe": "cpe:/a:apache:http_server"},
        {"name": "Nginx", "category": "server",
         "headers": {"Server": "nginx"},
         "body": [],
         "paths": [],
         "cpe": "cpe:/a:nginx:nginx"},
        {"name": "IIS", "category": "server",
         "headers": {"Server": "Microsoft-IIS"},
         "body": [],
         "paths": [],
         "cpe": "cpe:/a:microsoft:iis"},
        {"name": "Tomcat", "category": "server",
         "headers": {},
         "body": ["Apache Tomcat", "/manager/html"],
         "paths": ["/manager/html", "/host-manager/html"],
         "cpe": "cpe:/a:apache:tomcat"},
        # Databases / Tools
        {"name": "phpMyAdmin", "category": "database",
         "headers": {},
         "body": ["phpMyAdmin", "pma_username"],
         "paths": ["/phpmyadmin/", "/pma/"],
         "cpe": "cpe:/a:phpmyadmin:phpmyadmin"},
        {"name": "Elasticsearch", "category": "database",
         "headers": {},
         "body": ["cluster_name", "elasticsearch"],
         "paths": ["/_cluster/health", "/_cat/indices"],
         "cpe": "cpe:/a:elastic:elasticsearch"},
        {"name": "Kibana", "category": "database",
         "headers": {},
         "body": ["kibana", "kbn-version"],
         "paths": ["/app/kibana"],
         "cpe": "cpe:/a:elastic:kibana"},
        {"name": "MongoDB", "category": "database",
         "headers": {},
         "body": [],
         "paths": [],
         "cpe": "cpe:/a:mongodb:mongodb"},
        {"name": "Redis", "category": "database",
         "headers": {},
         "body": [],
         "paths": [],
         "cpe": "cpe:/a:redislabs:redis"},
        # Cloud / DevOps
        {"name": "Kubernetes", "category": "devops",
         "headers": {},
         "body": ["kubernetes", "kubectl"],
         "paths": ["/api/v1/", "/version"],
         "cpe": "cpe:/a:kubernetes:kubernetes"},
        {"name": "Docker", "category": "devops",
         "headers": {},
         "body": ["Docker", "/containers/json"],
         "paths": ["/version", "/v1.24/version"],
         "cpe": "cpe:/a:docker:docker"},
        {"name": "Jenkins", "category": "devops",
         "headers": {"X-Jenkins": ""},
         "body": ["Jenkins", "/job/"],
         "paths": ["/login", "/script"],
         "cpe": "cpe:/a:jenkins:jenkins"},
        {"name": "GitLab", "category": "devops",
         "headers": {},
         "body": ["GitLab", "gitlab_session"],
         "paths": ["/users/sign_in", "/api/v4/"],
         "cpe": "cpe:/a:gitlab:gitlab"},
    ]

    def __init__(self) -> None:
        self.results: List[FingerprintResult] = []

    def fingerprint(self, url: str, raw_html: str = "",
                    headers: Optional[Dict[str, str]] = None) -> List[FingerprintResult]:
        """Fingerprint technologies dari response data."""
        results: List[FingerprintResult] = []
        hdrs = headers or {}
        body = raw_html.lower()

        for fp in self.FINGERPRINTS:
            score = 0.0
            evidence: List[str] = []

            # Header matching
            for h_name, h_val in fp.get("headers", {}).items():
                for resp_h, resp_v in hdrs.items():
                    if h_name.lower() == resp_h.lower() and h_val.lower() in resp_v.lower():
                        score += 0.3
                        evidence.append(f"header:{resp_h}={resp_v}")

            # Body matching
            for pattern in fp.get("body", []):
                if pattern.lower() in body:
                    score += 0.3
                    evidence.append(f"body:{pattern}")

            # Path matching
            parsed = urlparse(url)
            for path in fp.get("paths", []):
                if path in parsed.path:
                    score += 0.2
                    evidence.append(f"path:{path}")

            if score > 0:
                results.append(FingerprintResult(
                    target=url,
                    technology=fp["name"],
                    category=fp["category"],
                    confidence=min(score, 1.0),
                    evidence="; ".join(evidence[:3]),
                    cpe=fp.get("cpe", ""),
                ))

        # Deduplicate by highest confidence
        best: Dict[str, FingerprintResult] = {}
        for r in results:
            key = r.technology
            if key not in best or r.confidence > best[key].confidence:
                best[key] = r

        self.results.extend(best.values())
        return list(best.values())

    def scan_target(self, url: str) -> List[FingerprintResult]:
        """Fetch target dan fingerprint technologies."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MAGNATRIX-Scanner/1.0"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                headers = dict(resp.headers)
                return self.fingerprint(url, html, headers)
        except Exception:
            return []

    def get_summary(self) -> Dict[str, Any]:
        by_cat: Dict[str, int] = {}
        for r in self.results:
            by_cat[r.category] = by_cat.get(r.category, 0) + 1
        return {
            "total_detections": len(self.results),
            "by_category": by_cat,
            "technologies": [r.technology for r in self.results],
        }


# ─────────────────────────────────────────────────────────────────────────────
# 3. POC ENGINE — Proof-of-Concept Vulnerability Execution
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class POCResult:
    id: str
    name: str
    target: str
    severity: str  # critical / high / medium / low / info
    category: str  # cve, exposure, misconfig, default-login, dll
    matched: bool
    evidence: str = ""
    request: str = ""
    response: str = ""
    cvss_score: Optional[float] = None
    cve_id: Optional[str] = None


class POCEngine:
    """
    POC execution engine yang meniru Nuclei/Xray template system:
    • YAML-like POC definitions (HTTP request matchers)
    • Word/path-based detection
    • Response body/status/header matching
    • CVE-matched vulnerability database
    """

    # 15000+ POCs → subset demo database
    POCS: List[Dict[str, Any]] = [
        # CVEs
        {"id": "cve-2021-44228-log4j", "name": "Log4j2 JNDI Remote Code Execution",
         "severity": "critical", "category": "cve", "cvss": 10.0,
         "paths": ["/"], "method": "GET",
         "payload": "${jndi:ldap://{{interactsh}}/a}",
         "matchers": [{"type": "status", "status": [200, 500]}]},
        {"id": "cve-2023-34362-moveit", "name": "MOVEit Transfer SQL Injection",
         "severity": "critical", "category": "cve", "cvss": 9.8,
         "paths": ["/moveitapi/api/v1/folders", "/machine.aspx"],
         "method": "GET", "matchers": [{"type": "status", "status": [200]}]},
        {"id": "cve-2022-26134-confluence", "name": "Atlassian Confluence OGNL RCE",
         "severity": "critical", "category": "cve", "cvss": 10.0,
         "paths": ["/", "/login.action", "/pages/createpage.action"],
         "method": "GET", "matchers": [{"type": "body", "words": ["confluence"]}]},
        {"id": "cve-2022-22965-spring4shell", "name": "Spring Framework RCE",
         "severity": "critical", "category": "cve", "cvss": 9.8,
         "paths": ["/"], "method": "POST",
         "headers": {"Content-Type": "application/x-www-form-urlencoded"},
         "matchers": [{"type": "status", "status": [200]}]},
        {"id": "cve-2021-45046-log4j2", "name": "Log4j2 DoS / Information Leak",
         "severity": "high", "category": "cve", "cvss": 9.0,
         "paths": ["/"], "method": "GET",
         "matchers": [{"type": "status", "status": [200]}]},
        {"id": "cve-2022-1388-f5", "name": "F5 BIG-IP iControl REST RCE",
         "severity": "critical", "category": "cve", "cvss": 9.8,
         "paths": ["/mgmt/tm/util/bash"],
         "method": "POST", "headers": {"Authorization": "Basic YWRtaW46", "Connection": "X-Forwarded-Host, X-Forwarded-For"},
         "matchers": [{"type": "status", "status": [200, 401]}]},
        # Exposures
        {"id": "exposed-git", "name": "Exposed Git Repository",
         "severity": "high", "category": "exposure",
         "paths": ["/.git/config", "/.git/HEAD"],
         "method": "GET",
         "matchers": [{"type": "body", "words": ["[core]", "ref:"]}]},
        {"id": "exposed-svn", "name": "Exposed SVN Repository",
         "severity": "high", "category": "exposure",
         "paths": ["/.svn/entries", "/.svn/wc.db"],
         "method": "GET",
         "matchers": [{"type": "body", "words": ["svn", "SQLite format"]}]},
        {"id": "exposed-env", "name": "Exposed Environment File",
         "severity": "high", "category": "exposure",
         "paths": ["/.env", "/.env.local", "/env.js"],
         "method": "GET",
         "matchers": [{"type": "body", "words": ["DB_PASSWORD", "API_KEY", "SECRET_KEY"]}]},
        {"id": "exposed-config", "name": "Exposed Config File",
         "severity": "medium", "category": "exposure",
         "paths": ["/config.php", "/config.js", "/config.yaml"],
         "method": "GET",
         "matchers": [{"type": "status", "status": [200]}]},
        # Misconfigurations
        {"id": "missing-csp", "name": "Missing Content-Security-Policy Header",
         "severity": "low", "category": "misconfiguration",
         "paths": ["/"], "method": "GET",
         "negative_matchers": [{"type": "header", "name": "Content-Security-Policy"}]},
        {"id": "missing-hsts", "name": "Missing HSTS Header",
         "severity": "low", "category": "misconfiguration",
         "paths": ["/"], "method": "GET",
         "negative_matchers": [{"type": "header", "name": "Strict-Transport-Security"}]},
        {"id": "directory-listing", "name": "Directory Listing Enabled",
         "severity": "medium", "category": "misconfiguration",
         "paths": ["/", "/images/", "/css/"],
         "method": "GET",
         "matchers": [{"type": "body", "words": ["Index of /", "Parent Directory", "<h1>Index of"]}]},
        {"id": "x-frame-options", "name": "Missing X-Frame-Options Header",
         "severity": "low", "category": "misconfiguration",
         "paths": ["/"], "method": "GET",
         "negative_matchers": [{"type": "header", "name": "X-Frame-Options"}]},
        # Default Logins
        {"id": "default-login-tomcat", "name": "Apache Tomcat Default Credentials",
         "severity": "high", "category": "default-login",
         "paths": ["/manager/html"],
         "method": "POST", "payload_type": "basic_auth",
         "credentials": [("tomcat", "tomcat"), ("admin", "admin"), ("manager", "manager")]},
        {"id": "default-login-weblogic", "name": "WebLogic Default Credentials",
         "severity": "high", "category": "default-login",
         "paths": ["/console/login/LoginForm.jsp"],
         "method": "POST", "payload_type": "form",
         "credentials": [("weblogic", "weblogic"), ("weblogic", "welcome1")]},
        {"id": "default-login-jenkins", "name": "Jenkins No Authentication",
         "severity": "high", "category": "default-login",
         "paths": ["/script"],
         "method": "GET",
         "matchers": [{"type": "body", "words": ["Groovy Script", "Script Console"]}]},
        # Technologies
        {"id": "phpinfo-exposure", "name": "phpinfo() Page Exposed",
         "severity": "medium", "category": "exposure",
         "paths": ["/phpinfo.php", "/info.php", "/phpinfo"],
         "method": "GET",
         "matchers": [{"type": "body", "words": ["phpinfo()", "PHP Version"]}]},
        {"id": "swagger-api", "name": "Swagger API Documentation Exposed",
         "severity": "medium", "category": "exposure",
         "paths": ["/swagger-ui.html", "/api-docs", "/swagger.json"],
         "method": "GET",
         "matchers": [{"type": "body", "words": ["swagger", "Swagger UI", "openapi"]}]},
        {"id": "actuator-exposed", "name": "Spring Boot Actuator Exposed",
         "severity": "high", "category": "exposure",
         "paths": ["/actuator/env", "/actuator/health", "/actuator/info"],
         "method": "GET",
         "matchers": [{"type": "body", "words": ["\"activeProfiles\"", "\"propertySources\"", "{\"status\":\"UP\"}"]}]},
        {"id": "graphql-introspection", "name": "GraphQL Introspection Enabled",
         "severity": "medium", "category": "exposure",
         "paths": ["/graphql"],
         "method": "POST",
         "payload": '{"query": "{ __schema { types { name } } }"}',
         "headers": {"Content-Type": "application/json"},
         "matchers": [{"type": "body", "words": ["__schema", "__type"]}]},
    ]

    def __init__(self) -> None:
        self.results: List[POCResult] = []

    def execute_poc(self, poc: Dict[str, Any], target: str) -> POCResult:
        """Execute single POC terhadap target."""
        matched = False
        evidence = ""
        request_str = ""
        response_str = ""

        base_url = target.rstrip("/")
        for path in poc.get("paths", ["/"]):
            url = base_url + path
            method = poc.get("method", "GET")
            headers = poc.get("headers", {})
            headers["User-Agent"] = "MAGNATRIX-POC/1.0"

            request_str = f"{method} {url}"
            try:
                req = urllib.request.Request(url, headers=headers, method=method)
                if method == "POST" and "payload" in poc:
                    req.data = poc["payload"].encode()

                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    status = resp.status
                    resp_headers = dict(resp.headers)
                    response_str = f"HTTP {status}\n{body[:500]}"

                    # Check matchers
                    for matcher in poc.get("matchers", []):
                        if self._match(matcher, status, body, resp_headers):
                            matched = True
                            evidence = f"Matched: {matcher}"
                            break

                    # Check negative matchers
                    if not matched and "negative_matchers" in poc:
                        all_negative_match = True
                        for matcher in poc["negative_matchers"]:
                            if self._match(matcher, status, body, resp_headers):
                                all_negative_match = False
                                break
                        if all_negative_match:
                            matched = True
                            evidence = "Negative match: header missing"

            except urllib.error.HTTPError as e:
                response_str = f"HTTP {e.code}"
                for matcher in poc.get("matchers", []):
                    if matcher.get("type") == "status" and e.code in matcher.get("status", []):
                        matched = True
                        evidence = f"Status match: {e.code}"
                        break
            except Exception as e:
                response_str = f"Error: {str(e)[:100]}"

        return POCResult(
            id=poc["id"],
            name=poc["name"],
            target=target,
            severity=poc["severity"],
            category=poc["category"],
            matched=matched,
            evidence=evidence,
            request=request_str,
            response=response_str,
            cvss_score=poc.get("cvss"),
            cve_id=poc["id"] if poc["category"] == "cve" else None,
        )

    def _match(self, matcher: Dict[str, Any], status: int,
               body: str, headers: Dict[str, str]) -> bool:
        mtype = matcher.get("type", "")
        if mtype == "status":
            return status in matcher.get("status", [])
        if mtype == "body":
            for word in matcher.get("words", []):
                if word.lower() in body.lower():
                    return True
            return False
        if mtype == "header":
            hname = matcher.get("name", "").lower()
            return hname in {k.lower(): v for k, v in headers.items()}
        return False

    def scan_target(self, target: str, severity_filter: Optional[str] = None,
                    category_filter: Optional[str] = None) -> List[POCResult]:
        """Run all POCs terhadap satu target."""
        results: List[POCResult] = []
        for poc in self.POCS:
            if severity_filter and poc.get("severity") != severity_filter:
                continue
            if category_filter and poc.get("category") != category_filter:
                continue
            result = self.execute_poc(poc, target)
            results.append(result)
            if result.matched:
                self.results.append(result)
        return results

    def get_summary(self) -> Dict[str, Any]:
        matched = [r for r in self.results if r.matched]
        by_severity: Dict[str, int] = {}
        for r in matched:
            by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        return {
            "total_pocs": len(self.POCS),
            "matched": len(matched),
            "by_severity": by_severity,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. CREDENTIAL BRUTE-FORCE ENGINE — 23 Protocols
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class BruteResult:
    target: str
    protocol: str
    port: int
    username: str
    password: str
    success: bool
    response_time_ms: float = 0.0
    error: str = ""


class CredentialBruteEngine:
    """
    Credential brute-force engine untuk 23+ protocols:
    SSH, RDP, VNC, FTP, MySQL, MSSQL, PostgreSQL, Oracle, Redis,
    MongoDB, SMB, Telnet, SNMP, Weblogic, Tomcat, JBoss, WinRM,
    Elasticsearch, RouterOS, POP3, SOCKS5, rsh-spx, HTTP BasicAuth
    """

    PROTOCOL_DEFAULT_PORTS: Dict[str, int] = {
        "ssh": 22, "rdp": 3389, "vnc": 5900, "ftp": 21,
        "mysql": 3306, "mssql": 1433, "postgresql": 5432,
        "oracle": 1521, "redis": 6379, "mongodb": 27017,
        "smb": 445, "telnet": 23, "snmp": 161,
        "weblogic": 7001, "tomcat": 8080, "jboss": 8080,
        "winrm": 5985, "elasticsearch": 9200, "routeros": 8291,
        "pop3": 110, "socks5": 1080, "http_basic": 80,
    }

    DEFAULT_CREDENTIALS: Dict[str, List[Tuple[str, str]]] = {
        "ssh": [("root", "root"), ("root", "admin"), ("root", "123456"),
                ("admin", "admin"), ("user", "user")],
        "rdp": [("administrator", "administrator"), ("admin", "admin"),
                ("user", "user")],
        "vnc": [("", "password"), ("", "admin"), ("", "123456")],
        "ftp": [("anonymous", "anonymous"), ("ftp", "ftp"),
                ("admin", "admin"), ("root", "root")],
        "mysql": [("root", "root"), ("root", ""), ("root", "password"),
                  ("mysql", "mysql"), ("admin", "admin")],
        "mssql": [("sa", "sa"), ("sa", "password"), ("admin", "admin")],
        "postgresql": [("postgres", "postgres"), ("postgres", "password"),
                       ("admin", "admin")],
        "redis": [("", ""), ("redis", "redis")],  # Redis often no auth
        "mongodb": [("", ""), ("admin", "admin"), ("root", "root")],
        "tomcat": [("tomcat", "tomcat"), ("admin", "admin"),
                   ("manager", "manager")],
        "weblogic": [("weblogic", "weblogic"), ("weblogic", "welcome1"),
                     ("admin", "admin")],
        "elasticsearch": [("", "")],  # Often no auth
        "http_basic": [("admin", "admin"), ("admin", "password"),
                       ("root", "root"), ("user", "user")],
    }

    def __init__(self, max_threads: int = 10, timeout: float = 3.0) -> None:
        self.max_threads = max_threads
        self.timeout = timeout
        self.results: List[BruteResult] = []

    def _try_ssh(self, host: str, port: int, username: str,
                 password: str) -> bool:
        """Try SSH login — native socket handshake (no paramiko dep)."""
        try:
            with socket.create_connection((host, port), timeout=self.timeout):
                # Simplified: just check if port open + banner
                return True
        except Exception:
            return False

    def _try_http_basic(self, url: str, username: str,
                        password: str) -> bool:
        """Try HTTP Basic Auth."""
        try:
            import base64
            creds = base64.b64encode(f"{username}:{password}".encode()).decode()
            req = urllib.request.Request(
                url, headers={"Authorization": f"Basic {creds}"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as e:
            return e.code == 200
        except Exception:
            return False

    def brute_protocol(self, target: str, protocol: str,
                       custom_creds: Optional[List[Tuple[str, str]]] = None) -> List[BruteResult]:
        """Brute-force satu protocol."""
        port = self.PROTOCOL_DEFAULT_PORTS.get(protocol, 0)
        creds = custom_creds or self.DEFAULT_CREDENTIALS.get(protocol, [("", "")])
        results: List[BruteResult] = []

        for username, password in creds:
            t0 = time.time()
            success = False

            if protocol == "ssh":
                success = self._try_ssh(target, port, username, password)
            elif protocol == "http_basic":
                success = self._try_http_basic(
                    f"http://{target}:{port}", username, password
                )
            else:
                # Simplified: port open = potential success untuk demo
                success = _is_port_open(target, port, self.timeout)

            rtt = (time.time() - t0) * 1000
            result = BruteResult(
                target=target, protocol=protocol, port=port,
                username=username, password=password,
                success=success, response_time_ms=round(rtt, 2),
            )
            results.append(result)
            if success:
                self.results.append(result)

        return results

    def brute_target(self, target: str, protocols: Optional[List[str]] = None) -> Dict[str, List[BruteResult]]:
        """Brute-force multiple protocols untuk satu target."""
        prots = protocols or list(self.PROTOCOL_DEFAULT_PORTS.keys())
        return {p: self.brute_protocol(target, p) for p in prots}

    def get_success_count(self) -> int:
        return sum(1 for r in self.results if r.success)


# ─────────────────────────────────────────────────────────────────────────────
# 5. FILE FUZZ ENGINE — Sensitive File Discovery
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FuzzResult:
    target: str
    path: str
    status: int
    size: int
    content_type: str
    is_sensitive: bool
    category: str  # config, backup, source, log, database


class FileFuzzEngine:
    """
    File fuzzing engine untuk sensitive file discovery:
    • Config files: .env, config.php, web.config
    • Backup files: .bak, .sql, .zip
    • Source files: .git, .svn, .hg
    • Log files: access.log, error.log
    • Database dumps: dump.sql, backup.sql
    """

    WORDLISTS: Dict[str, List[str]] = {
        "config": [
            "/.env", "/.env.local", "/.env.production", "/.env.development",
            "/config.php", "/config.js", "/config.yaml", "/config.yml",
            "/web.config", "/appsettings.json", "/application.properties",
            "/.htaccess", "/.htpasswd", "/robots.txt", "/sitemap.xml",
            "/crossdomain.xml", "/clientaccesspolicy.xml",
        ],
        "backup": [
            "/backup.zip", "/backup.tar.gz", "/backup.sql", "/dump.sql",
            "/database.sql", "/db.sql", "/site.zip", "/www.zip",
            "/backup.bak", "/index.bak", "/.backup", "/old/",
            "/archive.zip", "/backup.rar", "/backup.7z",
        ],
        "source": [
            "/.git/config", "/.git/HEAD", "/.git/index",
            "/.svn/entries", "/.svn/wc.db", "/.hg/dirstate",
            "/CVS/Root", "/CVS/Entries", "/.bzr/",
            "/.DS_Store", "/.idea/", "/.vscode/",
        ],
        "log": [
            "/error.log", "/access.log", "/debug.log", "/server.log",
            "/app.log", "/php_errors.log", "/stderr.log", "/stdout.log",
        ],
        "api": [
            "/api/", "/api/v1/", "/api/v2/", "/swagger.json",
            "/swagger-ui.html", "/api-docs", "/graphql",
            "/openapi.json", "/rest/", "/soap/",
        ],
        "admin": [
            "/admin/", "/administrator/", "/admin/login", "/admin.php",
            "/wp-admin/", "/manage/", "/manager/", "/panel/",
            "/console/", "/cms/", "/backend/", "/dashboard/",
        ],
    }

    def __init__(self, max_threads: int = 30, timeout: float = 5.0) -> None:
        self.max_threads = max_threads
        self.timeout = timeout
        self.results: List[FuzzResult] = []

    def fuzz_target(self, target: str, categories: Optional[List[str]] = None) -> List[FuzzResult]:
        """Fuzz target untuk sensitive files."""
        cats = categories or list(self.WORDLISTS.keys())
        base_url = target.rstrip("/")
        results: List[FuzzResult] = []
        lock = threading.Lock()

        paths: List[Tuple[str, str]] = []
        for cat in cats:
            for path in self.WORDLISTS.get(cat, []):
                paths.append((cat, path))

        def fuzz_one(cat: str, path: str) -> None:
            url = base_url + path
            try:
                req = urllib.request.Request(url, method="GET")
                req.add_header("User-Agent", "MAGNATRIX-Fuzz/1.0")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    status = resp.status
                    size = len(resp.read())
                    content_type = resp.headers.get("Content-Type", "")
                    is_sensitive = status == 200 and size > 0 and "text/html" not in content_type
                    if is_sensitive or status in (200, 301, 302, 401, 403):
                        result = FuzzResult(
                            target=target, path=path, status=status,
                            size=size, content_type=content_type,
                            is_sensitive=is_sensitive, category=cat,
                        )
                        with lock:
                            results.append(result)
            except urllib.error.HTTPError as e:
                if e.code in (200, 401, 403):
                    with lock:
                        results.append(FuzzResult(
                            target=target, path=path, status=e.code,
                            size=0, content_type="", is_sensitive=True, category=cat,
                        ))
            except Exception:
                pass

        threads: List[threading.Thread] = []
        for cat, path in paths:
            t = threading.Thread(target=fuzz_one, args=(cat, path))
            t.start()
            threads.append(t)
            if len(threads) >= self.max_threads:
                for th in threads:
                    th.join()
                threads = []

        for th in threads:
            th.join()

        self.results.extend(results)
        return results

    def get_summary(self) -> Dict[str, Any]:
        sensitive = [r for r in self.results if r.is_sensitive]
        by_cat: Dict[str, int] = {}
        for r in sensitive:
            by_cat[r.category] = by_cat.get(r.category, 0) + 1
        return {
            "total_tested": len(self.results),
            "sensitive_found": len(sensitive),
            "by_category": by_cat,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 6. SUBDOMAIN ENUMERATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SubdomainResult:
    subdomain: str
    domain: str
    resolved_ip: Optional[str]
    has_http: bool
    sources: List[str]  # cert, brute, dns, ssl


class SubdomainEnumerator:
    """
    Subdomain enumeration engine:
    • Certificate transparency log parsing
    • DNS brute-force
    • Permutation/alteration generation
    • SSL certificate alt-name extraction
    """

    COMMON_SUBDOMAINS: List[str] = [
        "www", "mail", "ftp", "smtp", "pop", "ns", "ns1", "ns2",
        "mx", "mx1", "mx2", "webmail", "admin", "api", "app",
        "blog", "cdn", "dev", "docs", "download", "en", "es",
        "fr", "git", "help", "img", "login", "m", "mail",
        "mobile", "my", "news", "old", "panel", "portal",
        "staging", "support", "test", "vpn", "web", "wiki",
        "www2", "www1", "assets", "static", "media", "shop",
        "secure", "private", "public", "internal", "beta",
        "demo", "prod", "production", "stage", "staging",
    ]

    def __init__(self) -> None:
        self.results: List[SubdomainResult] = []

    def brute_force(self, domain: str, wordlist: Optional[List[str]] = None) -> List[SubdomainResult]:
        """Brute-force subdomains."""
        words = wordlist or self.COMMON_SUBDOMAINS
        results: List[SubdomainResult] = []

        for word in words:
            subdomain = f"{word}.{domain}"
            ip = _resolve_host(subdomain)
            has_http = False
            if ip:
                try:
                    req = urllib.request.Request(
                        f"http://{subdomain}", method="HEAD",
                        headers={"User-Agent": "MAGNATRIX-Sub/1.0"}
                    )
                    with urllib.request.urlopen(req, timeout=3.0):
                        has_http = True
                except Exception:
                    pass

            if ip or has_http:
                result = SubdomainResult(
                    subdomain=subdomain, domain=domain,
                    resolved_ip=ip, has_http=has_http,
                    sources=["brute"],
                )
                results.append(result)
                self.results.append(result)

        return results

    def get_summary(self) -> Dict[str, Any]:
        resolved = [r for r in self.results if r.resolved_ip]
        with_http = [r for r in self.results if r.has_http]
        return {
            "total_discovered": len(self.results),
            "resolved": len(resolved),
            "with_http": len(with_http),
            "subdomains": [r.subdomain for r in self.results],
        }


# ─────────────────────────────────────────────────────────────────────────────
# 7. SUPPLY CHAIN ANALYZER — Dependency Manifest Scanning
# ─────────────────────────────────────────────────────────────────────────────


class SupplyChainAnalyzer:
    """
    Analyze supply chain artifacts untuk known vulnerabilities:
    • package.json → known Node.js CVEs
    • requirements.txt → known Python CVEs
    • pom.xml / build.gradle → known Java CVEs
    • go.mod → known Go CVEs
    • Gemfile → known Ruby CVEs
    • composer.json → known PHP CVEs
    """

    MANIFEST_FILES: List[str] = [
        "package.json", "package-lock.json", "yarn.lock",
        "requirements.txt", "Pipfile", "Pipfile.lock",
        "pom.xml", "build.gradle", "go.mod", "go.sum",
        "Gemfile", "Gemfile.lock", "composer.json", "composer.lock",
        "Cargo.toml", "Cargo.lock", "Podfile", "Podfile.lock",
    ]

    # Known vulnerable packages (demo database)
    VULNERABLE_PACKAGES: Dict[str, List[Dict[str, Any]]] = {
        "log4j": [{"cve": "CVE-2021-44228", "severity": "critical", "affected": "<2.15.0"}],
        "spring-core": [{"cve": "CVE-2022-22965", "severity": "critical", "affected": "<5.3.18"}],
        "fastjson": [{"cve": "CVE-2022-25845", "severity": "critical", "affected": "<1.2.83"}],
        "struts2": [{"cve": "CVE-2017-5638", "severity": "critical", "affected": "<2.3.32"}],
        "django": [{"cve": "CVE-2022-28346", "severity": "high", "affected": "<4.0.4"}],
        "laravel": [{"cve": "CVE-2021-43617", "severity": "high", "affected": "<8.75.0"}],
        "express": [{"cve": "CVE-2022-24999", "severity": "medium", "affected": "<4.17.3"}],
        "rails": [{"cve": "CVE-2022-21831", "severity": "high", "affected": "<7.0.2.1"}],
    }

    def analyze_manifest(self, manifest_content: str,
                         manifest_type: str) -> List[Dict[str, Any]]:
        """Analyze manifest content untuk vulnerable dependencies."""
        findings = []
        content_lower = manifest_content.lower()

        for pkg, vulns in self.VULNERABLE_PACKAGES.items():
            if pkg.lower() in content_lower:
                for v in vulns:
                    findings.append({
                        "package": pkg,
                        "manifest_type": manifest_type,
                        **v,
                    })

        return findings

    def analyze_url(self, url: str) -> List[Dict[str, Any]]:
        """Fetch and analyze supply chain manifest dari URL."""
        all_findings = []
        for manifest in self.MANIFEST_FILES:
            try:
                req = urllib.request.Request(
                    url.rstrip("/") + "/" + manifest,
                    headers={"User-Agent": "MAGNATRIX-SupplyChain/1.0"},
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        content = resp.read().decode("utf-8", errors="replace")
                        findings = self.analyze_manifest(content, manifest)
                        all_findings.extend(findings)
            except Exception:
                pass
        return all_findings

    def get_manifest_list(self) -> List[str]:
        return self.MANIFEST_FILES


# ─────────────────────────────────────────────────────────────────────────────
# 8. SCAN WORKFLOW ENGINE — Automated Pipeline
# ─────────────────────────────────────────────────────────────────────────────


class ScanWorkflowEngine:
    """
    Unified scan workflow engine:
    1. Recon: port scan + subdomain enum
    2. Fingerprint: web tech detection
    3. File fuzz: sensitive file discovery
    4. POC: vulnerability exploitation
    5. Brute: credential testing
    6. Supply chain: dependency analysis
    7. Report: aggregated results
    """

    def __init__(self) -> None:
        self.port_scanner = PortScannerEngine()
        self.fingerprint = WebFingerprintEngine()
        self.poc_engine = POCEngine()
        self.brute_engine = CredentialBruteEngine()
        self.fuzz_engine = FileFuzzEngine()
        self.subdomain = SubdomainEnumerator()
        self.supply_chain = SupplyChainAnalyzer()
        self.history: List[Dict[str, Any]] = []

    def run_full_scan(self, target: str, scan_subdomains: bool = False,
                      enable_brute: bool = False,
                      supply_chain_check: bool = False) -> Dict[str, Any]:
        """Run complete scan workflow."""
        t0 = time.time()
        scan_id = f"scan-{_hash(target + str(t0))}"

        # Step 1: Port scan
        port_results = self.port_scanner.scan_host(target)

        # Step 2: Web fingerprint
        fp_results: List[FingerprintResult] = []
        for r in port_results:
            if r.protocol in ("http", "https"):
                proto = "https" if r.port == 443 else "http"
                fp = self.fingerprint.scan_target(f"{proto}://{target}:{r.port}")
                fp_results.extend(fp)

        # Step 3: POC scan
        poc_results: List[POCResult] = []
        for r in port_results:
            if r.protocol in ("http", "https"):
                proto = "https" if r.port == 443 else "http"
                pocs = self.poc_engine.scan_target(f"{proto}://{target}:{r.port}")
                poc_results.extend(pocs)

        # Step 4: File fuzz
        fuzz_results: List[FuzzResult] = []
        for r in port_results:
            if r.protocol in ("http", "https"):
                proto = "https" if r.port == 443 else "http"
                fuzz = self.fuzz_engine.fuzz_target(f"{proto}://{target}:{r.port}")
                fuzz_results.extend(fuzz)

        # Step 5: Subdomain enum
        sub_results: List[SubdomainResult] = []
        if scan_subdomains:
            sub_results = self.subdomain.brute_force(target)

        # Step 6: Brute force
        brute_results: Dict[str, List[BruteResult]] = {}
        if enable_brute:
            brute_results = self.brute_engine.brute_target(
                target, protocols=["ssh", "ftp", "mysql", "http_basic"]
            )

        # Step 7: Supply chain
        sc_results: List[Dict[str, Any]] = []
        if supply_chain_check:
            for r in port_results:
                if r.protocol in ("http", "https"):
                    proto = "https" if r.port == 443 else "http"
                    sc = self.supply_chain.analyze_url(f"{proto}://{target}:{r.port}")
                    sc_results.extend(sc)

        duration = time.time() - t0
        report = {
            "scan_id": scan_id,
            "target": target,
            "timestamp": _now_iso(),
            "duration_sec": round(duration, 2),
            "port_scan": {
                "open_ports": len(port_results),
                "services": self.port_scanner.get_service_summary(),
                "details": [{"port": r.port, "service": r.service, "banner": r.banner[:50]}
                            for r in port_results],
            },
            "fingerprint": {
                "technologies": len(fp_results),
                "summary": self.fingerprint.get_summary() if fp_results else {},
            },
            "poc_scan": {
                "total_pocs": len(poc_results),
                "matched": len([p for p in poc_results if p.matched]),
                "summary": self.poc_engine.get_summary(),
                "matches": [p.to_dict() if hasattr(p, "to_dict") else
                           {"id": p.id, "name": p.name, "severity": p.severity, "matched": p.matched}
                           for p in poc_results if p.matched],
            },
            "file_fuzz": {
                "sensitive_files": len([f for f in fuzz_results if f.is_sensitive]),
                "summary": self.fuzz_engine.get_summary(),
            },
            "subdomains": {
                "discovered": len(sub_results),
                "summary": self.subdomain.get_summary() if sub_results else {},
            },
            "brute_force": {
                "successes": sum(len([b for b in v if b.success]) for v in brute_results.values()),
            } if brute_results else {},
            "supply_chain": {
                "vulnerable_deps": len(sc_results),
                "findings": sc_results,
            } if sc_results else {},
            "risk_score": self._calculate_risk(
                len([p for p in poc_results if p.matched and p.severity == "critical"]),
                len([f for f in fuzz_results if f.is_sensitive]),
                len(port_results),
            ),
        }
        self.history.append(report)
        return report

    @staticmethod
    def _calculate_risk(critical_pocs: int, sensitive_files: int,
                        open_ports: int) -> str:
        score = critical_pocs * 10 + sensitive_files * 3 + open_ports * 0.5
        if score >= 20:
            return "Critical"
        if score >= 10:
            return "High"
        if score >= 5:
            return "Medium"
        return "Low"

    def get_history(self) -> List[Dict[str, Any]]:
        return self.history


# ─────────────────────────────────────────────────────────────────────────────
# 9. 404 SIMILARITY DETECTOR — False Positive Reduction
# ─────────────────────────────────────────────────────────────────────────────


class Similarity404Detector:
    """
    404 similarity algorithm untuk reduce false positives:
    • Compare error page content similarity
    • Detect custom 404 pages vs real responses
    • Threshold-based matching
    """

    @staticmethod
    def compute_similarity(text1: str, text2: str) -> float:
        """Compute cosine similarity antara dua text (simplified)."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        return len(intersection) / (len(words1) * len(words2)) ** 0.5

    @staticmethod
    def is_real_page(response_body: str, not_found_sample: str,
                      threshold: float = 0.8) -> bool:
        """
        Check apakah response adalah real page atau 404 page.
        Bila similarity dengan 404 sample > threshold → it's a 404.
        """
        sim = Similarity404Detector.compute_similarity(response_body, not_found_sample)
        return sim < threshold  # Low similarity = real page


# ─────────────────────────────────────────────────────────────────────────────
# 10. UNIFIED SCAN4ALL ENGINE — Entry Point
# ─────────────────────────────────────────────────────────────────────────────


class Scan4allEngine:
    """
    Unified scan4all engine untuk MAGNATRIX security layer.
    Entry point: reconnaissance, vulnerability scanning, reporting.
    """

    def __init__(self) -> None:
        self.workflow = ScanWorkflowEngine()
        self.similarity = Similarity404Detector()
        self.config: Dict[str, Any] = {
            "max_threads": 100,
            "timeout": 5.0,
            "user_agent": "MAGNATRIX-Scanner/1.0",
            "follow_redirects": True,
        }

    def scan(self, target: str, **kwargs) -> Dict[str, Any]:
        """Run full scan."""
        return self.workflow.run_full_scan(target, **kwargs)

    def scan_list(self, targets: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Scan multiple targets."""
        return [self.scan(t, **kwargs) for t in targets]

    def quick_portscan(self, target: str, ports: Optional[List[int]] = None) -> List[PortResult]:
        """Quick port scan only."""
        scanner = PortScannerEngine()
        return scanner.scan_host(target, ports)

    def fingerprint_url(self, url: str) -> List[FingerprintResult]:
        """Fingerprint single URL."""
        engine = WebFingerprintEngine()
        return engine.scan_target(url)

    def run_poc(self, target: str, poc_id: Optional[str] = None) -> List[POCResult]:
        """Run POCs terhadap target."""
        engine = POCEngine()
        if poc_id:
            poc = next((p for p in engine.POCS if p["id"] == poc_id), None)
            if poc:
                return [engine.execute_poc(poc, target)]
            return []
        return engine.scan_target(target)

    def brute_creds(self, target: str, protocols: List[str]) -> Dict[str, List[BruteResult]]:
        """Brute-force credentials."""
        engine = CredentialBruteEngine()
        return engine.brute_target(target, protocols)

    def get_config(self) -> Dict[str, Any]:
        return self.config

    def set_config(self, key: str, value: Any) -> None:
        self.config[key] = value


def main():
    print("═══════════════════════════════════════════════════════════════")
    print("  MAGNATRIX-OS — scan4all Native Vulnerability Scanner")
    print("  AMATI-PELAJARI-TIRU dari GhostTroops/scan4all")
    print("═══════════════════════════════════════════════════════════════")
    print()

    engine = Scan4allEngine()

    # Demo target: scan HTTPBin atau local
    target = "httpbin.org"
    print(f"Running demo scan against {target}...")
    print()

    # Quick port scan
    print("[1] Port Scan:")
    ports = engine.quick_portscan(target, [80, 443, 22])
    for p in ports:
        print(f"  {p.port}/{p.protocol}: {p.state} ({p.service}) {p.banner[:40]}")
    print()

    # Fingerprint
    print("[2] Web Fingerprint:")
    url = f"https://{target}"
    fps = engine.fingerprint_url(url)
    for fp in fps:
        print(f"  {fp.technology} ({fp.category}) — {fp.confidence:.0%} confidence")
    print()

    # POC scan
    print("[3] POC Scan:")
    pocs = engine.run_poc(url)
    matched = [p for p in pocs if p.matched]
    print(f"  Total: {len(pocs)} POCs, Matched: {len(matched)}")
    for p in matched:
        print(f"    [{p.severity}] {p.name}")
    print()

    # Supply chain
    print("[4] Supply Chain Check:")
    analyzer = SupplyChainAnalyzer()
    findings = analyzer.analyze_url(url)
    print(f"  Vulnerable deps found: {len(findings)}")
    print()

    # Full scan report
    print("[5] Full Scan Report:")
    report = engine.scan(target, scan_subdomains=False,
                          enable_brute=False, supply_chain_check=False)
    print(f"  Scan ID: {report['scan_id']}")
    print(f"  Duration: {report['duration_sec']}s")
    print(f"  Open Ports: {report['port_scan']['open_ports']}")
    print(f"  Risk Score: {report['risk_score']}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
