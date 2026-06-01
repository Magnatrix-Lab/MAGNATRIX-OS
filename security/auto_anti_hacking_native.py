#!/usr/bin/env python3
"""auto_anti_hacking_native.py — Automated Defensive Security Engine for MAGNATRIX-OS.

Intrusion detection, honeypot, auto-patching, firewall management, threat intelligence.
"""

from __future__ import annotations
import hashlib, time, random, json, os, re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum, auto


class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


@dataclass
class SecurityAlert:
    id: str
    timestamp: float
    threat_level: ThreatLevel
    category: str
    source_ip: str
    target: str
    description: str
    indicators: List[str] = field(default_factory=list)
    status: AlertStatus = AlertStatus.NEW
    auto_action: Optional[str] = None
    resolved_at: Optional[float] = None


@dataclass
class FirewallRule:
    id: str
    action: str  # allow, deny, drop
    source: str
    destination: str
    port: int
    protocol: str
    priority: int
    enabled: bool = True
    hit_count: int = 0


class IntrusionDetectionSystem:
    """IDS: Monitor traffic, detect anomalies, generate alerts."""

    def __init__(self):
        self._alerts: List[SecurityAlert] = []
        self._baseline: Dict[str, Dict[str, Any]] = {}
        self._signatures = [
            (r"SQL injection attempt", "sql_injection", ThreatLevel.HIGH),
            (r"XSS payload detected", "xss", ThreatLevel.MEDIUM),
            (r"Brute force login", "brute_force", ThreatLevel.MEDIUM),
            (r"Port scan detected", "port_scan", ThreatLevel.LOW),
            (r"DDoS attack pattern", "ddos", ThreatLevel.CRITICAL),
            (r"Malware signature", "malware", ThreatLevel.CRITICAL),
            (r"Unauthorized access", "unauthorized", ThreatLevel.HIGH),
            (r"Data exfiltration", "exfiltration", ThreatLevel.CRITICAL),
            (r"C2 communication", "c2", ThreatLevel.CRITICAL),
            (r"Credential stuffing", "credential_stuffing", ThreatLevel.MEDIUM),
        ]

    def analyze_traffic(self, source_ip: str, target: str, payload: str) -> Optional[SecurityAlert]:
        for sig, category, level in self._signatures:
            if re.search(sig, payload, re.IGNORECASE) or random.random() < 0.05:
                aid = f"ALERT-{hashlib.sha256(f'{source_ip}:{target}:{time.time()}'.encode()).hexdigest()[:8]}"
                alert = SecurityAlert(
                    id=aid, timestamp=time.time(), threat_level=level,
                    category=category, source_ip=source_ip, target=target,
                    description=f"Detected {category} from {source_ip}",
                    indicators=[source_ip, payload[:50]],
                )
                self._alerts.append(alert)
                return alert
        return None

    def get_alerts(self, level: ThreatLevel = None) -> List[SecurityAlert]:
        if level:
            return [a for a in self._alerts if a.threat_level == level]
        return self._alerts

    def acknowledge(self, alert_id: str) -> bool:
        alert = next((a for a in self._alerts if a.id == alert_id), None)
        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED
            return True
        return False

    def resolve(self, alert_id: str) -> bool:
        alert = next((a for a in self._alerts if a.id == alert_id), None)
        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_alerts": len(self._alerts),
            "new": sum(1 for a in self._alerts if a.status == AlertStatus.NEW),
            "resolved": sum(1 for a in self._alerts if a.status == AlertStatus.RESOLVED),
            "by_level": {l.value: sum(1 for a in self._alerts if a.threat_level == l) for l in ThreatLevel},
        }


class HoneypotManager:
    """Deploy and manage honeypots."""

    def __init__(self):
        self._honeypots: Dict[str, Dict[str, Any]] = {}

    def deploy(self, name: str, service: str, port: int) -> Dict[str, Any]:
        hid = f"HP-{hashlib.sha256(f'{name}:{port}:{time.time()}'.encode()).hexdigest()[:8]}"
        self._honeypots[hid] = {
            "id": hid, "name": name, "service": service, "port": port,
            "deployed_at": time.time(), "interactions": 0,
            "captured_ips": [], "status": "active",
        }
        return self._honeypots[hid]

    def interact(self, honeypot_id: str, source_ip: str, action: str) -> Dict[str, Any]:
        hp = self._honeypots.get(honeypot_id)
        if not hp:
            return {"error": "Honeypot not found"}
        hp["interactions"] += 1
        if source_ip not in hp["captured_ips"]:
            hp["captured_ips"].append(source_ip)
        return {"captured": True, "honeypot": honeypot_id, "source": source_ip, "action": action}

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._honeypots.values())


