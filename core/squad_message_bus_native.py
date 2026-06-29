"""Squad Message Bus — SQLite-based message passing between agents."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class SquadMessage:
    msg_id: str = ""
    sender_id: str = ""
    recipient_id: str = ""  # empty = broadcast
    channel: str = ""  # general | task_N | decision | review
    content: str = ""
    timestamp: float = 0.0
    msg_type: str = "text"  # text | command | result | decision | alert
    priority: int = 0  # 0=normal, 1=high, 2=urgent

class SquadMessageBus:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._messages: list[SquadMessage] = []
        self._channels: set[str] = {"general", "decision", "review"}
        self._persist_path = self.root / "squad_messages.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._messages = [SquadMessage(**m) for m in data.get("messages", [])]
            self._channels = set(data.get("channels", ["general", "decision", "review"]))

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "messages": [m.__dict__ for m in self._messages],
            "channels": list(self._channels)
        }, indent=2))

    def create_channel(self, channel: str) -> None:
        self._channels.add(channel)
        self._save()

    def send(self, msg_id: str, sender: str, content: str, channel: str = "general", recipient: str = "", msg_type: str = "text", priority: int = 0) -> SquadMessage:
        import time
        msg = SquadMessage(
            msg_id=msg_id, sender_id=sender, recipient_id=recipient,
            channel=channel, content=content, timestamp=time.time(),
            msg_type=msg_type, priority=priority
        )
        self._messages.append(msg)
        self._save()
        return msg

    def inbox(self, agent_id: str, limit: int = 50) -> list[SquadMessage]:
        results = [m for m in self._messages if m.recipient_id == agent_id or m.recipient_id == ""]
        return sorted(results, key=lambda x: x.timestamp, reverse=True)[:limit]

    def channel_history(self, channel: str, limit: int = 100) -> list[SquadMessage]:
        return [m for m in self._messages if m.channel == channel][-limit:]

    def broadcast(self, sender: str, content: str, channel: str = "general") -> SquadMessage:
        return self.send(f"msg_{len(self._messages)}", sender, content, channel=channel)

    def to_dict(self) -> dict:
        return {"message_count": len(self._messages), "channels": len(self._channels)}

    def get_stats(self) -> dict:
        by_channel = {}
        by_type = {}
        for m in self._messages:
            by_channel[m.channel] = by_channel.get(m.channel, 0) + 1
            by_type[m.msg_type] = by_type.get(m.msg_type, 0) + 1
        return {"messages": len(self._messages), "by_channel": by_channel, "by_type": by_type}

__all__ = ["SquadMessageBus", "SquadMessage"]
