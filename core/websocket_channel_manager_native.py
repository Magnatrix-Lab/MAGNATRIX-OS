"""WebSocket Channel Manager — Channel creation, ACL, rate limits."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class Channel:
    channel_id: str = ""
    name: str = ""
    created_at: float = 0.0
    owner: str = ""
    max_members: int = 100
    rate_limit_msg_per_sec: int = 10
    members: list[str] = None
    banned: list[str] = None

    def __post_init__(self):
        if self.members is None:
            self.members = []
        if self.banned is None:
            self.banned = []

class WebSocketChannelManager:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._channels: dict[str, Channel] = {}
        self._rate_counters: dict[str, list[float]] = {}
        self._persist_path = self.root / "websocket_channels.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._channels = {k: Channel(**v) for k, v in data.get("channels", {}).items()}
            self._rate_counters = data.get("rate_counters", {})

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "channels": {k: v.__dict__ for k, v in self._channels.items()},
            "rate_counters": self._rate_counters
        }, indent=2))

    def create_channel(self, name: str, owner: str, max_members: int = 100, rate_limit: int = 10) -> Channel:
        ch_id = f"ch_{len(self._channels)}"
        channel = Channel(channel_id=ch_id, name=name, created_at=time.time(), owner=owner, max_members=max_members, rate_limit_msg_per_sec=rate_limit)
        self._channels[ch_id] = channel
        self._save()
        return channel

    def join_channel(self, ch_id: str, conn_id: str) -> bool:
        channel = self._channels.get(ch_id)
        if not channel or conn_id in channel.banned or len(channel.members) >= channel.max_members:
            return False
        if conn_id not in channel.members:
            channel.members.append(conn_id)
            self._save()
        return True

    def leave_channel(self, ch_id: str, conn_id: str) -> bool:
        channel = self._channels.get(ch_id)
        if channel and conn_id in channel.members:
            channel.members.remove(conn_id)
            self._save()
            return True
        return False

    def ban(self, ch_id: str, conn_id: str) -> bool:
        channel = self._channels.get(ch_id)
        if channel:
            if conn_id not in channel.banned:
                channel.banned.append(conn_id)
            if conn_id in channel.members:
                channel.members.remove(conn_id)
            self._save()
            return True
        return False

    def check_rate(self, ch_id: str, conn_id: str) -> bool:
        channel = self._channels.get(ch_id)
        if not channel:
            return False
        key = f"{ch_id}:{conn_id}"
        now = time.time()
        window = [t for t in self._rate_counters.get(key, []) if now - t < 1.0]
        if len(window) >= channel.rate_limit_msg_per_sec:
            return False
        window.append(now)
        self._rate_counters[key] = window
        self._save()
        return True

    def delete_channel(self, ch_id: str) -> bool:
        if ch_id in self._channels:
            del self._channels[ch_id]
            self._save()
            return True
        return False

    def to_dict(self) -> dict:
        return {"channel_count": len(self._channels)}

    def get_stats(self) -> dict:
        total_members = sum(len(c.members) for c in self._channels.values())
        return {"channels": len(self._channels), "total_members": total_members, "banned": sum(len(c.banned) for c in self._channels.values())}

__all__ = ["WebSocketChannelManager", "Channel"]
