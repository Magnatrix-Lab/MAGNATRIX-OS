"""
message_gateway_native.py
MAGNATRIX-OS — Message Gateway

Inspired by Deer-Flow (ByteDance): Message gateway for inter-agent communication.
Route, filter, and broadcast messages between agents and subagents. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class GatewayMessage:
    msg_id: str
    channel: str
    from_id: str
    to_id: str
    content: str
    priority: int = 5
    delivered: bool = False
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MessageGateway:
    """Route, filter, and broadcast messages between agents and subagents."""

    def __init__(self, gateway_dir: str = "./message_gateway"):
        self.gateway_dir = Path(gateway_dir)
        self.gateway_dir.mkdir(exist_ok=True)
        self.messages: List[GatewayMessage] = []
        self.subscribers: Dict[str, List[str]] = {}  # channel -> [agent_ids]
        self._load()

    def _load(self) -> None:
        for fname in ["messages.json", "subscribers.json"]:
            f = self.gateway_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "messages.json":
                            self.messages = [GatewayMessage(**m) for m in data]
                        else:
                            self.subscribers = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.gateway_dir / "messages.json", "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self.messages[-500:]], f, indent=2)
        with open(self.gateway_dir / "subscribers.json", "w", encoding="utf-8") as f:
            json.dump(self.subscribers, f, indent=2)

    def subscribe(self, agent_id: str, channel: str) -> None:
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        if agent_id not in self.subscribers[channel]:
            self.subscribers[channel].append(agent_id)
        self._save()

    def unsubscribe(self, agent_id: str, channel: str) -> None:
        if channel in self.subscribers and agent_id in self.subscribers[channel]:
            self.subscribers[channel].remove(agent_id)
        self._save()

    def send(self, msg_id: str, channel: str, from_id: str, to_id: str,
             content: str, priority: int = 5) -> GatewayMessage:
        msg = GatewayMessage(
            msg_id=msg_id, channel=channel, from_id=from_id, to_id=to_id,
            content=content, priority=priority,
        )
        self.messages.append(msg)
        self._save()
        return msg

    def broadcast(self, msg_id: str, channel: str, from_id: str, content: str) -> List[GatewayMessage]:
        recipients = self.subscribers.get(channel, [])
        sent = []
        for to_id in recipients:
            if to_id != from_id:
                msg = self.send(f"{msg_id}_{to_id}", channel, from_id, to_id, content)
                sent.append(msg)
        return sent

    def get_inbox(self, agent_id: str, channel: Optional[str] = None) -> List[GatewayMessage]:
        msgs = [m for m in self.messages if m.to_id == agent_id and not m.delivered]
        if channel:
            msgs = [m for m in msgs if m.channel == channel]
        return msgs

    def mark_delivered(self, msg_id: str) -> bool:
        for m in self.messages:
            if m.msg_id == msg_id:
                m.delivered = True
                self._save()
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.messages)
        delivered = sum(1 for m in self.messages if m.delivered)
        channels = len(self.subscribers)
        return {"total_messages": total, "delivered": delivered, "channels": channels}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MessageGateway", "GatewayMessage"]