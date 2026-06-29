"""Proxy Rotator - Proxy rotation and load balancing."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import deque


@dataclass
class RotationSession:
    session_id: str
    proxy_ids: List[str] = field(default_factory=list)
    current_index: int = 0
    strategy: str = "round_robin"  # round_robin, least_used, random, weighted
    created_at: float = 0.0
    requests_served: int = 0

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "proxy_ids": self.proxy_ids,
            "current_index": self.current_index,
            "strategy": self.strategy,
            "created_at": self.created_at,
            "requests_served": self.requests_served,
        }


@dataclass
class ProxyUsage:
    proxy_id: str
    request_count: int = 0
    total_response_time_ms: float = 0.0
    failure_count: int = 0
    last_used: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "proxy_id": self.proxy_id,
            "request_count": self.request_count,
            "total_response_time_ms": round(self.total_response_time_ms, 2),
            "failure_count": self.failure_count,
            "last_used": self.last_used,
        }


class ProxyRotator:
    """Rotate proxies across requests with multiple strategies."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "proxy_rotator"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, RotationSession] = {}
        self.usage: Dict[str, ProxyUsage] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for s in data.get("sessions", []):
                    self.sessions[s["session_id"]] = RotationSession(**s)
                for u in data.get("usage", []):
                    self.usage[u["proxy_id"]] = ProxyUsage(**u)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "sessions": [s.to_dict() for s in self.sessions.values()],
            "usage": [u.to_dict() for u in self.usage.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def create_session(self, proxy_ids: List[str], strategy: str = "round_robin") -> RotationSession:
        if strategy not in ("round_robin", "least_used", "random", "weighted"):
            raise ValueError(f"Strategy {strategy} not supported")
        session_id = f"sess_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        session = RotationSession(
            session_id=session_id,
            proxy_ids=proxy_ids,
            strategy=strategy,
            created_at=time.time(),
        )
        self.sessions[session_id] = session
        for pid in proxy_ids:
            if pid not in self.usage:
                self.usage[pid] = ProxyUsage(proxy_id=pid)
        self._save_state()
        return session

    def next_proxy(self, session_id: str) -> Optional[str]:
        """Get next proxy according to rotation strategy."""
        if session_id not in self.sessions:
            return None
        session = self.sessions[session_id]
        if not session.proxy_ids:
            return None

        if session.strategy == "round_robin":
            pid = session.proxy_ids[session.current_index % len(session.proxy_ids)]
            session.current_index += 1
        elif session.strategy == "least_used":
            pid = min(session.proxy_ids, key=lambda p: self.usage.get(p, ProxyUsage(p)).request_count)
        elif session.strategy == "weighted":
            # Prefer proxies with lower failure rates
            weights = {}
            for p in session.proxy_ids:
                u = self.usage.get(p, ProxyUsage(p))
                fail_rate = u.failure_count / max(1, u.request_count)
                weights[p] = 1.0 - fail_rate
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}
            # Simple deterministic weighted pick
            pid = max(weights, key=weights.get) if weights else session.proxy_ids[0]
        else:
            import random
            random.seed(int(time.time() * 1000))
            pid = random.choice(session.proxy_ids)

        session.requests_served += 1
        self.usage[pid].request_count += 1
        self.usage[pid].last_used = time.time()
        self._save_state()
        return pid

    def report_failure(self, session_id: str, proxy_id: str) -> None:
        """Report a proxy failure to adjust rotation weights."""
        if proxy_id in self.usage:
            self.usage[proxy_id].failure_count += 1
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if proxy_id in session.proxy_ids and self.usage.get(proxy_id, ProxyUsage(proxy_id)).failure_count > 5:
                session.proxy_ids.remove(proxy_id)
        self._save_state()

    def report_success(self, proxy_id: str, response_time_ms: float) -> None:
        if proxy_id in self.usage:
            self.usage[proxy_id].total_response_time_ms += response_time_ms
        self._save_state()

    def get_session_stats(self, session_id: str) -> Dict:
        if session_id not in self.sessions:
            return {}
        session = self.sessions[session_id]
        usage_stats = {pid: self.usage.get(pid, ProxyUsage(pid)).to_dict() for pid in session.proxy_ids}
        return {
            "session_id": session_id,
            "strategy": session.strategy,
            "requests_served": session.requests_served,
            "active_proxies": len(session.proxy_ids),
            "usage": usage_stats,
        }

    def get_stats(self) -> Dict:
        total_reqs = sum(u.request_count for u in self.usage.values())
        total_fails = sum(u.failure_count for u in self.usage.values())
        return {
            "sessions_total": len(self.sessions),
            "proxies_tracked": len(self.usage),
            "total_requests": total_reqs,
            "total_failures": total_fails,
            "failure_rate": round(total_fails / max(1, total_reqs), 4),
        }

    def to_dict(self) -> Dict:
        return {
            "sessions": [s.to_dict() for s in self.sessions.values()],
            "usage": [u.to_dict() for u in self.usage.values()],
            "stats": self.get_stats(),
        }


__all__ = ["ProxyRotator", "RotationSession", "ProxyUsage"]
