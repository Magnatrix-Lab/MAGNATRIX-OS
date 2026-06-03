"""
llm_connection_pool_native.py
MAGNATRIX-OS Connection Pool Engine
Native Python, stdlib only.
Provides connection pooling with borrow/return, health checks, max idle time, and pool statistics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Set

T = TypeVar('T')


class ConnectionStatus(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


@dataclass
class PooledConnection(Generic[T]):
    connection_id: str
    connection: T
    status: ConnectionStatus = ConnectionStatus.IDLE
    created_at: float = field(default_factory=time.time)
    last_used: float = 0.0
    use_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.connection_id, "status": self.status.value,
            "created_at": self.created_at, "last_used": self.last_used,
            "use_count": self.use_count,
        }


class ConnectionPoolEngine(Generic[T]):
    """Generic connection pool with health checks and lifecycle management."""

    def __init__(self, max_size: int = 10, min_idle: int = 2,
                 max_idle_time: float = 300.0, health_check_interval: float = 30.0) -> None:
        self.max_size = max_size
        self.min_idle = min_idle
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval
        self._pool: Dict[str, PooledConnection[T]] = {}
        self._factory: Optional[Callable[[], T]] = None
        self._health_check: Optional[Callable[[T], bool]] = None
        self._counter = 0

    def set_factory(self, factory: Callable[[], T]) -> None:
        self._factory = factory

    def set_health_check(self, check: Callable[[T], bool]) -> None:
        self._health_check = check

    def _create_id(self) -> str:
        self._counter += 1
        return f"conn_{self._counter}_{int(time.time())}"

    def create_connection(self) -> Optional[PooledConnection[T]]:
        if not self._factory:
            return None
        conn = self._factory()
        pc = PooledConnection(connection_id=self._create_id(), connection=conn)
        self._pool[pc.connection_id] = pc
        return pc

    def borrow(self) -> Optional[PooledConnection[T]]:
        # Return idle connection
        for pc in self._pool.values():
            if pc.status == ConnectionStatus.IDLE:
                pc.status = ConnectionStatus.ACTIVE
                pc.last_used = time.time()
                pc.use_count += 1
                return pc
        # Create new if under limit
        if len(self._pool) < self.max_size:
            new_pc = self.create_connection()
            if new_pc:
                new_pc.status = ConnectionStatus.ACTIVE
                new_pc.last_used = time.time()
                new_pc.use_count = 1
                return new_pc
        return None

    def return_connection(self, connection_id: str) -> bool:
        pc = self._pool.get(connection_id)
        if not pc:
            return False
        pc.status = ConnectionStatus.IDLE
        return True

    def close(self, connection_id: str) -> bool:
        pc = self._pool.pop(connection_id, None)
        if pc:
            pc.status = ConnectionStatus.CLOSED
            return True
        return False

    def health_check_all(self) -> List[str]:
        unhealthy = []
        if not self._health_check:
            return unhealthy
        for pc in list(self._pool.values()):
            if pc.status == ConnectionStatus.CLOSED:
                continue
            try:
                if not self._health_check(pc.connection):
                    pc.status = ConnectionStatus.UNHEALTHY
                    unhealthy.append(pc.connection_id)
            except Exception:
                pc.status = ConnectionStatus.UNHEALTHY
                unhealthy.append(pc.connection_id)
        return unhealthy

    def evict_idle(self) -> int:
        now = time.time()
        to_evict = [cid for cid, pc in self._pool.items()
                    if pc.status == ConnectionStatus.IDLE and now - pc.last_used > self.max_idle_time]
        for cid in to_evict:
            self.close(cid)
        return len(to_evict)

    def get_stats(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for pc in self._pool.values():
            by_status[pc.status.value] = by_status.get(pc.status.value, 0) + 1
        return {
            "total": len(self._pool), "max_size": self.max_size,
            "by_status": by_status, "avg_use_count": sum(pc.use_count for pc in self._pool.values()) / max(len(self._pool), 1),
        }

    def get_connection(self, connection_id: str) -> Optional[PooledConnection[T]]:
        return self._pool.get(connection_id)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Connection Pool Engine")
    print("=" * 60)

    engine = ConnectionPoolEngine[str](max_size=5, min_idle=1)
    engine.set_factory(lambda: f"connection_{int(time.time() * 1000)}")
    engine.set_health_check(lambda c: c is not None and len(c) > 0)

    print("\n--- Borrow connections ---")
    conns = []
    for i in range(3):
        conn = engine.borrow()
        if conn:
            conns.append(conn)
            print(f"  Borrowed: {conn.connection_id}")

    print("\n--- Return connections ---")
    for c in conns:
        engine.return_connection(c.connection_id)
        print(f"  Returned: {c.connection_id}")

    print("\n--- Health check ---")
    unhealthy = engine.health_check_all()
    print(f"  Unhealthy: {unhealthy}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nConnection Pool test complete.")


if __name__ == "__main__":
    run()
