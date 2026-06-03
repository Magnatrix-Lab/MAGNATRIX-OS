"""LLM Email Scheduler — Native Python (stdlib only)."""
from __future__ import annotations
import time, heapq
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto
from datetime import datetime

@dataclass
class ScheduledEmail:
    id: str
    recipient: str
    subject: str
    body: str
    scheduled_time: float
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "ScheduledEmail") -> bool:
        if self.scheduled_time == other.scheduled_time:
            return self.priority < other.priority
        return self.scheduled_time < other.scheduled_time

class EmailScheduler:
    def __init__(self) -> None:
        self._queue: List[ScheduledEmail] = []
        self._sent: List[ScheduledEmail] = []
        self._sender: Optional[Callable[[ScheduledEmail], bool]] = None

    def set_sender(self, sender: Callable[[ScheduledEmail], bool]) -> None:
        self._sender = sender

    def schedule(self, email: ScheduledEmail) -> None:
        heapq.heappush(self._queue, email)

    def schedule_at(self, email_id: str, recipient: str, subject: str, body: str, timestamp: str, priority: int = 1) -> None:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        scheduled_time = dt.timestamp()
        email = ScheduledEmail(email_id, recipient, subject, body, scheduled_time, priority)
        self.schedule(email)

    def process_due(self) -> List[ScheduledEmail]:
        now = time.time()
        sent = []
        while self._queue and self._queue[0].scheduled_time <= now:
            email = heapq.heappop(self._queue)
            if self._sender:
                if self._sender(email):
                    self._sent.append(email)
                    sent.append(email)
            else:
                self._sent.append(email)
                sent.append(email)
        return sent

    def get_upcoming(self, n: int = 5) -> List[ScheduledEmail]:
        return sorted(self._queue, key=lambda e: e.scheduled_time)[:n]

    def cancel(self, email_id: str) -> bool:
        for i, email in enumerate(self._queue):
            if email.id == email_id:
                self._queue.pop(i)
                heapq.heapify(self._queue)
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {"scheduled": len(self._queue), "sent": len(self._sent)}

def run() -> None:
    print("Email Scheduler test")
    e = EmailScheduler()
    e.set_sender(lambda email: print("  Sending to " + email.recipient + ": " + email.subject) or True)
    e.schedule(ScheduledEmail("e1", "alice@example.com", "Hello", "Body", time.time() - 1, 1))
    e.schedule(ScheduledEmail("e2", "bob@example.com", "Reminder", "Body", time.time() + 3600, 2))
    e.schedule(ScheduledEmail("e3", "charlie@example.com", "Alert", "Body", time.time() - 2, 1))
    sent = e.process_due()
    print("  Sent: " + str(len(sent)))
    print("  Upcoming: " + str(len(e.get_upcoming())))
    print("  Stats: " + str(e.get_stats()))
    print("Email Scheduler test complete.")

if __name__ == "__main__":
    run()
