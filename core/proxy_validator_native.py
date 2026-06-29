"""Proxy Validator - Health and availability validation for proxies."""
from __future__ import annotations

import json
import time
import socket
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ProxyEntry:
    entry_id: str
    host: str
    port: int
    protocol: str = "http"  # http, https, socks4, socks5
    country: str = ""
    anonymity: str = "unknown"  # transparent, anonymous, elite
    last_checked: float = 0.0
    is_alive: bool = False
    response_time_ms: float = 0.0
    uptime_score: float = 0.0  # 0-1

    def to_dict(self) -> Dict:
        return {
            "entry_id": self.entry_id,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "country": self.country,
            "anonymity": self.anonymity,
            "last_checked": self.last_checked,
            "is_alive": self.is_alive,
            "response_time_ms": round(self.response_time_ms, 2),
            "uptime_score": round(self.uptime_score, 3),
        }


@dataclass
class ValidationResult:
    result_id: str
    proxy_id: str
    timestamp: float
    passed: bool = False
    errors: List[str] = field(default_factory=list)
    response_time_ms: float = 0.0
    ssl_supported: bool = False

    def to_dict(self) -> Dict:
        return {
            "result_id": self.result_id,
            "proxy_id": self.proxy_id,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "errors": self.errors,
            "response_time_ms": round(self.response_time_ms, 2),
            "ssl_supported": self.ssl_supported,
        }


class ProxyValidator:
    """Validate proxy health by checking connectivity and response time."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "proxy_validator"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.proxies: Dict[str, ProxyEntry] = {}
        self.results: List[ValidationResult] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for p in data.get("proxies", []):
                    self.proxies[p["entry_id"]] = ProxyEntry(**p)
                for r in data.get("results", []):
                    self.results.append(ValidationResult(**r))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "proxies": [p.to_dict() for p in self.proxies.values()],
            "results": [r.to_dict() for r in self.results[-1000:]],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def add_proxy(self, host: str, port: int, protocol: str = "http", country: str = "", anonymity: str = "unknown") -> ProxyEntry:
        entry_id = f"proxy_{host}:{port}_{protocol}"
        entry = ProxyEntry(
            entry_id=entry_id,
            host=host,
            port=port,
            protocol=protocol,
            country=country,
            anonymity=anonymity,
        )
        self.proxies[entry_id] = entry
        self._save_state()
        return entry

    def validate(self, proxy_id: str, timeout_sec: float = 5.0) -> ValidationResult:
        """Validate a single proxy by attempting TCP connection."""
        if proxy_id not in self.proxies:
            raise ValueError(f"Proxy {proxy_id} not found")
        proxy = self.proxies[proxy_id]
        start = time.time()
        errors = []
        passed = False
        ssl_supported = False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_sec)
            result = sock.connect_ex((proxy.host, proxy.port))
            if result == 0:
                passed = True
                proxy.is_alive = True
                if proxy.protocol in ("https", "socks5"):
                    ssl_supported = True
            else:
                errors.append(f"Connection failed with code {result}")
                proxy.is_alive = False
            sock.close()
        except Exception as e:
            errors.append(str(e))
            proxy.is_alive = False

        elapsed_ms = (time.time() - start) * 1000.0
        proxy.response_time_ms = elapsed_ms
        proxy.last_checked = time.time()

        if passed:
            proxy.uptime_score = min(1.0, proxy.uptime_score * 0.9 + 0.1)
        else:
            proxy.uptime_score = proxy.uptime_score * 0.8

        result = ValidationResult(
            result_id=f"val_{proxy_id}_{int(time.time() * 1000)}",
            proxy_id=proxy_id,
            timestamp=time.time(),
            passed=passed,
            errors=errors,
            response_time_ms=round(elapsed_ms, 2),
            ssl_supported=ssl_supported,
        )
        self.results.append(result)
        self._save_state()
        return result

    def validate_batch(self, proxy_ids: List[str], timeout_sec: float = 5.0) -> List[ValidationResult]:
        return [self.validate(pid, timeout_sec) for pid in proxy_ids]

    def get_alive_proxies(self, min_uptime: float = 0.5) -> List[ProxyEntry]:
        return [p for p in self.proxies.values() if p.is_alive and p.uptime_score >= min_uptime]

    def get_dead_proxies(self) -> List[ProxyEntry]:
        return [p for p in self.proxies.values() if not p.is_alive]

    def get_stats(self) -> Dict:
        alive = sum(1 for p in self.proxies.values() if p.is_alive)
        total = len(self.proxies)
        avg_response = sum(p.response_time_ms for p in self.proxies.values() if p.is_alive) / max(1, alive)
        return {
            "proxies_total": total,
            "alive": alive,
            "dead": total - alive,
            "alive_pct": round(alive / max(1, total) * 100, 1),
            "avg_response_ms": round(avg_response, 2),
            "validations_total": len(self.results),
        }

    def to_dict(self) -> Dict:
        return {
            "proxies": [p.to_dict() for p in self.proxies.values()],
            "results": [r.to_dict() for r in self.results[-100:]],
            "stats": self.get_stats(),
        }


__all__ = ["ProxyValidator", "ProxyEntry", "ValidationResult"]
