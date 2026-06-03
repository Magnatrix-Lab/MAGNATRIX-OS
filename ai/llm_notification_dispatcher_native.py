"""LLM Notification Dispatcher — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto
from datetime import datetime

class NotificationPriority(Enum):
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    URGENT = auto()

class NotificationStatus(Enum):
    PENDING = auto()
    SENT = auto()
    DELIVERED = auto()
    READ = auto()
    FAILED = auto()

@dataclass
class Notification:
    id: str
    recipient: str
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: str = ""
    delivered_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class NotificationDispatcher:
    def __init__(self) -> None:
        self._channels: Dict[str, Callable[[Notification], bool]] = {}
        self._notifications: List[Notification] = []
        self._subscriptions: Dict[str, List[str]] = {}

    def register_channel(self, channel_name: str, sender: Callable[[Notification], bool]) -> None:
        self._channels[channel_name] = sender

    def subscribe(self, user_id: str, channel_name: str) -> None:
        if user_id not in self._subscriptions:
            self._subscriptions[user_id] = []
        if channel_name not in self._subscriptions[user_id]:
            self._subscriptions[user_id].append(channel_name)

    def unsubscribe(self, user_id: str, channel_name: str) -> None:
        if user_id in self._subscriptions:
            self._subscriptions[user_id] = [c for c in self._subscriptions[user_id] if c != channel_name]

    def dispatch(self, notification: Notification) -> bool:
        notification.created_at = datetime.now().isoformat()
        self._notifications.append(notification)
        channels = self._subscriptions.get(notification.recipient, [])
        success = False
        for channel in channels:
            sender = self._channels.get(channel)
            if sender:
                if sender(notification):
                    notification.status = NotificationStatus.SENT
                    success = True
        if not success and not channels:
            for sender in self._channels.values():
                if sender(notification):
                    notification.status = NotificationStatus.SENT
                    success = True
                    break
        return success

    def mark_read(self, notification_id: str) -> bool:
        for n in self._notifications:
            if n.id == notification_id:
                n.status = NotificationStatus.READ
                return True
        return False

    def get_pending(self, recipient: Optional[str] = None) -> List[Notification]:
        pending = [n for n in self._notifications if n.status == NotificationStatus.PENDING]
        if recipient:
            pending = [n for n in pending if n.recipient == recipient]
        return pending

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for n in self._notifications:
            counts[n.status.name] = counts.get(n.status.name, 0) + 1
        return {"total": len(self._notifications), "by_status": counts, "channels": len(self._channels)}

def run() -> None:
    print("Notification Dispatcher test")
    e = NotificationDispatcher()
    e.register_channel("email", lambda n: print("  [EMAIL] To " + n.recipient + ": " + n.title) or True)
    e.register_channel("sms", lambda n: print("  [SMS] To " + n.recipient + ": " + n.title) or True)
    e.subscribe("alice", "email")
    e.subscribe("bob", "sms")
    e.dispatch(Notification("n1", "alice", "Welcome", "Welcome to the system!"))
    e.dispatch(Notification("n2", "bob", "Alert", "System maintenance tonight", NotificationPriority.HIGH))
    print("  Pending: " + str(len(e.get_pending())))
    print("  Stats: " + str(e.get_stats()))
    print("Notification Dispatcher test complete.")

if __name__ == "__main__":
    run()
