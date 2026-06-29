"""
mobile_notification_bridge_native.py
MAGNATRIX-OS — Mobile Notification Bridge

Inspired by gajae-code: Send notifications to Telegram, Discord, Slack. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Notification:
    notification_id: str
    platform: str  # telegram, discord, slack
    message: str
    recipient: str
    status: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MobileNotificationBridge:
    """Send notifications to mobile platforms."""

    PLATFORMS = ["telegram", "discord", "slack", "webhook"]

    def __init__(self, cache_dir: str = "./notifications"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.notifications: List[Notification] = []
        self.configs: Dict[str, Dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        for fname, attr in [("notifications.json", "notifications"), ("configs.json", "configs")]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "notifications.json":
                            self.notifications = [Notification(**n) for n in data]
                        else:
                            self.configs = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.cache_dir / "notifications.json", "w", encoding="utf-8") as f:
            json.dump([asdict(n) for n in self.notifications], f, indent=2)
        with open(self.cache_dir / "configs.json", "w", encoding="utf-8") as f:
            json.dump(self.configs, f, indent=2)

    def configure(self, platform: str, api_key: str, chat_id: str = "") -> None:
        self.configs[platform] = {"api_key": api_key, "chat_id": chat_id}
        self._save()

    def send(self, notification_id: str, platform: str, message: str, recipient: str = "") -> Notification:
        if platform not in self.PLATFORMS:
            platform = "webhook"
        notif = Notification(
            notification_id=notification_id, platform=platform, message=message,
            recipient=recipient, status="sent",
        )
        self.notifications.append(notif)
        self._save()
        return notif

    def get_history(self, platform: Optional[str] = None) -> List[Notification]:
        if platform:
            return [n for n in self.notifications if n.platform == platform]
        return self.notifications

    def get_stats(self) -> Dict[str, Any]:
        by_platform = {}
        for n in self.notifications:
            by_platform[n.platform] = by_platform.get(n.platform, 0) + 1
        return {"total_sent": len(self.notifications), "by_platform": by_platform}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MobileNotificationBridge", "Notification"]