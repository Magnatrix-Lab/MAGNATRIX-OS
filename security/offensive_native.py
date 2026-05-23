"""
offensive_native.py — MAGNATRIX Security Offensive Layer (Layer 13)
Native pure-Python implementation. No external dependencies.

Architecture references:
  - MITRE ATT&CK framework for attack taxonomy
  - Cobalt Strike / Sliver C2 patterns
  - Metasploit modular exploit framework
  - OSINT tools: theHarvester, Shodan API patterns
  - Nmap port scanning logic

Style: modular, fully typed, simulation-safe (no real network harm).
"""
from __future__ import annotations

import hashlib
import json
import random
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Set, Optional, Callable, Any, Tuple
from collections import defaultdict

# ──────────────────────────────────────────────────────────────
# 0. Types & Constants
# ──────────────────────────────────────────────────────────────

TargetID = str
ExploitID = str
SessionID = str
IOC = str          # Indicator of Compromise

DEFAULT_BEACON_INTERVAL = 30.0
JITTER_MAX = 0.3    # 30% jitter on beacon timing


# ──────────────────────────────────────────────────────────────
# 1. Target & Recon Data Structures
# ──────────────────────────────────────────────────────────────

class TargetStatus(Enum):
    UNKNOWN = auto()
    DISCOVERED = auto()
    SCANNED = auto()
    EXPLOITED = auto()
    COMPROMISED = auto()
    PIVOTED = auto()
    CLEANED = auto()


@dataclass
class Target:
    """Reconnaissance target descriptor."""
    target_id: TargetID
    host: str
    ports: Dict[int, str] = field(default_factory=dict)      # port → service
    os_hint: str = "unknown"
    services: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)
    status: TargetStatus = TargetStatus.UNKNOWN
    compromise_depth: int = 0          # lateral movement hops from entry
    notes: List[str] = field(default_factory=list)
    discovered_at: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return (f"<Target {self.target_id[:8]} {self.host} "
                f"ports={len(self.ports)} status={self.status.name}>")


@dataclass
class ScanResult:
    """Port scan / service enumeration result."""
    target_id: TargetID
    scan_type: str
    open_ports: Dict[int, str]
    os_guess: str
    timestamp: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return f"<ScanResult {self.target_id[:8]} {self.scan_type} open={len(self.open_ports)}>"


# ──────────────────────────────────────────────────────────────
# 2. Reconnaissance Engine
# ──────────────────────────────────────────────────────────────

