"""
llm_notification_router_native.py
MAGNATRIX-OS Notification Router Engine
Native Python, stdlib only.
Provides multi-channel notification routing with priority, batching, templating,
rate limiting, and delivery tracking for alerts, reports, and system events.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class ChannelType(Enum):
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class DeliveryStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    SUPPRESSED = "suppressed"


@dataclass
class Notification:
    id: str
    title: str
    body: str
    channels: List[ChannelType]
    priority: NotificationPriority
    recipients: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    template_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    scheduled_at: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "title": self.title, "body": self.body,
            "channels": [c.value for c in self.channels], "priority": self.priority.value,
            "recipients": self.recipients, "metadata": self.metadata,
            "template_id": self.template_id, "created_at": self.created_at,
            "scheduled_at": self.scheduled_at, "tags": self.tags,
        }


@dataclass
class DeliveryRecord:
    notification_id: str
    channel: ChannelType
    recipient: str
    status: DeliveryStatus
    sent_at: Optional[float] = None
    delivered_at: Optional[float] = None
    error_message: str = ""
    attempt_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id, "channel": self.channel.value,
            "recipient": self.recipient, "status": self.status.value,
            "sent_at": self.sent_at, "delivered_at": self.delivered_at,
            "error_message": self.error_message, "attempt_count": self.attempt_count,
        }


class NotificationRouterEngine:
    """
    Multi-channel notification router with delivery tracking and rate limiting.
    """

    def __init__(self) -> None:
        self._channels: Dict[ChannelType, Callable[[Notification, str], bool]] = {}
        self._templates: Dict[str, Callable[[Dict[str, Any]], str]] = {}
        self._queue: List[Notification] = []
        self._records: List[DeliveryRecord] = []
        self._rate_limits: Dict[str, Dict[str, Any]] = {}  # recipient -> {last_sent, count}
        self._batch_size: int = 10
        self._batch_interval: float = 30.0

    def register_channel(self, channel_type: ChannelType, sender: Callable[[Notification, str], bool]) -> None:
        self._channels[channel_type] = sender

    def register_template(self, template_id: str, renderer: Callable[[Dict[str, Any]], str]) -> None:
        self._templates[template_id] = renderer

    def _check_rate_limit(self, recipient: str, channel: ChannelType) -> bool:
        key = f"{recipient}:{channel.value}"
        now = time.time()
        window = self._rate_limits.get(key, {"last_sent": 0, "count": 0, "window_start": now})
        if now - window["window_start"] > 60:
            window = {"last_sent": 0, "count": 0, "window_start": now}
        if window["count"] >= 10:  # Max 10 per minute per channel
            return False
        window["count"] += 1
        window["last_sent"] = now
        self._rate_limits[key] = window
        return True

    def _render(self, notification: Notification) -> str:
        if notification.template_id and notification.template_id in self._templates:
            return self._templates[notification.template_id](notification.metadata)
        return notification.body

    def send(self, notification: Notification) -> List[DeliveryRecord]:
        records = []
        body = self._render(notification)
        notif = Notification(
            id=notification.id, title=notification.title, body=body,
            channels=notification.channels, priority=notification.priority,
            recipients=notification.recipients, metadata=notification.metadata,
            template_id=notification.template_id, created_at=notification.created_at,
            scheduled_at=notification.scheduled_at, tags=notification.tags,
        )

        for channel in notif.channels:
            sender = self._channels.get(channel)
            if not sender:
                continue
            for recipient in notif.recipients:
                if not self._check_rate_limit(recipient, channel):
                    record = DeliveryRecord(
                        notification_id=notif.id, channel=channel, recipient=recipient,
                        status=DeliveryStatus.SUPPRESSED, error_message="Rate limit exceeded"
                    )
                    records.append(record)
                    continue

                record = DeliveryRecord(
                    notification_id=notif.id, channel=channel, recipient=recipient,
                    status=DeliveryStatus.SENT, sent_at=time.time()
                )
                try:
                    success = sender(notif, recipient)
                    if success:
                        record.status = DeliveryStatus.DELIVERED
                        record.delivered_at = time.time()
                    else:
                        record.status = DeliveryStatus.FAILED
                        record.error_message = "Sender returned false"
                except Exception as e:
                    record.status = DeliveryStatus.FAILED
                    record.error_message = str(e)
                record.attempt_count = 1
                records.append(record)
                self._records.append(record)
        return records

    def queue(self, notification: Notification) -> None:
        self._queue.append(notification)
        self._queue.sort(key=lambda n: n.priority.value, reverse=True)

    def flush_queue(self) -> List[DeliveryRecord]:
        all_records = []
        for notification in self._queue:
            records = self.send(notification)
            all_records.extend(records)
        self._queue.clear()
        return all_records

    def get_records(self, notification_id: Optional[str] = None, status: Optional[DeliveryStatus] = None) -> List[DeliveryRecord]:
        records = self._records
        if notification_id:
            records = [r for r in records if r.notification_id == notification_id]
        if status:
            records = [r for r in records if r.status == status]
        return records

    def get_stats(self) -> Dict[str, Any]:
        by_channel: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        for r in self._records:
            by_channel[r.channel.value] = by_channel.get(r.channel.value, 0) + 1
            by_status[r.status.value] = by_status.get(r.status.value, 0) + 1
        return {
            "total_records": len(self._records),
            "queued": len(self._queue),
            "by_channel": by_channel,
            "by_status": by_status,
        }

    def export_records(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self._records], f, indent=2, default=str)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Notification Router Engine")
    print("=" * 60)

    engine = NotificationRouterEngine()

    # Register channel senders
    def email_sender(notification: Notification, recipient: str) -> bool:
        print(f"  [EMAIL] To: {recipient} | Subject: {notification.title}")
        return True

    def webhook_sender(notification: Notification, recipient: str) -> bool:
        print(f"  [WEBHOOK] To: {recipient} | Body: {notification.body[:50]}")
        return True

    def slack_sender(notification: Notification, recipient: str) -> bool:
        print(f"  [SLACK] Channel: {recipient} | {notification.title}")
        return True

    engine.register_channel(ChannelType.EMAIL, email_sender)
    engine.register_channel(ChannelType.WEBHOOK, webhook_sender)
    engine.register_channel(ChannelType.SLACK, slack_sender)

    # Register template
    def alert_template(data: Dict[str, Any]) -> str:
        return f"ALERT: {data.get('severity', 'UNKNOWN')} - {data.get('message', 'No message')}"

    engine.register_template("alert_template", alert_template)

    print("\n--- Send notification ---")
    notif1 = Notification(
        id="n1", title="System Alert", body="", channels=[ChannelType.EMAIL, ChannelType.SLACK],
        priority=NotificationPriority.HIGH, recipients=["admin@example.com", "#alerts"],
        template_id="alert_template", metadata={"severity": "CRITICAL", "message": "CPU usage 95%"}
    )
    records = engine.send(notif1)
    for r in records:
        print(f"  {r.channel.value} -> {r.recipient}: {r.status.value}")

    print("\n--- Queue and flush ---")
    notif2 = Notification(
        id="n2", title="Daily Report", body="Daily metrics summary", channels=[ChannelType.EMAIL],
        priority=NotificationPriority.NORMAL, recipients=["team@example.com"]
    )
    notif3 = Notification(
        id="n3", title="Emergency", body="Service down!", channels=[ChannelType.WEBHOOK, ChannelType.EMAIL],
        priority=NotificationPriority.EMERGENCY, recipients=["pager@example.com", "https://hooks.example.com"]
    )
    engine.queue(notif2)
    engine.queue(notif3)
    engine.flush_queue()

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nNotification Router test complete.")


if __name__ == "__main__":
    run()
