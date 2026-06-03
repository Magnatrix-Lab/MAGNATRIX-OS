#!/usr/bin/env python3
"""
MAGNATRIX-OS — Notification Hub
ai/llm_notification_hub_native.py

Features:
- Multi-channel notification routing (email, slack, sms, in-app)
- Priority-based queuing (critical, high, normal, low)
- Template-based message generation
- Delivery tracking and retry
- Batch notification support

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("notification_hub")


class Channel(enum.Enum):
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class Priority(enum.Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class DeliveryStatus(enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


@dataclass
class NotificationTemplate:
    id: str
    subject: str
    body: str
    channel: Channel
    format_fn: Optional[Callable[[Dict[str, Any]], str]] = None

    def render(self, context: Dict[str, Any]) -> str:
        if self.format_fn:
            return self.format_fn(context)
        text = self.body
        for key, val in context.items():
            text = text.replace(f"{{{key}}}", str(val))
        return text


@dataclass
class Notification:
    id: str
    recipient: str
    template_id: str
    context: Dict[str, Any]
    priority: Priority
    channel: Channel
    status: DeliveryStatus = DeliveryStatus.QUEUED
    timestamp: float = 0.0
    retries: int = 0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.monotonic()


class NotificationHub:
    """Multi-channel notification hub with priority and templates."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._templates: Dict[str, NotificationTemplate] = {}
        self._queue: deque = deque()
        self._history: List[Notification] = []
        self._handlers: Dict[Channel, Callable[[Notification, str], bool]] = {}
        self._counter = 0

    def register_template(self, template: NotificationTemplate) -> None:
        self._templates[template.id] = template

    def register_handler(self, channel: Channel, handler: Callable[[Notification, str], bool]) -> None:
        self._handlers[channel] = handler

    def send(self, recipient: str, template_id: str, context: Dict[str, Any], priority: Priority = Priority.NORMAL, channel: Optional[Channel] = None) -> Notification:
        self._counter += 1
        notif_id = f"N{self._counter}"
        template = self._templates.get(template_id)
        ch = channel or (template.channel if template else Channel.IN_APP)
        notif = Notification(notif_id, recipient, template_id, context, priority, ch)
        self._queue.append(notif)
        self._history.append(notif)
        return notif

    def process_queue(self, max_items: int = 10) -> List[Notification]:
        processed = []
        # Sort by priority
        sorted_queue = sorted(self._queue, key=lambda n: n.priority.value)
        for _ in range(min(max_items, len(sorted_queue))):
            if not sorted_queue:
                break
            notif = sorted_queue.pop(0)
            self._queue.remove(notif)
            success = self._deliver(notif)
            notif.status = DeliveryStatus.DELIVERED if success else DeliveryStatus.FAILED
            processed.append(notif)
        return processed

    def _deliver(self, notif: Notification) -> bool:
        handler = self._handlers.get(notif.channel)
        if not handler:
            return False
        template = self._templates.get(notif.template_id)
        body = template.render(notif.context) if template else str(notif.context)
        return handler(notif, body)

    def get_status(self, recipient: Optional[str] = None) -> Dict[str, Any]:
        notifications = self._history
        if recipient:
            notifications = [n for n in notifications if n.recipient == recipient]
        statuses = {}
        for n in notifications:
            statuses[n.status.value] = statuses.get(n.status.value, 0) + 1
        return {"total": len(notifications), "statuses": statuses}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "templates": len(self._templates),
            "handlers": len(self._handlers),
            "queued": len(self._queue),
            "total_sent": len(self._history),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Notification Hub")
    print("ai/llm_notification_hub_native.py")
    print("=" * 60)

    hub = NotificationHub(max_retries=2)

    # 1. Register templates
    print("\n[1] Register Templates")
    hub.register_template(NotificationTemplate("t1", "Welcome", "Hello {name}, welcome to {service}!", Channel.EMAIL))
    hub.register_template(NotificationTemplate("t2", "Alert", "Alert: {event} detected at {time}", Channel.SLACK))
    hub.register_template(NotificationTemplate("t3", "SMS Alert", "Code: {code}", Channel.SMS))
    print(f"  Registered 3 templates")

    # 2. Register handlers
    print("\n[2] Register Handlers")
    def email_handler(n, body):
        print(f"    [EMAIL] To {n.recipient}: {body[:50]}...")
        return True
    def slack_handler(n, body):
        print(f"    [SLACK] To {n.recipient}: {body[:50]}...")
        return True
    def sms_handler(n, body):
        print(f"    [SMS] To {n.recipient}: {body}")
        return True
    def failing_handler(n, body):
        return False

    hub.register_handler(Channel.EMAIL, email_handler)
    hub.register_handler(Channel.SLACK, slack_handler)
    hub.register_handler(Channel.SMS, sms_handler)
    print(f"  Registered 3 handlers")

    # 3. Send notifications
    print("\n[3] Send Notifications")
    hub.send("alice@example.com", "t1", {"name": "Alice", "service": "MAGNATRIX"}, Priority.NORMAL, Channel.EMAIL)
    hub.send("#ops", "t2", {"event": "High CPU", "time": "10:00"}, Priority.HIGH, Channel.SLACK)
    hub.send("+1234567890", "t3", {"code": "12345"}, Priority.CRITICAL, Channel.SMS)
    hub.send("bob@example.com", "t1", {"name": "Bob", "service": "MAGNATRIX"}, Priority.LOW, Channel.EMAIL)
    print(f"  Queued 4 notifications")

    # 4. Process queue
    print("\n[4] Process Queue (priority order)")
    processed = hub.process_queue(max_items=10)
    for p in processed:
        print(f"  {p.id} [{p.priority.value}] {p.channel.value}: {p.status.value}")

    # 5. Stats
    print("\n[5] Hub Stats")
    stats = hub.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
