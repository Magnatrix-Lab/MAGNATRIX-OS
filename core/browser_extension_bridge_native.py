
"""
browser_extension_bridge_native.py
MAGNATRIX-OS — Browser Extension Bridge

Native Messaging / WebSocket bridge for communicating with
browser extensions (Chrome, Firefox, Edge). Inspired by Hermes
browser extension side-panel integration.

Pure Python standard library.
"""

import json
import struct
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum, auto


class MessageType(Enum):
    QUERY = auto()
    RESPONSE = auto()
    EVENT = auto()
    COMMAND = auto()
    ERROR = auto()


@dataclass
class ExtensionMessage:
    msg_type: str
    payload: Dict[str, Any]
    timestamp: str
    request_id: Optional[str] = None


class BrowserExtensionBridge:
    """Bridge for native messaging with browser extensions."""

    def __init__(self, extension_id: str = "magnatrix.os"):
        self.extension_id = extension_id
        self.handlers: Dict[str, Callable] = {}
        self.message_queue: List[ExtensionMessage] = []
        self._callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._running = False

    def register_handler(self, msg_type: str, handler: Callable) -> None:
        self.handlers[msg_type] = handler

    def send_native_message(self, message: Dict) -> None:
        """Send message to browser via native messaging protocol."""
        encoded = json.dumps(message).encode("utf-8")
        length = struct.pack("@I", len(encoded))
        try:
            import sys
            sys.stdout.buffer.write(length)
            sys.stdout.buffer.write(encoded)
            sys.stdout.buffer.flush()
        except Exception:
            pass

    def read_native_message(self) -> Optional[Dict]:
        """Read message from browser via native messaging protocol."""
        try:
            import sys
            raw_length = sys.stdin.buffer.read(4)
            if len(raw_length) == 0:
                return None
            length = struct.unpack("@I", raw_length)[0]
            message = sys.stdin.buffer.read(length).decode("utf-8")
            return json.loads(message)
        except Exception:
            return None

    def process_message(self, raw_message: Dict) -> Optional[Dict]:
        msg_type = raw_message.get("type", "unknown")
        handler = self.handlers.get(msg_type)
        if handler:
            try:
                return handler(raw_message)
            except Exception as e:
                return {"type": "error", "error": str(e)}
        return {"type": "error", "error": f"No handler for type: {msg_type}"}

    def build_tab_message(self, tab_info: Dict) -> ExtensionMessage:
        return ExtensionMessage(
            msg_type="tab_update",
            payload=tab_info,
            timestamp=datetime.now().isoformat(),
        )

    def build_summary_request(self, tab_ids: List[str]) -> ExtensionMessage:
        return ExtensionMessage(
            msg_type="summarize",
            payload={"tab_ids": tab_ids},
            timestamp=datetime.now().isoformat(),
        )

    def build_quick_command(self, command: str, tab_id: Optional[str] = None) -> ExtensionMessage:
        return ExtensionMessage(
            msg_type="quick_command",
            payload={"command": command, "tab_id": tab_id},
            timestamp=datetime.now().isoformat(),
        )

    def to_dict(self) -> Dict:
        return {
            "extension_id": self.extension_id,
            "registered_handlers": list(self.handlers.keys()),
            "queue_size": len(self.message_queue),
        }


__all__ = ["BrowserExtensionBridge", "ExtensionMessage", "MessageType"]
