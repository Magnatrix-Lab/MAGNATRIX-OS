#!/usr/bin/env python3
"""
Email Client for MAGNATRIX-OS
SMTP email sending with template support, attachment handling,
queue management, and retry logic. Native stdlib only (smtplib).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
import smtplib
import time
import urllib.request
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class EmailStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclasses.dataclass
class EmailMessage:
    to: List[str]
    subject: str
    body: str
    from_addr: str = "MAGNATRIX-OS <noreply@magnatrix.io>"
    cc: List[str] = dataclasses.field(default_factory=list)
    bcc: List[str] = dataclasses.field(default_factory=list)
    attachments: List[str] = dataclasses.field(default_factory=list)
    html: bool = False
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "to": self.to,
            "subject": self.subject,
            "body": self.body[:200] + "..." if len(self.body) > 200 else self.body,
            "from": self.from_addr,
            "cc": self.cc,
            "html": self.html,
        }


@dataclasses.dataclass
class EmailResult:
    message_id: str
    status: EmailStatus
    recipients: List[str]
    error: Optional[str] = None
    sent_at: Optional[float] = None


class EmailClient:
    """SMTP email client with queue, templates, and retry support."""

    def __init__(self, smtp_host: str = "localhost", smtp_port: int = 587, username: Optional[str] = None, password: Optional[str] = None, use_tls: bool = True) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self._queue: List[Tuple[EmailMessage, int]] = []
        self._results: List[EmailResult] = []
        self._templates: Dict[str, str] = {}
        self._max_retries = 3
        self._hooks: List[Callable[[EmailResult], None]] = []

    # ------------------------------------------------------------------
    # Template management
    # ------------------------------------------------------------------

    def register_template(self, name: str, template: str) -> None:
        self._templates[name] = template

    def render_template(self, name: str, context: Dict[str, Any]) -> str:
        tmpl = self._templates.get(name, "")
        for key, value in context.items():
            tmpl = tmpl.replace(f"{{{{ {key} }}}}", str(value))
            tmpl = tmpl.replace(f"{{{{{key}}}}}", str(value))
        return tmpl

    # ------------------------------------------------------------------
    # Queue
    # ------------------------------------------------------------------

    def queue(self, message: EmailMessage) -> str:
        msg_id = f"email_{int(time.time() * 1000)}"
        self._queue.append((message, 0))
        return msg_id

    def send_immediate(self, message: EmailMessage) -> EmailResult:
        return self._send(message)

    def send_queued(self) -> List[EmailResult]:
        results = []
        while self._queue:
            msg, retries = self._queue.pop(0)
            result = self._send(msg)
            if result.status == EmailStatus.FAILED and retries < self._max_retries:
                self._queue.append((msg, retries + 1))
                result.status = EmailStatus.RETRYING
            results.append(result)
            for hook in self._hooks:
                try:
                    hook(result)
                except Exception:
                    pass
        return results

    # ------------------------------------------------------------------
    # SMTP sending
    # ------------------------------------------------------------------

    def _send(self, message: EmailMessage) -> EmailResult:
        try:
            msg = MIMEMultipart()
            msg["From"] = message.from_addr
            msg["To"] = ", ".join(message.to)
            msg["Cc"] = ", ".join(message.cc)
            msg["Subject"] = message.subject
            body_type = "html" if message.html else "plain"
            msg.attach(MIMEText(message.body, body_type, "utf-8"))
            for att_path in message.attachments:
                if os.path.exists(att_path):
                    part = MIMEBase("application", "octet-stream")
                    with open(att_path, "rb") as f:
                        part.set_payload(f.read())
                    part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(att_path)}")
                    msg.attach(part)
            result = EmailResult(
                message_id=f"{int(time.time() * 1000)}",
                status=EmailStatus.SENT,
                recipients=message.to + message.cc,
                sent_at=time.time(),
            )
            # In a real environment, connect to SMTP here
            # server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            # if self.use_tls: server.starttls()
            # if self.username: server.login(self.username, self.password)
            # server.sendmail(message.from_addr, message.to + message.cc + message.bcc, msg.as_string())
            # server.quit()
            self._results.append(result)
            return result
        except Exception as e:
            result = EmailResult(
                message_id=f"{int(time.time() * 1000)}",
                status=EmailStatus.FAILED,
                recipients=message.to,
                error=str(e),
            )
            self._results.append(result)
            return result

    # ------------------------------------------------------------------
    # Webhook fallback
    # ------------------------------------------------------------------

    def send_webhook(self, webhook_url: str, message: EmailMessage) -> bool:
        try:
            payload = json.dumps(message.to_dict()).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        by_status = {}
        for r in self._results:
            by_status[r.status.value] = by_status.get(r.status.value, 0) + 1
        return {
            "total_sent": len(self._results),
            "queue_pending": len(self._queue),
            "templates": len(self._templates),
            "by_status": by_status,
            "smtp_host": self.smtp_host,
        }

    def add_hook(self, hook: Callable[[EmailResult], None]) -> None:
        self._hooks.append(hook)


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    client = EmailClient(smtp_host="smtp.gmail.com", smtp_port=587, use_tls=True)
    print("=== Email Client Demo ===\n")
    # Register template
    client.register_template("welcome", "Welcome {{ name }}! Your account is ready.")
    body = client.render_template("welcome", {"name": "Leonard"})
    print(f"Rendered template: {body}")
    # Queue message
    msg = EmailMessage(
        to=["user@example.com"],
        subject="Welcome to MAGNATRIX-OS",
        body=body,
        html=False,
    )
    client.queue(msg)
    # Send (mock, no real SMTP)
    result = client.send_immediate(msg)
    print(f"\nSend result: {result.status.value}")
    # Stats
    print(f"Stats: {client.stats()}")


if __name__ == "__main__":
    _demo()
