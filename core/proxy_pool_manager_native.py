"""Proxy Pool Manager - Centralized proxy pool lifecycle management."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class PoolEntry:
    pool_id: str
    proxy_id: str
    status: str = "active"  # active, cooldown, banned, retired
    added_at: float = 0.0
    last_used: float = 0.0
    use_count: int = 0
    failure_streak: int = 0
    cooldown_until: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "pool_id": self.pool_id,
            "proxy_id": self.proxy_id,
            "status": self.status,
            "added_at": self.added_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "failure_streak": self.failure_streak,
            "cooldown_until": self.cooldown_until,
        }


@dataclass
class PoolStats:
    pool_name: str
    total: int = 0
    active: int = 0
    cooldown: int = 0
    banned: int = 0
    retired: int = 0
    avg_use_count: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "pool_name": self.pool_name,
            "total": self.total,
            "active": self.active,
            "cooldown": self.cooldown,
            "banned": self.banned,
            "retired": self.retired,
            "avg_use_count": round(self.avg_use_count, 2),
        }


class ProxyPoolManager:
    """Manage proxy pool lifecycle: add, cooldown, ban, retire, refresh."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "proxy_pool"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pools: Dict[str, List[PoolEntry]] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for pool_name, entries in data.get("pools", {}).items():
                    self.pools[pool_name] = [PoolEntry(**e) for e in entries]
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {"pools": {name: [e.to_dict() for e in entries] for name, entries in self.pools.items()}}
        state_file.write_text(json.dumps(state, indent=2))

    def create_pool(self, pool_name: str) -> List[PoolEntry]:
        if pool_name not in self.pools:
            self.pools[pool_name] = []
        self._save_state()
        return self.pools[pool_name]

    def add_to_pool(self, pool_name: str, proxy_id: str) -> PoolEntry:
        if pool_name not in self.pools:
            self.pools[pool_name] = []
        # Check if already exists
        for e in self.pools[pool_name]:
            if e.proxy_id == proxy_id:
                return e
        entry = PoolEntry(
            pool_id=f"pool_{pool_name}_{proxy_id}_{int(time.time())}",
            proxy_id=proxy_id,
            status="active",
            added_at=time.time(),
        )
        self.pools[pool_name].append(entry)
        self._save_state()
        return entry

    def use_proxy(self, pool_name: str, proxy_id: str) -> PoolEntry:
        """Mark proxy as used."""
        for e in self.pools.get(pool_name, []):
            if e.proxy_id == proxy_id and e.status == "active":
                e.use_count += 1
                e.last_used = time.time()
                e.failure_streak = 0
                self._save_state()
                return e
        raise ValueError(f"Active proxy {proxy_id} not found in pool {pool_name}")

    def report_failure(self, pool_name: str, proxy_id: str) -> PoolEntry:
        """Report failure, possibly cooldown or ban."""
        for e in self.pools.get(pool_name, []):
            if e.proxy_id == proxy_id:
                e.failure_streak += 1
                if e.failure_streak >= 5:
                    e.status = "banned"
                elif e.failure_streak >= 2:
                    e.status = "cooldown"
                    e.cooldown_until = time.time() + 300  # 5 min cooldown
                self._save_state()
                return e
        raise ValueError(f"Proxy {proxy_id} not found in pool {pool_name}")

    def refresh_pool(self, pool_name: str) -> int:
        """Refresh pool: remove banned, reactivate cooled down."""
        if pool_name not in self.pools:
            return 0
        refreshed = 0
        now = time.time()
        for e in self.pools[pool_name]:
            if e.status == "cooldown" and now >= e.cooldown_until:
                e.status = "active"
                e.failure_streak = 0
                refreshed += 1
            elif e.status == "banned" and e.failure_streak >= 10:
                e.status = "retired"
        self._save_state()
        return refreshed

    def get_active(self, pool_name: str) -> List[PoolEntry]:
        self.refresh_pool(pool_name)
        return [e for e in self.pools.get(pool_name, []) if e.status == "active"]

    def get_pool_stats(self, pool_name: str) -> PoolStats:
        entries = self.pools.get(pool_name, [])
        active = sum(1 for e in entries if e.status == "active")
        cooldown = sum(1 for e in entries if e.status == "cooldown")
        banned = sum(1 for e in entries if e.status == "banned")
        retired = sum(1 for e in entries if e.status == "retired")
        avg_use = sum(e.use_count for e in entries) / max(1, len(entries))
        return PoolStats(
            pool_name=pool_name,
            total=len(entries),
            active=active,
            cooldown=cooldown,
            banned=banned,
            retired=retired,
            avg_use_count=avg_use,
        )

    def get_stats(self) -> Dict:
        total_proxies = sum(len(entries) for entries in self.pools.values())
        return {
            "pools_total": len(self.pools),
            "proxies_total": total_proxies,
            "pool_names": list(self.pools.keys()),
        }

    def to_dict(self) -> Dict:
        return {
            "pools": {name: [e.to_dict() for e in entries] for name, entries in self.pools.items()},
            "stats": self.get_stats(),
        }


__all__ = ["ProxyPoolManager", "PoolEntry", "PoolStats"]
