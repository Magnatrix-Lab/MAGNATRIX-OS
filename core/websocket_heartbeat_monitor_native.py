"""WebSocket Heartbeat Monitor — Ping/pong, timeout detection, cleanup."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class HeartbeatEvent:
    conn_id: str = ""
    event_type: str = ""  # ping | pong | timeout
    timestamp: float = 0.0
    latency_ms: int = 0

class WebSocketHeartbeatMonitor:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._pings: dict[str, float] = {}
        self._events: list[HeartbeatEvent] = []
        self._timeout_sec: float = 30.0
        self._persist_path = self.root / "websocket_heartbeat.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._pings = data.get("pings", {})
            self._events = [HeartbeatEvent(**e) for e in data.get("events", [])]
            self._timeout_sec = data.get("timeout_sec", 30.0)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "pings": self._pings,
            "events": [e.__dict__ for e in self._events],
            "timeout_sec": self._timeout_sec
        }, indent=2))

    def send_ping(self, conn_id: str) -> None:
        self._pings[conn_id] = time.time()
        self._events.append(HeartbeatEvent(conn_id=conn_id, event_type="ping", timestamp=time.time()))
        self._save()

    def receive_pong(self, conn_id: str) -> bool:
        ping_time = self._pings.pop(conn_id, None)
        if ping_time is not None:
            latency_ms = int((time.time() - ping_time) * 1000)
            self._events.append(HeartbeatEvent(conn_id=conn_id, event_type="pong", timestamp=time.time(), latency_ms=latency_ms))
            self._save()
            return True
        return False

    def check_timeouts(self, active_conns: list[str]) -> list[str]:
        now = time.time()
        timed_out = []
        for conn_id, ping_time in list(self._pings.items()):
            if conn_id not in active_conns or (now - ping_time) > self._timeout_sec:
                timed_out.append(conn_id)
                self._events.append(HeartbeatEvent(conn_id=conn_id, event_type="timeout", timestamp=now))
                self._pings.pop(conn_id, None)
        self._save()
        return timed_out

    def set_timeout(self, timeout_sec: float) -> None:
        self._timeout_sec = timeout_sec
        self._save()

    def to_dict(self) -> dict:
        return {"pending_pings": len(self._pings), "event_count": len(self._events), "timeout_sec": self._timeout_sec}

    def get_stats(self) -> dict:
        pongs = [e for e in self._events if e.event_type == "pong"]
        avg_latency = sum(e.latency_ms for e in pongs) / len(pongs) if pongs else 0
        return {"pending_pings": len(self._pings), "events": len(self._events), "timeouts": sum(1 for e in self._events if e.event_type == "timeout"), "avg_latency_ms": avg_latency}

__all__ = ["WebSocketHeartbeatMonitor", "HeartbeatEvent"]
