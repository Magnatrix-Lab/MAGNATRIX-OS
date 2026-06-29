"""Proxy Anonymity Checker - Detect anonymity level of proxies."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class AnonymityCheck:
    check_id: str
    proxy_id: str
    timestamp: float
    level: str = "unknown"  # transparent, anonymous, distorting, elite
    headers_leaked: List[str] = field(default_factory=list)
    real_ip_detected: bool = False
    proxy_detected: bool = False
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "check_id": self.check_id,
            "proxy_id": self.proxy_id,
            "timestamp": self.timestamp,
            "level": self.level,
            "headers_leaked": self.headers_leaked,
            "real_ip_detected": self.real_ip_detected,
            "proxy_detected": self.proxy_detected,
            "confidence": round(self.confidence, 3),
        }


class ProxyAnonymityChecker:
    """Check proxy anonymity level by analyzing header leakage patterns."""

    HEADER_PATTERNS = {
        "transparent": ["X-Forwarded-For", "X-Real-IP", "Via", "Proxy-Connection"],
        "anonymous": ["Via", "Proxy-Connection"],
        "distorting": ["Via"],
        "elite": [],
    }

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "proxy_anonymity"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.checks: List[AnonymityCheck] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for c in data.get("checks", []):
                    self.checks.append(AnonymityCheck(**c))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {"checks": [c.to_dict() for c in self.checks[-1000:]]}
        state_file.write_text(json.dumps(state, indent=2))

    def check(self, proxy_id: str, simulated_headers: Optional[List[str]] = None) -> AnonymityCheck:
        """Check anonymity level of a proxy."""
        if simulated_headers is None:
            # Simulate based on proxy_id hash
            h = hash(proxy_id)
            levels = ["transparent", "anonymous", "distorting", "elite"]
            level = levels[h % len(levels)]
            leaked = self.HEADER_PATTERNS[level][:]
            real_ip = level in ("transparent", "anonymous")
            proxy_detected = level in ("transparent", "anonymous", "distorting")
            confidence = 0.6 + (h % 30) / 100.0
        else:
            leaked = []
            real_ip = False
            proxy_detected = False
            level = "elite"
            for header in simulated_headers:
                if header in ("X-Forwarded-For", "X-Real-IP"):
                    leaked.append(header)
                    real_ip = True
                    level = "transparent"
                elif header in ("Via", "Proxy-Connection"):
                    leaked.append(header)
                    proxy_detected = True
                    if level == "elite":
                        level = "anonymous"
            confidence = 0.9 if leaked else 0.95

        check = AnonymityCheck(
            check_id=f"anon_{proxy_id}_{int(time.time() * 1000)}",
            proxy_id=proxy_id,
            timestamp=time.time(),
            level=level,
            headers_leaked=leaked,
            real_ip_detected=real_ip,
            proxy_detected=proxy_detected,
            confidence=round(confidence, 3),
        )
        self.checks.append(check)
        self._save_state()
        return check

    def check_batch(self, proxy_ids: List[str]) -> List[AnonymityCheck]:
        return [self.check(pid) for pid in proxy_ids]

    def get_elite_proxies(self) -> List[str]:
        latest = {}
        for c in self.checks:
            if c.proxy_id not in latest or c.timestamp > latest[c.proxy_id].timestamp:
                latest[c.proxy_id] = c
        return [pid for pid, c in latest.items() if c.level == "elite"]

    def get_anonymity_distribution(self) -> Dict[str, int]:
        dist = {}
        for c in self.checks:
            dist[c.level] = dist.get(c.level, 0) + 1
        return dist

    def get_stats(self) -> Dict:
        return {
            "checks_total": len(self.checks),
            "anonymity_dist": self.get_anonymity_distribution(),
            "elite_count": len(self.get_elite_proxies()),
        }

    def to_dict(self) -> Dict:
        return {
            "checks": [c.to_dict() for c in self.checks[-200:]],
            "stats": self.get_stats(),
        }


__all__ = ["ProxyAnonymityChecker", "AnonymityCheck"]
