#!/usr/bin/env python3
"""
MAGNATRIX-OS Browser Extension Native Bridge
Native messaging host for Chrome/Firefox. Two-way JSON message protocol.
"""
import sys, json, struct, os, threading, queue
from typing import Dict, Any, Optional, Callable

class BrowserExtensionBridgeNative:
    """
    Native messaging host for browser extensions.
    Protocol: 32-bit LE length prefix + JSON payload.
    """

    def __init__(self):
        self._running = False
        self._callbacks: Dict[str, Callable] = {}
        self._out_queue = queue.Queue()

    def _read_message(self) -> Optional[Dict]:
        """Read a message from stdin (from browser extension)."""
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length:
            return None
        length = struct.unpack("=I", raw_length)[0]
        message = sys.stdin.buffer.read(length).decode("utf-8")
        return json.loads(message)

    def _send_message(self, message: Dict):
        """Send a message to stdout (to browser extension)."""
        encoded = json.dumps(message).encode("utf-8")
        sys.stdout.buffer.write(struct.pack("=I", len(encoded)))
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()

    def register_handler(self, action: str, handler: Callable):
        self._callbacks[action] = handler

    def start(self):
        self._running = True
        print("[BROWSER_EXT] Native messaging host started", file=sys.stderr)
        while self._running:
            try:
                msg = self._read_message()
                if msg is None:
                    break
                action = msg.get("action")
                handler = self._callbacks.get(action)
                if handler:
                    response = handler(msg.get("payload", {}))
                    self._send_message({"id": msg.get("id"), "result": response})
                else:
                    self._send_message({"id": msg.get("id"), "error": f"Unknown action: {action}"})
            except Exception as e:
                self._send_message({"error": str(e)})

    def stop(self):
        self._running = False

    def send_to_extension(self, action: str, payload: Dict):
        """Send unsolicited message to browser extension."""
        self._send_message({"action": action, "payload": payload})


class ExtensionAPI:
    """High-level API exposed to browser extension."""

    def __init__(self):
        self.bridge = BrowserExtensionBridgeNative()
        self._setup_handlers()

    def _setup_handlers(self):
        self.bridge.register_handler("ping", lambda _: {"status": "ok", "version": "0.9.5"})
        self.bridge.register_handler("get_context", self._get_context)
        self.bridge.register_handler("query_llm", self._query_llm)
        self.bridge.register_handler("capture_page", self._capture_page)
        self.bridge.register_handler("inject_script", self._inject_script)

    def _get_context(self, payload: Dict) -> Dict:
        return {
            "url": payload.get("url"),
            "title": payload.get("title"),
            "selected_text": payload.get("selectedText"),
            "timestamp": __import__("time").time(),
        }

    def _query_llm(self, payload: Dict) -> Dict:
        prompt = payload.get("prompt", "")
        # Forward to UnifiedLLM
        return {"response": f"[LLM] {prompt[:40]}...", "model": "llama3"}

    def _capture_page(self, payload: Dict) -> Dict:
        return {"screenshot": payload.get("screenshotDataUri"), "url": payload.get("url")}

    def _inject_script(self, payload: Dict) -> Dict:
        return {"injected": True, "script": payload.get("script", "")[:100]}

    def start(self):
        self.bridge.start()


def _demo():
    print("=" * 60)
    print("Browser Extension Native Bridge Demo")
    print("=" * 60)
    print("This is a native messaging host. Run from browser extension.")
    print("Manifest: chrome-extension://<id>/")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
    # In production, start the bridge
    # ExtensionAPI().start()
