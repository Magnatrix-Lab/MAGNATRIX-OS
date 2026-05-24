#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Browser Engine (Layer 7 Extension)
CDP-Based Headless Browser with DOM Extraction, Network Intercept, Screenshot
================================================================================
Zero-dependency browser automation using raw DevTools Protocol over websocket.
================================================================================
"""
from __future__ import annotations

import base64
import hashlib
import json
import socket
import struct
import threading
import time
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# =============================================================================
# Constants
# =============================================================================
DEFAULT_CDP_HOST = "127.0.0.1"
DEFAULT_CDP_PORT = 9222
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


# =============================================================================
# Data Types
# =============================================================================
@dataclass
class PageInfo:
    target_id: str
    title: str
    url: str
    ws_debugger_url: str = ""


@dataclass
class DOMNode:
    node_id: int
    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    text: str = ""
    children: List[DOMNode] = field(default_factory=list)


@dataclass
class NetworkRequest:
    request_id: str
    url: str
    method: str
    headers: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# WebSocket Frame Parser (RFC 6455)
# =============================================================================
class WSFrame:
    def __init__(self, opcode: int = 0x1, payload: bytes = b"", masked: bool = False) -> None:
        self.opcode = opcode
        self.payload = payload
        self.masked = masked

    def to_bytes(self) -> bytes:
        length = len(self.payload)
        header = self.opcode | (0x80 if self.masked else 0x00)
        if length < 126:
            buf = struct.pack("BB", header, length | (0x80 if self.masked else 0))
        elif length < 65536:
            buf = struct.pack("!BBH", header, 126 | (0x80 if self.masked else 0), length)
        else:
            buf = struct.pack("!BBQ", header, 127 | (0x80 if self.masked else 0), length)
        if self.masked:
            mask_key = struct.pack("I", int(time.time() * 1000) & 0xFFFFFFFF)
            masked_payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(self.payload))
            return buf + mask_key + masked_payload
        return buf + self.payload

    @classmethod
    def parse(cls, data: bytes) -> Tuple[Optional[WSFrame], bytes]:
        if len(data) < 2:
            return None, data
        header = data[0]
        opcode = header & 0x0F
        masked = bool(data[1] & 0x80)
        length = data[1] & 0x7F
        offset = 2
        if length == 126:
            if len(data) < 4:
                return None, data
            length = struct.unpack("!H", data[2:4])[0]
            offset = 4
        elif length == 127:
            if len(data) < 10:
                return None, data
            length = struct.unpack("!Q", data[2:10])[0]
            offset = 10
        if masked:
            if len(data) < offset + 4:
                return None, data
            mask_key = data[offset:offset + 4]
            offset += 4
        if len(data) < offset + length:
            return None, data
        payload = data[offset:offset + length]
        if masked:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return cls(opcode, payload, masked), data[offset + length:]


# =============================================================================
# CDP Connection
# =============================================================================
class CDPConnection:
    """Raw CDP websocket connection to Chrome DevTools."""

    def __init__(self, ws_url: str) -> None:
        self.ws_url = ws_url
        self._sock: Optional[socket.socket] = None
        self._buffer = b""
        self._msg_id = 0
        self._callbacks: Dict[int, Callable[[Dict[str, Any]], None]] = {}
        self._event_handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def _connect(self) -> None:
        parsed = urllib.parse.urlparse(self.ws_url)
        host = parsed.hostname or DEFAULT_CDP_HOST
        port = parsed.port or DEFAULT_CDP_PORT
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(10.0)
        self._sock.connect((host, port))
        # HTTP upgrade
        path = parsed.path or "/"
        key = base64.b64encode(os.urandom(16)).decode()
        headers = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self._sock.sendall(headers.encode())
        resp = self._sock.recv(4096)
        if b"101" not in resp:
            raise ConnectionError(f"CDP WS handshake failed: {resp[:200]}")

    def send(self, method: str, params: Optional[Dict[str, Any]] = None, callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> int:
        with self._lock:
            self._msg_id += 1
            msg_id = self._msg_id
        payload = json.dumps({"id": msg_id, "method": method, "params": params or {}}, default=str)
        frame = WSFrame(opcode=0x1, payload=payload.encode())
        if callback:
            self._callbacks[msg_id] = callback
        if self._sock:
            self._sock.sendall(frame.to_bytes())
        return msg_id

    def on_event(self, event: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._event_handlers.setdefault(event, []).append(handler)

    def _read_loop(self) -> None:
        while self._running and self._sock:
            try:
                data = self._sock.recv(65536)
                if not data:
                    break
                self._buffer += data
                while True:
                    frame, self._buffer = WSFrame.parse(self._buffer)
                    if frame is None:
                        break
                    if frame.opcode == 0x1:
                        try:
                            msg = json.loads(frame.payload.decode("utf-8"))
                            if "id" in msg and msg["id"] in self._callbacks:
                                cb = self._callbacks.pop(msg["id"])
                                cb(msg)
                            elif "method" in msg:
                                for h in self._event_handlers.get(msg["method"], []):
                                    h(msg.get("params", {}))
                        except Exception:
                            pass
                    elif frame.opcode == 0x8:
                        break
            except Exception:
                break
        self._running = False

    def start(self) -> None:
        self._connect()
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.sendall(WSFrame(opcode=0x8, payload=b"").to_bytes())
            except Exception:
                pass
            self._sock.close()
            self._sock = None


# =============================================================================
# Page Controller
# =============================================================================
class PageController:
    """Navigate, reload, evaluate on a CDP page."""

    def __init__(self, cdp: CDPConnection) -> None:
        self.cdp = cdp
        self._current_url = ""

    def navigate(self, url: str, wait_load: bool = True, timeout: float = 30.0) -> bool:
        loaded = threading.Event()
        def on_load(_: Dict[str, Any]) -> None:
            loaded.set()
        if wait_load:
            self.cdp.on_event("Page.loadEventFired", on_load)
        self.cdp.send("Page.enable")
        self.cdp.send("Runtime.enable")
        self.cdp.send("Page.navigate", {"url": url})
        self._current_url = url
        if wait_load:
            return loaded.wait(timeout)
        return True

    def reload(self, ignore_cache: bool = False) -> None:
        self.cdp.send("Page.reload", {"ignoreCache": ignore_cache})

    def evaluate(self, expression: str) -> Any:
        result: Dict[str, Any] = {}
        def cb(msg: Dict[str, Any]) -> None:
            result.update(msg)
        self.cdp.send("Runtime.evaluate", {"expression": expression, "returnByValue": True}, cb)
        # Simple blocking wait for demo purposes
        time.sleep(0.2)
        return result.get("result", {}).get("value")

    def set_viewport(self, width: int, height: int, device_scale: float = 1.0) -> None:
        self.cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": width,
            "height": height,
            "deviceScaleFactor": device_scale,
            "mobile": False,
        })


# =============================================================================
# DOM Extractor
# =============================================================================
class DOMExtractor:
    """Extract DOM tree and text content via CDP."""

    def __init__(self, cdp: CDPConnection) -> None:
        self.cdp = cdp

    def get_document(self, callback: Optional[Callable[[DOMNode], None]] = None) -> Optional[DOMNode]:
        result: Dict[str, Any] = {}
        def cb(msg: Dict[str, Any]) -> None:
            result.update(msg)
        self.cdp.send("DOM.getDocument", {"depth": -1, "pierce": True}, cb)
        time.sleep(0.2)
        root = result.get("result", {}).get("root", {})
        return self._parse_node(root) if root else None

    def _parse_node(self, raw: Dict[str, Any]) -> DOMNode:
        attrs: Dict[str, str] = {}
        attr_list = raw.get("attributes", [])
        for i in range(0, len(attr_list), 2):
            if i + 1 < len(attr_list):
                attrs[attr_list[i]] = attr_list[i + 1]
        children = [self._parse_node(c) for c in raw.get("children", [])]
        return DOMNode(
            node_id=raw.get("nodeId", 0),
            tag=raw.get("nodeName", "").lower(),
            attributes=attrs,
            text=raw.get("nodeValue", ""),
            children=children,
        )

    def query_selector(self, selector: str) -> Optional[DOMNode]:
        js = f"document.querySelector({json.dumps(selector)}).outerHTML"
        html = self._evaluate_blocking(js)
        if html:
            return DOMNode(node_id=0, tag="fragment", text=html)
        return None

    def query_selector_all(self, selector: str) -> List[DOMNode]:
        js = f"JSON.stringify(Array.from(document.querySelectorAll({json.dumps(selector)})).map(e => e.outerHTML))"
        result = self._evaluate_blocking(js)
        if result:
            try:
                htmls = json.loads(result)
                return [DOMNode(node_id=i, tag="fragment", text=h) for i, h in enumerate(htmls)]
            except Exception:
                pass
        return []

    def _evaluate_blocking(self, expression: str) -> Any:
        result: Dict[str, Any] = {}
        def cb(msg: Dict[str, Any]) -> None:
            result.update(msg)
        self.cdp.send("Runtime.evaluate", {"expression": expression, "returnByValue": True}, cb)
        time.sleep(0.2)
        return result.get("result", {}).get("value")


# =============================================================================
# Network Interceptor
# =============================================================================
class NetworkInterceptor:
    """Intercept and modify network requests via CDP Fetch domain."""

    def __init__(self, cdp: CDPConnection) -> None:
        self.cdp = cdp
        self._patterns: List[str] = []
        self._handlers: Dict[str, Callable[[NetworkRequest], Optional[Dict[str, Any]]]] = {}

    def enable(self) -> None:
        self.cdp.send("Fetch.enable", {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]})
        self.cdp.on_event("Fetch.requestPaused", self._on_paused)

    def disable(self) -> None:
        self.cdp.send("Fetch.disable")

    def _on_paused(self, params: Dict[str, Any]) -> None:
        req = NetworkRequest(
            request_id=params.get("requestId", ""),
            url=params.get("request", {}).get("url", ""),
            method=params.get("request", {}).get("method", "GET"),
            headers=params.get("request", {}).get("headers", {}),
        )
        handler = self._handlers.get("*")
        if handler:
            override = handler(req)
            if override:
                self.cdp.send("Fetch.continueRequest", {
                    "requestId": req.request_id,
                    **override,
                })
            else:
                self.cdp.send("Fetch.continueRequest", {"requestId": req.request_id})
        else:
            self.cdp.send("Fetch.continueRequest", {"requestId": req.request_id})

    def on_request(self, pattern: str, handler: Callable[[NetworkRequest], Optional[Dict[str, Any]]]) -> None:
        self._handlers[pattern] = handler


# =============================================================================
# Screenshot Engine
# =============================================================================
class ScreenshotEngine:
    """Capture screenshots via CDP Page.captureScreenshot."""

    def __init__(self, cdp: CDPConnection) -> None:
        self.cdp = cdp

    def capture(self, format: str = "png", full_page: bool = False, callback: Optional[Callable[[bytes], None]] = None) -> Optional[bytes]:
        params: Dict[str, Any] = {"format": format}
        if full_page:
            params["captureBeyondViewport"] = True
        result: Dict[str, Any] = {}
        def cb(msg: Dict[str, Any]) -> None:
            result.update(msg)
        self.cdp.send("Page.captureScreenshot", params, cb)
        time.sleep(0.3)
        data = result.get("result", {}).get("data", "")
        if data:
            img = base64.b64decode(data)
            if callback:
                callback(img)
            return img
        return None

    def save_to(self, path: str, format: str = "png", full_page: bool = False) -> bool:
        img = self.capture(format, full_page)
        if img:
            Path(path).write_bytes(img)
            return True
        return False


# =============================================================================
# Cookie Jar
# =============================================================================
class CookieJar:
    """Manage cookies via CDP Network domain."""

    def __init__(self, cdp: CDPConnection) -> None:
        self.cdp = cdp

    def get_all(self, callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None) -> List[Dict[str, Any]]:
        result: Dict[str, Any] = {}
        def cb(msg: Dict[str, Any]) -> None:
            result.update(msg)
        self.cdp.send("Network.getAllCookies", {}, cb)
        time.sleep(0.2)
        cookies = result.get("result", {}).get("cookies", [])
        if callback:
            callback(cookies)
        return cookies

    def set(self, name: str, value: str, domain: str, path: str = "/") -> None:
        self.cdp.send("Network.setCookie", {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
        })

    def delete(self, name: str, domain: str) -> None:
        self.cdp.send("Network.deleteCookies", {"name": name, "domain": domain})


# =============================================================================
# Proxy Manager
# =============================================================================
class ProxyManager:
    """Route browser traffic through SOCKS/HTTP proxies."""

    def __init__(self) -> None:
        self._proxy: Optional[str] = None
        self._bypass: List[str] = []

    def set_proxy(self, proxy_url: str) -> None:
        self._proxy = proxy_url

    def bypass(self, pattern: str) -> None:
        self._bypass.append(pattern)

    def to_cdp_args(self) -> List[str]:
        args: List[str] = []
        if self._proxy:
            parsed = urllib.parse.urlparse(self._proxy)
            if parsed.scheme in ("http", "https"):
                args.append(f"--proxy-server={self._proxy}")
            elif parsed.scheme == "socks5":
                args.append(f"--proxy-server=socks5://{parsed.hostname}:{parsed.port}")
        return args


# =============================================================================
# Browser Engine Kernel Bridge
# =============================================================================
class BrowserEngineKernelBridge:
    def __init__(self, controller: PageController, extractor: DOMExtractor, event_bus: Any = None) -> None:
        self.controller = controller
        self.extractor = extractor
        self.bus = event_bus

    def navigate_and_extract(self, url: str, selectors: List[str]) -> Dict[str, Any]:
        self.controller.navigate(url)
        results: Dict[str, Any] = {"url": url, "selectors": {}}
        for sel in selectors:
            nodes = self.extractor.query_selector_all(sel)
            results["selectors"][sel] = [n.text for n in nodes]
        if self.bus:
            self.bus.publish("browser.extracted", results)
        return results


# =============================================================================
# Browser Engine
# =============================================================================
class BrowserEngine:
    """Top-level orchestrator for CDP-based browser automation."""

    def __init__(self, cdp_ws_url: str) -> None:
        self.cdp = CDPConnection(cdp_ws_url)
        self.controller = PageController(self.cdp)
        self.extractor = DOMExtractor(self.cdp)
        self.network = NetworkInterceptor(self.cdp)
        self.screenshot = ScreenshotEngine(self.cdp)
        self.cookies = CookieJar(self.cdp)
        self.proxy = ProxyManager()
        self.bridge = BrowserEngineKernelBridge(self.controller, self.extractor)
        self._running = False

    def start(self) -> None:
        self.cdp.start()
        self._running = True

    def stop(self) -> None:
        self._running = False
        self.cdp.stop()

    def navigate(self, url: str) -> bool:
        return self.controller.navigate(url)

    def extract(self, selectors: List[str]) -> Dict[str, Any]:
        return self.bridge.navigate_and_extract(self.controller._current_url, selectors)

    def screenshot_to(self, path: str) -> bool:
        return self.screenshot.save_to(path)

    def __enter__(self) -> BrowserEngine:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Browser Engine Demo (stub — requires Chrome)")
    print("=" * 60)
    print("BrowserEngine orchestrates:")
    print("  - CDPConnection (raw WS to Chrome)")
    print("  - PageController (navigate, reload, evaluate)")
    print("  - DOMExtractor (querySelector, tree parse)")
    print("  - NetworkInterceptor (requestPaused)")
    print("  - ScreenshotEngine (captureScreenshot)")
    print("  - CookieJar (getAllCookies, setCookie)")
    print("  - ProxyManager (CLI args generation)")
    print("Demo complete — start Chrome with --remote-debugging-port=9222 to use.")


if __name__ == "__main__":
    run_demo()