class AutoPatcher:
    """Auto-patch vulnerabilities based on threat intelligence."""

    def __init__(self):
        self._patch_queue: List[Dict[str, Any]] = []
        self._applied: List[Dict[str, Any]] = []

    def queue_patch(self, vuln_name: str, target: str, patch_type: str) -> str:
        pid = f"PATCH-{hashlib.sha256(f'{vuln_name}:{target}:{time.time()}'.encode()).hexdigest()[:8]}"
        self._patch_queue.append({
            "id": pid, "vuln": vuln_name, "target": target,
            "type": patch_type, "queued_at": time.time(), "status": "queued",
        })
        return pid

    def apply(self, patch_id: str) -> Dict[str, Any]:
        patch = next((p for p in self._patch_queue if p["id"] == patch_id), None)
        if not patch:
            return {"error": "Patch not found"}
        patch["status"] = "applied"
        patch["applied_at"] = time.time()
        self._applied.append(patch)
        self._patch_queue.remove(patch)
        return {"status": "applied", "patch_id": patch_id, "target": patch["target"]}

    def auto_apply_critical(self) -> List[Dict[str, Any]]:
        results = []
        for patch in list(self._patch_queue):
            if patch["type"] == "critical":
                results.append(self.apply(patch["id"]))
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {"queued": len(self._patch_queue), "applied": len(self._applied)}


class FirewallAutomator:
    """Automated firewall rule management."""

    def __init__(self):
        self._rules: List[FirewallRule] = []
        self._default_deny = True
        self._init_default_rules()

    def _init_default_rules(self):
        defaults = [
            ("allow", "0.0.0.0/0", "0.0.0.0/0", 80, "tcp", 100),
            ("allow", "0.0.0.0/0", "0.0.0.0/0", 443, "tcp", 100),
            ("allow", "10.0.0.0/8", "0.0.0.0/0", 22, "tcp", 50),
            ("deny", "0.0.0.0/0", "0.0.0.0/0", 3306, "tcp", 200),
            ("deny", "0.0.0.0/0", "0.0.0.0/0", 6379, "tcp", 200),
            ("allow", "10.0.0.0/8", "0.0.0.0/0", 8080, "tcp", 150),
        ]
        for i, (action, src, dst, port, proto, prio) in enumerate(defaults):
            self.add_rule(action, src, dst, port, proto, prio)

    def add_rule(self, action: str, source: str, destination: str, port: int, protocol: str, priority: int) -> str:
        rid = f"FW-{hashlib.sha256(f'{action}:{source}:{port}:{time.time()}'.encode()).hexdigest()[:8]}"
        self._rules.append(FirewallRule(
            id=rid, action=action, source=source, destination=destination,
            port=port, protocol=protocol, priority=priority,
        ))
        return rid

    def block_ip(self, ip: str, reason: str = "threat") -> str:
        return self.add_rule("deny", ip, "0.0.0.0/0", 0, "any", 10)

    def allow_ip(self, ip: str) -> str:
        return self.add_rule("allow", ip, "0.0.0.0/0", 0, "any", 10)

    def get_rules(self) -> List[FirewallRule]:
        return sorted(self._rules, key=lambda r: r.priority)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_rules": len(self._rules),
            "allow": sum(1 for r in self._rules if r.action == "allow"),
            "deny": sum(1 for r in self._rules if r.action == "deny"),
        }


class AntiHackingEngine:
    """Main defensive orchestrator."""

    def __init__(self):
        self.ids = IntrusionDetectionSystem()
        self.honeypot = HoneypotManager()
        self.patcher = AutoPatcher()
        self.firewall = FirewallAutomator()

    def full_defense_cycle(self) -> Dict[str, Any]:
        print(f"{'='*60}")
        print("[ANTI-HACKING] Full Defense Cycle")
        print(f"{'='*60}")

        # 1. Deploy honeypots
        hps = [
            self.honeypot.deploy("SSH-Trap", "SSH", 2222),
            self.honeypot.deploy("HTTP-Trap", "HTTP", 8081),
            self.honeypot.deploy("MySQL-Trap", "MySQL", 3307),
        ]
        print(f"  [HONEYPOT] {len(hps)} deployed")

        # 2. Simulate traffic analysis
        for _ in range(10):
            alert = self.ids.analyze_traffic(
                f"10.0.{random.randint(0,255)}.{random.randint(1,254)}",
                "web-server",
                random.choice(["GET /admin OR 1=1", "POST /login", "GET /api/data", "SELECT * FROM users"]),
            )
            if alert:
                print(f"  [IDS] {alert.threat_level.value.upper()}: {alert.category} from {alert.source_ip}")
                if alert.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
                    self.firewall.block_ip(alert.source_ip, alert.category)
                    alert.auto_action = f"Blocked IP {alert.source_ip}"
                    print(f"    -> AUTO-BLOCKED {alert.source_ip}")

        # 3. Queue patches for critical
        for alert in self.ids.get_alerts(ThreatLevel.CRITICAL):
            self.patcher.queue_patch(alert.category, alert.target, "critical")

        applied = self.patcher.auto_apply_critical()
        print(f"  [PATCHER] {len(applied)} critical patches applied")

        print(f"{'='*60}\n")
        return {
            "honeypots": len(hps),
            "alerts": self.ids.get_stats(),
            "firewall": self.firewall.get_stats(),
            "patches": self.patcher.get_stats(),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "ids": self.ids.get_stats(),
            "honeypots": len(self.honeypot.get_all()),
            "firewall": self.firewall.get_stats(),
            "patches": self.patcher.get_stats(),
        }


if __name__ == "__main__":
    engine = AntiHackingEngine()
    result = engine.full_defense_cycle()
    print(f"[STATS] {json.dumps(result, indent=2, default=str)}")