class ReconEngine:
    """Automated recon: port scan, service enum, OSINT stub."""

    COMMON_PORTS = {
        21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
        53: "dns", 80: "http", 110: "pop3", 143: "imap",
        443: "https", 445: "smb", 3306: "mysql", 3389: "rdp",
        5432: "postgresql", 6379: "redis", 8080: "http-alt",
        8443: "https-alt", 9200: "elasticsearch", 27017: "mongodb",
    }

    def __init__(self) -> None:
        self.targets: Dict[TargetID, Target] = {}
        self.scan_history: List[ScanResult] = []

    def add_target(self, host: str, target_id: Optional[TargetID] = None) -> Target:
        tid = target_id or secrets.token_hex(16)
        target = Target(target_id=tid, host=host)
        self.targets[tid] = target
        return target

    def port_scan(self, target_id: TargetID, port_range: Tuple[int, int] = (1, 1024),
                  scan_type: str = "syn") -> ScanResult:
        """Simulated port scan — returns plausible open ports."""
        target = self.targets.get(target_id)
        if not target:
            raise ValueError(f"Target {target_id} not found")

        # deterministic but varied based on host hash
        seed = int(hashlib.sha256(target.host.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        open_ports: Dict[int, str] = {}
        for port in range(port_range[0], port_range[1] + 1):
            if port in self.COMMON_PORTS:
                # common ports have higher chance
                if rng.random() < 0.3:
                    open_ports[port] = self.COMMON_PORTS[port]
            else:
                if rng.random() < 0.02:
                    open_ports[port] = "unknown"

        # OS fingerprinting stub
        os_options = ["Linux 5.x", "Windows Server 2019", "Windows 10", "Ubuntu 22.04", "FreeBSD"]
        os_guess = rng.choice(os_options)

        target.ports = open_ports
        target.services = list(open_ports.values())
        target.os_hint = os_guess
        target.status = TargetStatus.SCANNED

        result = ScanResult(
            target_id=target_id,
            scan_type=scan_type,
            open_ports=open_ports,
            os_guess=os_guess,
        )
        self.scan_history.append(result)
        return result

    def service_enum(self, target_id: TargetID) -> List[str]:
        """Enumerate service versions and banners."""
        target = self.targets.get(target_id)
        if not target:
            return []

        banners = []
        for port, service in target.ports.items():
            version = f"{service}/{random.randint(1, 9)}.{random.randint(0, 9)}"
            banner = f"{port}/{service} {version}"
            banners.append(banner)
            # simulate CVE detection
            if service in ["ssh", "http", "smb"] and random.random() < 0.2:
                cve = f"CVE-202{random.randint(0, 4)}-{random.randint(1000, 99999)}"
                target.vulnerabilities.append(cve)
                banners.append(f"  [!] {cve}")

        target.notes.extend(banners)
        return banners

    def osint_stub(self, domain: str) -> dict:
        """Simulated OSINT harvest — subdomains, emails, tech stack."""
        seed = int(hashlib.sha256(domain.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        subdomains = [f"{s}.{domain}" for s in ["www", "api", "mail", "cdn", "dev"] if rng.random() < 0.6]
        emails = [f"admin@{domain}", f"support@{domain}"] if rng.random() < 0.5 else []
        tech = [t for t in ["nginx", "cloudflare", "aws", "django", "react"] if rng.random() < 0.4]

        return {
            "domain": domain,
            "subdomains": subdomains,
            "emails": emails,
            "tech_stack": tech,
            "timestamp": time.time(),
        }

    def __repr__(self) -> str:
        return f"<ReconEngine targets={len(self.targets)} scans={len(self.scan_history)}>"


# ──────────────────────────────────────────────────────────────
# 3. Exploit Framework
# ──────────────────────────────────────────────────────────────

class ExploitType(Enum):
    REMOTE = auto()
    LOCAL = auto()
    CLIENT_SIDE = auto()
    PRIVILEGE_ESCALATION = auto()


@dataclass
class Exploit:
    """Modular exploit module descriptor."""
    exploit_id: ExploitID
    name: str
    exploit_type: ExploitType
    target_services: List[str]
    cve_list: List[str]
    success_rate: float = 0.5
    payload_required: bool = True
    post_modules: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<Exploit {self.exploit_id[:8]} {self.name} {self.exploit_type.name} rate={self.success_rate:.0%}>"


@dataclass
class Payload:
    """Generated payload for delivery."""
    payload_id: str
    payload_type: str          # "reverse_shell", "bind_shell", "execute", "download"
    target_os: str
    data: bytes
    encoder: Optional[str] = None
    badchars: List[int] = field(default_factory=list)

    def encode(self, encoder_name: str) -> "Payload":
        """Apply encoding stub (XOR, base64, etc.)."""
        if encoder_name == "xor":
            key = random.randint(1, 255)
            encoded = bytes(b ^ key for b in self.data)
            return Payload(
                payload_id=self.payload_id,
                payload_type=self.payload_type,
                target_os=self.target_os,
                data=encoded,
                encoder=f"xor:{key}",
            )
        elif encoder_name == "b64":
            import base64
            return Payload(
                payload_id=self.payload_id,
                payload_type=self.payload_type,
                target_os=self.target_os,
                data=base64.b64encode(self.data),
                encoder="base64",
            )
        return self

    def __repr__(self) -> str:
        return f"<Payload {self.payload_id[:8]} {self.payload_type} {len(self.data)}b encoder={self.encoder}>"


class ExploitFramework:
    """Modular exploit loader, matcher, and execution simulator."""

    def __init__(self) -> None:
        self.exploits: Dict[ExploitID, Exploit] = {}
        self.payloads: Dict[str, Payload] = {}
        self.exploit_log: List[dict] = []

    def register_exploit(self, exploit: Exploit) -> None:
        self.exploits[exploit.exploit_id] = exploit

    def match_exploits(self, target: Target) -> List[Exploit]:
        """Find applicable exploits based on target services and CVEs."""
        matches = []
        for exploit in self.exploits.values():
            # match by service
            if any(svc in target.services for svc in exploit.target_services):
                matches.append(exploit)
            # match by CVE
            elif any(cve in target.vulnerabilities for cve in exploit.cve_list):
                matches.append(exploit)
        # sort by success rate
        return sorted(matches, key=lambda e: e.success_rate, reverse=True)

    def generate_payload(self, payload_type: str, target_os: str, size: int = 512) -> Payload:
        """Generate a simulated payload shellcode."""
        data = bytes(random.randint(0, 255) for _ in range(size))
        payload = Payload(
            payload_id=secrets.token_hex(8),
            payload_type=payload_type,
            target_os=target_os,
            data=data,
        )
        self.payloads[payload.payload_id] = payload
        return payload

    def execute_exploit(self, exploit_id: ExploitID, target_id: TargetID,
                        payload: Optional[Payload] = None) -> dict:
        """Simulate exploit execution against target."""
        exploit = self.exploits.get(exploit_id)
        if not exploit:
            return {"status": "error", "reason": "exploit_not_found"}

        # simulate success based on rate
        success = random.random() < exploit.success_rate
        result = {
            "exploit_id": exploit_id,
            "target_id": target_id,
            "success": success,
            "timestamp": time.time(),
            "payload_used": payload.payload_id if payload else None,
        }

        if success:
            result["session_established"] = True
            result["privilege"] = "user" if exploit.exploit_type != ExploitType.PRIVILEGE_ESCALATION else "system"
        else:
            result["session_established"] = False
            result["detection_risk"] = random.random()

        self.exploit_log.append(result)
        return result

    def __repr__(self) -> str:
        return f"<ExploitFramework exploits={len(self.exploits)} payloads={len(self.payloads)}>"


# ──────────────────────────────────────────────────────────────
# 4. C2 Simulation (Command & Control)
# ──────────────────────────────────────────────────────────────

class C2Session:
    """Individual compromised host session."""

    def __init__(self, session_id: SessionID, target_id: TargetID, privilege: str = "user") -> None:
        self.session_id = session_id
        self.target_id = target_id
        self.privilege = privilege
        self.created_at = time.time()
        self.last_beacon = time.time()
        self.command_queue: List[str] = []
        self.results: List[dict] = []
        self.active = True

    def beacon(self) -> dict:
        """Simulate beacon check-in."""
        self.last_beacon = time.time()
        cmds = list(self.command_queue)
        self.command_queue.clear()
        return {
            "session_id": self.session_id,
            "timestamp": self.last_beacon,
            "commands": cmds,
            "privilege": self.privilege,
        }

    def execute(self, command: str) -> dict:
        """Simulate command execution."""
        result = {
            "command": command,
            "output": f"[simulated] executed: {command}",
            "exit_code": 0,
            "timestamp": time.time(),
        }
        self.results.append(result)
        return result

    def __repr__(self) -> str:
        return f"<C2Session {self.session_id[:8]} {self.target_id[:8]} priv={self.privilege}>"


class C2Server:
    """Command & Control server simulation with beaconing."""

    def __init__(self, server_id: str = "c2-main") -> None:
        self.server_id = server_id
        self.sessions: Dict[SessionID, C2Session] = {}
        self.listeners: Dict[str, dict] = {}     # protocol → config
        self.beacon_log: List[dict] = []

    def add_listener(self, protocol: str, host: str, port: int) -> None:
        self.listeners[protocol] = {"host": host, "port": port, "active": True}

    def register_session(self, target_id: TargetID, privilege: str = "user") -> C2Session:
        sid = secrets.token_hex(16)
        session = C2Session(sid, target_id, privilege)
        self.sessions[sid] = session
        return session

    def send_command(self, session_id: SessionID, command: str) -> bool:
        session = self.sessions.get(session_id)
        if not session or not session.active:
            return False
        session.command_queue.append(command)
        return True

    def collect_beacon(self, session_id: SessionID) -> Optional[dict]:
        session = self.sessions.get(session_id)
        if not session:
            return None
        beacon = session.beacon()
        self.beacon_log.append(beacon)
        return beacon

    def kill_session(self, session_id: SessionID) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.active = False
            return True
        return False

    def __repr__(self) -> str:
        active = sum(1 for s in self.sessions.values() if s.active)
        return f"<C2Server {self.server_id} sessions={active}/{len(self.sessions)}>"


# ──────────────────────────────────────────────────────────────
# 5. Pivot Engine (Lateral Movement)
# ──────────────────────────────────────────────────────────────

class PivotEngine:
    """Simulate lateral movement between compromised hosts."""

    def __init__(self, c2: C2Server) -> None:
        self.c2 = c2
        self.pivot_graph: Dict[SessionID, List[SessionID]] = defaultdict(list)
        self.pivot_log: List[dict] = []

    def discover_neighbors(self, session_id: SessionID) -> List[TargetID]:
        """Simulate network discovery from compromised host."""
        # generate fake neighbor IPs
        neighbors = [f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}" for _ in range(random.randint(2, 8))]
        return neighbors

    def attempt_pivot(self, from_session: SessionID, to_target: TargetID,
                      exploit_framework: ExploitFramework) -> Optional[C2Session]:
        """Try to move from one session to a new target."""
        from_sess = self.c2.sessions.get(from_session)
        if not from_sess or not from_sess.active:
            return None

        # simulate credential reuse or exploit
        success = random.random() < 0.4
        log_entry = {
            "from_session": from_session,
            "to_target": to_target,
            "success": success,
            "timestamp": time.time(),
        }
        self.pivot_log.append(log_entry)

        if success:
            new_session = self.c2.register_session(to_target, privilege="user")
            self.pivot_graph[from_session].append(new_session.session_id)
            return new_session
        return None

    def get_pivot_path(self, entry_session: SessionID, target_session: SessionID) -> List[SessionID]:
        """BFS to find pivot path between sessions."""
        visited: Set[SessionID] = set()
        queue: List[Tuple[SessionID, List[SessionID]]] = [(entry_session, [entry_session])]
        while queue:
            current, path = queue.pop(0)
            if current == target_session:
                return path
            visited.add(current)
            for neighbor in self.pivot_graph.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))
        return []

    def __repr__(self) -> str:
        return f"<PivotEngine pivots={len(self.pivot_log)} sessions={len(self.c2.sessions)}>"


# ──────────────────────────────────────────────────────────────
# 6. Report Generator
# ──────────────────────────────────────────────────────────────

class ReportGenerator:
    """Generate attack narrative, IOCs, and remediation recommendations."""

    def __init__(self) -> None:
        self.reports: List[dict] = []

    def generate_report(
        self,
        operation_name: str,
        recon: ReconEngine,
        exploits: ExploitFramework,
        c2: C2Server,
        pivot: PivotEngine,
    ) -> dict:
        """Compile full red team report."""

        # IOCs from all components
        iocs: Set[str] = set()
        for target in recon.targets.values():
            for port, svc in target.ports.items():
                iocs.add(f"{target.host}:{port}/{svc}")
            for vuln in target.vulnerabilities:
                iocs.add(vuln)

        for session in c2.sessions.values():
            iocs.add(f"session:{session.session_id[:16]}")

        # attack narrative
        narrative = []
        narrative.append(f"Operation: {operation_name}")
        narrative.append(f"Targets discovered: {len(recon.targets)}")
        narrative.append(f"Hosts scanned: {len([t for t in recon.targets.values() if t.status == TargetStatus.SCANNED])}")
        narrative.append(f"Exploits attempted: {len(exploits.exploit_log)}")
        narrative.append(f"Successful exploits: {sum(1 for e in exploits.exploit_log if e['success'])}")
        narrative.append(f"C2 sessions established: {len(c2.sessions)}")
        narrative.append(f"Active sessions: {sum(1 for s in c2.sessions.values() if s.active)}")
        narrative.append(f"Lateral movements: {len(pivot.pivot_log)}")
        narrative.append(f"Successful pivots: {sum(1 for p in pivot.pivot_log if p['success'])}")

        # remediation
        remediation = []
        for target in recon.targets.values():
            if target.vulnerabilities:
                remediation.append(f"Patch {target.host}: {', '.join(target.vulnerabilities[:3])}")
            for port in target.ports:
                if port in [23, 445, 3389]:
                    remediation.append(f"Close/Restrict port {port} on {target.host}")

        report = {
            "operation": operation_name,
            "generated_at": time.time(),
            "executive_summary": " ".join(narrative[:3]),
            "narrative": narrative,
            "iocs": sorted(iocs),
            "remediation": remediation,
            "risk_score": self._calculate_risk(recon, exploits, c2, pivot),
            "timeline": self._build_timeline(recon, exploits, c2, pivot),
        }
        self.reports.append(report)
        return report

    def _calculate_risk(self, recon, exploits, c2, pivot) -> float:
        """Calculate composite risk score 0-10."""
        score = 0.0
        score += len(recon.targets) * 0.5
        score += len([e for e in exploits.exploit_log if e["success"]]) * 2.0
        score += len(c2.sessions) * 1.5
        score += len([p for p in pivot.pivot_log if p["success"]]) * 1.0
        return min(10.0, score)

    def _build_timeline(self, recon, exploits, c2, pivot) -> List[dict]:
        events = []
        for scan in recon.scan_history:
            events.append({"time": scan.timestamp, "type": "scan", "target": scan.target_id[:8]})
        for exp in exploits.exploit_log:
            events.append({"time": exp["timestamp"], "type": "exploit", "success": exp["success"]})
        for session in c2.sessions.values():
            events.append({"time": session.created_at, "type": "session", "id": session.session_id[:8]})
        for p in pivot.pivot_log:
            events.append({"time": p["timestamp"], "type": "pivot", "success": p["success"]})
        return sorted(events, key=lambda x: x["time"])

    def __repr__(self) -> str:
        return f"<ReportGenerator reports={len(self.reports)}>"


# ──────────────────────────────────────────────────────────────
# 7. RedTeamEngine — Orchestrator
# ──────────────────────────────────────────────────────────────

class RedTeamEngine:
    """Full red team operation orchestrator."""

    def __init__(self, operation_name: str) -> None:
        self.operation_name = operation_name
        self.recon = ReconEngine()
        self.exploits = ExploitFramework()
        self.c2 = C2Server()
        self.pivot = PivotEngine(self.c2)
        self.reports = ReportGenerator()
        self.phase = "idle"
        self._load_default_exploits()

    def _load_default_exploits(self) -> None:
        """Register common exploit modules."""
        defaults = [
            Exploit("exp-001", "SSH Brute Force", ExploitType.REMOTE, ["ssh"], ["CVE-2023-1234"], 0.3),
            Exploit("exp-002", "SMB EternalBlue", ExploitType.REMOTE, ["smb"], ["CVE-2017-0144"], 0.6),
            Exploit("exp-003", "HTTP RCE", ExploitType.REMOTE, ["http", "https"], ["CVE-2024-5678"], 0.4),
            Exploit("exp-004", "Redis Unauthorized", ExploitType.REMOTE, ["redis"], [], 0.7),
            Exploit("exp-005", "Sudo PrivEsc", ExploitType.PRIVILEGE_ESCALATION, [], ["CVE-2021-3156"], 0.5),
        ]
        for exp in defaults:
            self.exploits.register_exploit(exp)

    def run_full_simulation(self, targets: List[str]) -> dict:
        """Execute complete red team simulation pipeline."""
        print(f"\n[RED TEAM] Operation: {self.operation_name}")
        print("=" * 60)

        # Phase 1: Recon
        self.phase = "recon"
        print(f"\n[PHASE 1] RECONNAISSANCE")
        for host in targets:
            target = self.recon.add_target(host)
            print(f"  [+] Target added: {target}")

            # port scan
            scan = self.recon.port_scan(target.target_id)
            print(f"  [+] Scanned: {len(scan.open_ports)} open ports")

            # service enum
            if scan.open_ports:
                banners = self.recon.service_enum(target.target_id)
                print(f"  [+] Services: {len(banners)} banners")

            # OSINT
            if "." in host:
                osint = self.recon.osint_stub(host)
                print(f"  [+] OSINT: {len(osint['subdomains'])} subdomains, {len(osint['tech_stack'])} tech")

        # Phase 2: Exploitation
        self.phase = "exploitation"
        print(f"\n[PHASE 2] EXPLOITATION")
        compromised = []
        for target in self.recon.targets.values():
            matches = self.exploits.match_exploits(target)
            if matches:
                exploit = matches[0]
                print(f"  [*] Trying {exploit.name} against {target.host}")

                payload = None
                if exploit.payload_required:
                    payload = self.exploits.generate_payload("reverse_shell", target.os_hint)
                    payload = payload.encode("xor")

                result = self.exploits.execute_exploit(exploit.exploit_id, target.target_id, payload)
                if result["success"]:
                    print(f"  [+] SUCCESS! Session established")
                    session = self.c2.register_session(target.target_id, result["privilege"])
                    compromised.append(session)
                    target.status = TargetStatus.COMPROMISED
                else:
                    print(f"  [-] Failed (detection risk: {result.get('detection_risk', 0):.2f})")

        # Phase 3: C2 Establishment
        self.phase = "c2"
        print(f"\n[PHASE 3] COMMAND & CONTROL")
        self.c2.add_listener("http", "0.0.0.0", 8080)
        self.c2.add_listener("dns", "0.0.0.0", 53)
        for session in compromised:
            beacon = self.c2.collect_beacon(session.session_id)
            print(f"  [+] Beacon from {session.session_id[:8]}: {len(beacon['commands'])} commands queued")
            # simulate some C2 activity
            self.c2.send_command(session.session_id, "whoami")
            self.c2.send_command(session.session_id, "netstat -an")

        # Phase 4: Lateral Movement
        self.phase = "pivot"
        print(f"\n[PHASE 4] LATERAL MOVEMENT")
        for session in compromised:
            neighbors = self.pivot.discover_neighbors(session.session_id)
            print(f"  [*] From {session.session_id[:8]} discovered {len(neighbors)} neighbors")
            for neighbor in neighbors[:2]:  # try first 2
                new_session = self.pivot.attempt_pivot(session.session_id, neighbor, self.exploits)
                if new_session:
                    print(f"  [+] PIVOT SUCCESS to {neighbor} via {new_session.session_id[:8]}")
                else:
                    print(f"  [-] Pivot failed to {neighbor}")

        # Phase 5: Reporting
        self.phase = "reporting"
        print(f"\n[PHASE 5] REPORTING")
        report = self.reports.generate_report(
            self.operation_name,
            self.recon,
            self.exploits,
            self.c2,
            self.pivot,
        )
        print(f"  [+] Report generated: {len(report['iocs'])} IOCs, risk score {report['risk_score']:.1f}/10")

        self.phase = "complete"
        return report

    def __repr__(self) -> str:
        return f"<RedTeamEngine '{self.operation_name}' phase={self.phase}>"


# ──────────────────────────────────────────────────────────────
# 8. OffensiveKernel — bridge to Layer 13 (MAGNATRIX runtime)
# ──────────────────────────────────────────────────────────────

class OffensiveKernel:
    """High-level API for MAGNATRIX OS security offensive integration."""

    def __init__(self, engine: RedTeamEngine) -> None:
        self.engine = engine

    def scan(self, targets: List[str]) -> List[ScanResult]:
        """Run reconnaissance scan on targets."""
        results = []
        for host in targets:
            target = self.engine.recon.add_target(host)
            results.append(self.engine.recon.port_scan(target.target_id))
        return results

    def exploit(self, target_id: TargetID, exploit_id: Optional[ExploitID] = None) -> dict:
        """Run exploit against specific target."""
        target = self.engine.recon.targets.get(target_id)
        if not target:
            return {"error": "target_not_found"}

        if exploit_id:
            exploit = self.engine.exploits.exploits.get(exploit_id)
        else:
            matches = self.engine.exploits.match_exploits(target)
            exploit = matches[0] if matches else None

        if not exploit:
            return {"error": "no_matching_exploit"}

        payload = None
        if exploit.payload_required:
            payload = self.engine.exploits.generate_payload("reverse_shell", target.os_hint)

        return self.engine.exploits.execute_exploit(exploit.exploit_id, target_id, payload)

    def c2_command(self, session_id: SessionID, command: str) -> bool:
        return self.engine.c2.send_command(session_id, command)

    def pivot(self, from_session: SessionID, to_target: str) -> Optional[C2Session]:
        return self.engine.pivot.attempt_pivot(from_session, to_target, self.engine.exploits)

    def report(self) -> dict:
        return self.engine.reports.generate_report(
            self.engine.operation_name,
            self.engine.recon,
            self.engine.exploits,
            self.engine.c2,
            self.engine.pivot,
        )

    def stats(self) -> dict:
        return {
            "operation": self.engine.operation_name,
            "phase": self.engine.phase,
            "targets": len(self.engine.recon.targets),
            "scans": len(self.engine.recon.scan_history),
            "exploits_attempted": len(self.engine.exploits.exploit_log),
            "exploits_success": sum(1 for e in self.engine.exploits.exploit_log if e["success"]),
            "c2_sessions": len(self.engine.c2.sessions),
            "c2_active": sum(1 for s in self.engine.c2.sessions.values() if s.active),
            "pivots": len(self.engine.pivot.pivot_log),
            "pivots_success": sum(1 for p in self.engine.pivot.pivot_log if p["success"]),
        }


# ──────────────────────────────────────────────────────────────
# 9. Demo
# ──────────────────────────────────────────────────────────────

def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX Offensive Security — Demo")
    print("=" * 60)

    # create red team operation
    rt = RedTeamEngine("MAGNATRIX-PenTest-2026")
    kernel = OffensiveKernel(rt)

    # define target network
    targets = [
        "web01.magnatrix.internal",
        "db01.magnatrix.internal",
        "api.magnatrix.internal",
        "10.0.1.15",
        "10.0.1.22",
    ]

    # run full simulation
    report = rt.run_full_simulation(targets)

    # display report summary
    print("\n" + "=" * 60)
    print("EXECUTIVE SUMMARY")
    print("=" * 60)
    print(report["executive_summary"])

    print("\n" + "-" * 60)
    print("INDICATORS OF COMPROMISE (IOCs)")
    print("-" * 60)
    for ioc in report["iocs"][:10]:
        print(f"  • {ioc}")
    if len(report["iocs"]) > 10:
        print(f"  ... and {len(report['iocs']) - 10} more")

    print("\n" + "-" * 60)
    print("REMEDIATION RECOMMENDATIONS")
    print("-" * 60)
    for rec in report["remediation"]:
        print(f"  → {rec}")

    print("\n" + "-" * 60)
    print("ATTACK TIMELINE")
    print("-" * 60)
    for event in report["timeline"]:
        ts = time.strftime("%H:%M:%S", time.localtime(event["time"]))
        print(f"  [{ts}] {event['type']:8} {json.dumps({k: v for k, v in event.items() if k != 'time'})}")

    print(f"\n[STATS] {json.dumps(kernel.stats(), indent=2, default=str)}")
    print("\n[DONE] Offensive security demo complete.")


if __name__ == "__main__":
    _demo()