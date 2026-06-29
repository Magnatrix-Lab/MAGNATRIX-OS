"""DB Connection Pool -- Connection lifecycle, load balancing, health checks."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class Connection:
    conn_id: str = ""
    host: str = ""
    port: int = 0
    database: str = ""
    status: str = "idle"  # idle | active | closed | failed
    created_at: float = 0.0
    last_used: float = 0.0
    query_count: int = 0
    fail_count: int = 0

class DBConnectionPool:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._connections: dict[str, Connection] = {}
        self._max_size: int = 10
        self._min_size: int = 2
        self._max_idle_time: float = 300.0
        self._persist_path = self.root / "db_pool.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._connections = {k: Connection(**v) for k, v in data.get("connections", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "connections": {k: v.__dict__ for k, v in self._connections.items()}
        }, indent=2))

    def create(self, host: str, port: int, database: str) -> Connection:
        conn_id = f"conn_{host}_{port}_{len(self._connections)}"
        conn = Connection(
            conn_id=conn_id, host=host, port=port, database=database,
            created_at=time.time(), last_used=time.time(), status="idle"
        )
        self._connections[conn_id] = conn
        self._save()
        return conn

    def acquire(self) -> Connection | None:
        idle = [c for c in self._connections.values() if c.status == "idle"]
        if idle:
            conn = min(idle, key=lambda c: c.last_used)
            conn.status = "active"
            conn.last_used = time.time()
            self._save()
            return conn
        if len(self._connections) < self._max_size:
            return self.create("localhost", 5432, "default")
        return None

    def release(self, conn_id: str) -> bool:
        conn = self._connections.get(conn_id)
        if conn and conn.status == "active":
            conn.status = "idle"
            conn.last_used = time.time()
            self._save()
            return True
        return False

    def health_check(self) -> list[str]:
        now = time.time()
        failed = []
        for conn_id, conn in self._connections.items():
            if conn.status == "failed":
                failed.append(conn_id)
            elif conn.status == "idle" and (now - conn.last_used) > self._max_idle_time:
                conn.status = "closed"
                failed.append(conn_id)
        self._save()
        return failed

    def get_stats(self) -> dict:
        by_status = {}
        for c in self._connections.values():
            by_status[c.status] = by_status.get(c.status, 0) + 1
        total_queries = sum(c.query_count for c in self._connections.values())
        return {"connections": len(self._connections), "by_status": by_status, "total_queries": total_queries}

    def to_dict(self) -> dict:
        return {"connection_count": len(self._connections), "max": self._max_size}

__all__ = ["DBConnectionPool", "Connection"]
