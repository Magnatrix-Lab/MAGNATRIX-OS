"""Proxy Protocol Router - Route traffic through HTTP, SOCKS4, SOCKS5."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RouteRule:
    rule_id: str
    target_host: str = ""  # wildcard * for all
    target_port: int = 0
    protocol: str = "http"  # http, https, socks4, socks5
    proxy_id: str = ""
    priority: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "target_host": self.target_host,
            "target_port": self.target_port,
            "protocol": self.protocol,
            "proxy_id": self.proxy_id,
            "priority": self.priority,
            "enabled": self.enabled,
        }


@dataclass
class RouteLog:
    log_id: str
    timestamp: float
    target_host: str
    target_port: int
    proxy_id: str
    protocol: str
    bytes_sent: int = 0
    bytes_received: int = 0
    duration_ms: float = 0.0
    status: str = "success"

    def to_dict(self) -> Dict:
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp,
            "target_host": self.target_host,
            "target_port": self.target_port,
            "proxy_id": self.proxy_id,
            "protocol": self.protocol,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
        }


class ProxyProtocolRouter:
    """Route outbound traffic through HTTP, SOCKS4, or SOCKS5 proxies."""

    SUPPORTED_PROTOCOLS = ["http", "https", "socks4", "socks5"]

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "proxy_router"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.rules: List[RouteRule] = []
        self.logs: List[RouteLog] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for r in data.get("rules", []):
                    self.rules.append(RouteRule(**r))
                for l in data.get("logs", []):
                    self.logs.append(RouteLog(**l))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "rules": [r.to_dict() for r in self.rules],
            "logs": [l.to_dict() for l in self.logs[-2000:]],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def add_rule(self, target_host: str, target_port: int, protocol: str, proxy_id: str, priority: int = 0) -> RouteRule:
        if protocol not in self.SUPPORTED_PROTOCOLS:
            raise ValueError(f"Protocol {protocol} not supported")
        rule_id = f"rule_{hashlib.md5(f'{target_host}:{target_port}:{protocol}:{proxy_id}'.encode()).hexdigest()[:8]}"
        rule = RouteRule(
            rule_id=rule_id,
            target_host=target_host,
            target_port=target_port,
            protocol=protocol,
            proxy_id=proxy_id,
            priority=priority,
            enabled=True,
        )
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        self._save_state()
        return rule

    def route(self, target_host: str, target_port: int, protocol: str = "http") -> Optional[RouteRule]:
        """Find best matching route for a target."""
        for rule in self.rules:
            if not rule.enabled or rule.protocol != protocol:
                continue
            if rule.target_port != 0 and rule.target_port != target_port:
                continue
            if rule.target_host and rule.target_host != "*" and rule.target_host != target_host:
                continue
            # Log the route
            log = RouteLog(
                log_id=f"log_{rule.rule_id}_{int(time.time() * 1000)}",
                timestamp=time.time(),
                target_host=target_host,
                target_port=target_port,
                proxy_id=rule.proxy_id,
                protocol=protocol,
                bytes_sent=0,
                bytes_received=0,
                duration_ms=0.0,
                status="routed",
            )
            self.logs.append(log)
            self._save_state()
            return rule
        return None

    def log_request(self, proxy_id: str, target_host: str, target_port: int, bytes_sent: int, bytes_received: int, duration_ms: float, status: str = "success") -> RouteLog:
        log = RouteLog(
            log_id=f"log_{proxy_id}_{int(time.time() * 1000)}",
            timestamp=time.time(),
            target_host=target_host,
            target_port=target_port,
            proxy_id=proxy_id,
            protocol="http",
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            duration_ms=round(duration_ms, 2),
            status=status,
        )
        self.logs.append(log)
        self._save_state()
        return log

    def disable_rule(self, rule_id: str) -> Optional[RouteRule]:
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                self._save_state()
                return rule
        return None

    def enable_rule(self, rule_id: str) -> Optional[RouteRule]:
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                self._save_state()
                return rule
        return None

    def get_traffic_stats(self, proxy_id: str = "") -> Dict:
        logs = self.logs
        if proxy_id:
            logs = [l for l in logs if l.proxy_id == proxy_id]
        total_sent = sum(l.bytes_sent for l in logs)
        total_received = sum(l.bytes_received for l in logs)
        total_duration = sum(l.duration_ms for l in logs)
        success = sum(1 for l in logs if l.status == "success")
        return {
            "requests_total": len(logs),
            "bytes_sent": total_sent,
            "bytes_received": total_received,
            "avg_duration_ms": round(total_duration / max(1, len(logs)), 2),
            "success_rate": round(success / max(1, len(logs)), 4),
        }

    def get_stats(self) -> Dict:
        by_protocol = {}
        for l in self.logs:
            by_protocol[l.protocol] = by_protocol.get(l.protocol, 0) + 1
        return {
            "rules_total": len(self.rules),
            "logs_total": len(self.logs),
            "traffic_by_protocol": by_protocol,
            "overall_traffic": self.get_traffic_stats(),
        }

    def to_dict(self) -> Dict:
        return {
            "rules": [r.to_dict() for r in self.rules],
            "logs": [l.to_dict() for l in self.logs[-100:]],
            "stats": self.get_stats(),
        }


__all__ = ["ProxyProtocolRouter", "RouteRule", "RouteLog"]
