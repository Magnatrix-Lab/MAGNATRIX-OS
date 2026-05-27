#!/usr/bin/env python3
"""
MAGNATRIX-OS Chat Bridge Native
Unified chat integration: Telegram, Discord, Slack, WhatsApp.
Pure Python stdlib + requests/urllib.
"""
import json, urllib.request, urllib.error, urllib.parse, time, threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass


@dataclass
class ChatConfig:
    platform: str
    token: str = ""
    webhook_url: str = ""
    api_base: str = ""
    chat_id: str = ""


class ChatAdapter:
    """Base chat adapter."""

    def __init__(self, config: ChatConfig):
        self.config = config

    def send(self, message: str, channel: str = None) -> bool:
        raise NotImplementedError

    def receive(self) -> List[Dict]:
        raise NotImplementedError

    def _http_post(self, url: str, data: Dict, headers: Dict = None) -> Dict:
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers=headers or {}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}

    def _http_get(self, url: str, headers: Dict = None) -> Dict:
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}


class TelegramAdapter(ChatAdapter):
    """Telegram Bot API adapter."""

    def __init__(self, config: ChatConfig):
        super().__init__(config)
        self.base = f"https://api.telegram.org/bot{config.token}"

    def send(self, message: str, channel: str = None) -> bool:
        chat_id = channel or self.config.chat_id
        result = self._http_post(
            f"{self.base}/sendMessage",
            {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
        )
        return "error" not in result

    def receive(self) -> List[Dict]:
        result = self._http_get(f"{self.base}/getUpdates")
        return result.get("result", [])


class DiscordAdapter(ChatAdapter):
    """Discord Webhook adapter."""

    def send(self, message: str, channel: str = None) -> bool:
        result = self._http_post(
            self.config.webhook_url,
            {"content": message},
            {"Content-Type": "application/json"},
        )
        return "error" not in result

    def receive(self) -> List[Dict]:
        return []  # Webhooks are inbound only


class SlackAdapter(ChatAdapter):
    """Slack Webhook/RTM adapter."""

    def send(self, message: str, channel: str = None) -> bool:
        result = self._http_post(
            self.config.webhook_url,
            {"text": message},
            {"Content-Type": "application/json", "Authorization": f"Bearer {self.config.token}"},
        )
        return "error" not in result

    def receive(self) -> List[Dict]:
        return []


class WhatsAppAdapter(ChatAdapter):
    """WhatsApp Business API adapter (Meta Graph API)."""

    def __init__(self, config: ChatConfig):
        super().__init__(config)
        self.base = f"https://graph.facebook.com/v18.0/{config.chat_id}"

    def send(self, message: str, channel: str = None) -> bool:
        result = self._http_post(
            f"{self.base}/messages",
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": channel or "",
                "type": "text",
                "text": {"body": message},
            },
            {"Authorization": f"Bearer {self.config.token}", "Content-Type": "application/json"},
        )
        return "error" not in result

    def receive(self) -> List[Dict]:
        return []


class ChatBridgeNative:
    """Unified chat bridge orchestrator."""

    ADAPTERS = {
        "telegram": TelegramAdapter,
        "discord": DiscordAdapter,
        "slack": SlackAdapter,
        "whatsapp": WhatsAppAdapter,
    }

    def __init__(self):
        self.adapters: Dict[str, ChatAdapter] = {}
        self._message_handlers: List[Callable] = []

    def connect(self, platform: str, config: ChatConfig) -> bool:
        cls = self.ADAPTERS.get(platform)
        if not cls:
            return False
        self.adapters[platform] = cls(config)
        return True

    def send(self, platform: str, message: str, channel: str = None) -> bool:
        adapter = self.adapters.get(platform)
        if not adapter:
            return False
        return adapter.send(message, channel)

    def broadcast(self, message: str, channel: str = None) -> Dict[str, bool]:
        results = {}
        for platform, adapter in self.adapters.items():
            results[platform] = adapter.send(message, channel)
        return results

    def on_message(self, handler: Callable):
        self._message_handlers.append(handler)

    def poll(self, platform: str) -> List[Dict]:
        adapter = self.adapters.get(platform)
        if not adapter:
            return []
        messages = adapter.receive()
        for msg in messages:
            for handler in self._message_handlers:
                try:
                    handler(platform, msg)
                except Exception:
                    pass
        return messages

    def start_polling(self, interval: float = 5.0):
        def loop():
            while True:
                for platform in self.adapters:
                    self.poll(platform)
                time.sleep(interval)
        threading.Thread(target=loop, daemon=True).start()


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS Chat Bridge Demo")
    print("=" * 60)

    bridge = ChatBridgeNative()

    # Mock configs (would be real tokens in production)
    bridge.connect("telegram", ChatConfig("telegram", "mock-token", chat_id="12345"))
    bridge.connect("discord", ChatConfig("discord", webhook_url="https://discord.com/api/webhooks/mock"))
    bridge.connect("slack", ChatConfig("slack", "mock-token", webhook_url="https://hooks.slack.com/mock"))

    print("\n[1] Sending to all platforms...")
    results = bridge.broadcast("MAGNATRIX-OS is online!")
    for platform, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"    {status} {platform}")

    print("\n[2] Polling Telegram...")
    msgs = bridge.poll("telegram")
    print(f"    Received {len(msgs)} messages")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
