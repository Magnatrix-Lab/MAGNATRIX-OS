#!/usr/bin/env python3
"""
Subprocess Bridge for MAGNATRIX-OS
ACP-style bridge for communicating with external subprocess agents.
JSON-RPC 2.0 over NDJSON, with request/response correlation,
heartbeat, and auto-recovery. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass
class JSONRPCRequest:
    jsonrpc: str = "2.0"
    id: str = ""
    method: str = ""
    params: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"jsonrpc": self.jsonrpc, "id": self.id, "method": self.method, "params": self.params}

    def to_ndjson(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False) + "\n"


@dataclasses.dataclass
class JSONRPCResponse:
    jsonrpc: str = "2.0"
    id: str = ""
    result: Any = None
    error: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JSONRPCResponse:
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id", ""),
            result=data.get("result"),
            error=data.get("error"),
        )


@dataclasses.dataclass
class BridgeEndpoint:
    endpoint_id: str
    name: str
    command: List[str]  # subprocess command
    process: Optional[subprocess.Popen] = None
    active: bool = False
    last_heartbeat: float = 0.0
    request_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)


class SubprocessBridge:
    """ACP-style subprocess bridge with JSON-RPC over NDJSON."""

    def __init__(self, heartbeat_interval: float = 5.0, recovery_enabled: bool = True) -> None:
        self._endpoints: Dict[str, BridgeEndpoint] = {}
        self._pending: Dict[str, threading.Event] = {}  # id -> Event
        self._responses: Dict[str, JSONRPCResponse] = {}  # id -> Response
        self._callbacks: Dict[str, Callable[[JSONRPCResponse], None]] = {}
        self._heartbeat_interval = heartbeat_interval
        self._recovery_enabled = recovery_enabled
        self._running = False
        self._reader_threads: Dict[str, threading.Thread] = {}
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Endpoint management
    # ------------------------------------------------------------------

    def register(self, endpoint: BridgeEndpoint) -> None:
        self._endpoints[endpoint.endpoint_id] = endpoint

    def start_endpoint(self, endpoint_id: str) -> bool:
        ep = self._endpoints.get(endpoint_id)
        if not ep:
            return False
        if ep.process and ep.process.poll() is None:
            return True  # Already running
        try:
            ep.process = subprocess.Popen(
                ep.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            ep.active = True
            ep.last_heartbeat = time.time()
            # Start reader thread
            t = threading.Thread(target=self._read_loop, args=(endpoint_id,), daemon=True)
            t.start()
            self._reader_threads[endpoint_id] = t
            return True
        except Exception as e:
            ep.error_count += 1
            ep.active = False
            return False

    def stop_endpoint(self, endpoint_id: str) -> None:
        ep = self._endpoints.get(endpoint_id)
        if not ep or not ep.process:
            return
        ep.active = False
        try:
            ep.process.terminate()
            ep.process.wait(timeout=3)
        except Exception:
            try:
                ep.process.kill()
            except Exception:
                pass
        ep.process = None

    def _read_loop(self, endpoint_id: str) -> None:
        ep = self._endpoints[endpoint_id]
        while ep.active and ep.process and ep.process.stdout:
            try:
                line = ep.process.stdout.readline()
                if not line:
                    break
                self._handle_line(line, endpoint_id)
            except Exception:
                break
        ep.active = False

    def _handle_line(self, line: str, endpoint_id: str) -> None:
        try:
            data = json.loads(line.strip())
        except json.JSONDecodeError:
            return
        if "id" in data and "result" in data:
            resp = JSONRPCResponse.from_dict(data)
            with self._lock:
                self._responses[resp.id] = resp
                event = self._pending.pop(resp.id, None)
            if event:
                event.set()
            cb = self._callbacks.pop(resp.id, None)
            if cb:
                cb(resp)
        elif "method" in data:
            # Notification from subprocess
            pass

    # ------------------------------------------------------------------
    # JSON-RPC communication
    # ------------------------------------------------------------------

    def call(self, endpoint_id: str, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> JSONRPCResponse:
        ep = self._endpoints.get(endpoint_id)
        if not ep or not ep.active or not ep.process or not ep.process.stdin:
            return JSONRPCResponse(id="", error={"code": -32000, "message": "Endpoint not active"})
        req_id = str(uuid.uuid4())[:8]
        req = JSONRPCRequest(id=req_id, method=method, params=params or {})
        event = threading.Event()
        with self._lock:
            self._pending[req_id] = event
        try:
            ep.process.stdin.write(req.to_ndjson())
            ep.process.stdin.flush()
            ep.request_count += 1
        except Exception as e:
            with self._lock:
                self._pending.pop(req_id, None)
            ep.error_count += 1
            return JSONRPCResponse(id=req_id, error={"code": -32001, "message": str(e)})
        if event.wait(timeout=timeout):
            with self._lock:
                resp = self._responses.pop(req_id, None)
            return resp or JSONRPCResponse(id=req_id, error={"code": -32002, "message": "No response"})
        with self._lock:
            self._pending.pop(req_id, None)
        return JSONRPCResponse(id=req_id, error={"code": -32003, "message": "Timeout"})

    def notify(self, endpoint_id: str, method: str, params: Optional[Dict[str, Any]] = None) -> bool:
        ep = self._endpoints.get(endpoint_id)
        if not ep or not ep.active or not ep.process or not ep.process.stdin:
            return False
        req = JSONRPCRequest(id="", method=method, params=params or {})
        try:
            ep.process.stdin.write(req.to_ndjson())
            ep.process.stdin.flush()
            return True
        except Exception:
            return False

    def call_async(self, endpoint_id: str, method: str, params: Optional[Dict[str, Any]] = None, callback: Optional[Callable[[JSONRPCResponse], None]] = None) -> str:
        req_id = str(uuid.uuid4())[:8]
        ep = self._endpoints.get(endpoint_id)
        if not ep or not ep.active or not ep.process or not ep.process.stdin:
            if callback:
                callback(JSONRPCResponse(id=req_id, error={"code": -32000, "message": "Endpoint not active"}))
            return req_id
        req = JSONRPCRequest(id=req_id, method=method, params=params or {})
        if callback:
            self._callbacks[req_id] = callback
        try:
            ep.process.stdin.write(req.to_ndjson())
            ep.process.stdin.flush()
        except Exception as e:
            if callback:
                callback(JSONRPCResponse(id=req_id, error={"code": -32001, "message": str(e)}))
        return req_id

    # ------------------------------------------------------------------
    # Heartbeat & recovery
    # ------------------------------------------------------------------

    def start_heartbeat(self) -> None:
        self._running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        self._running = False

    def _heartbeat_loop(self) -> None:
        while self._running:
            for ep in self._endpoints.values():
                if ep.active:
                    # Check if process alive
                    if ep.process and ep.process.poll() is not None:
                        ep.active = False
                        ep.error_count += 1
                        if self._recovery_enabled:
                            self.start_endpoint(ep.endpoint_id)
                    else:
                        ep.last_heartbeat = time.time()
                        # Send ping
                        self.notify(ep.endpoint_id, "ping", {"timestamp": time.time()})
            time.sleep(self._heartbeat_interval)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        active = sum(1 for ep in self._endpoints.values() if ep.active)
        total_reqs = sum(ep.request_count for ep in self._endpoints.values())
        total_errors = sum(ep.error_count for ep in self._endpoints.values())
        return {
            "endpoints": len(self._endpoints),
            "active": active,
            "total_requests": total_reqs,
            "total_errors": total_errors,
            "pending_requests": len(self._pending),
            "recovery_enabled": self._recovery_enabled,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    bridge = SubprocessBridge(heartbeat_interval=10.0)
    print("=== Subprocess Bridge Demo ===\n")
    # Register a mock endpoint (echo command)
    bridge.register(BridgeEndpoint(
        endpoint_id="echo",
        name="Echo Agent",
        command=["python", "-c", "import sys, json; [sys.stdout.write(json.dumps({'jsonrpc':'2.0','id': json.loads(l)['id'], 'result': 'Echo: ' + json.loads(l)['method']})+'\\n') for l in sys.stdin]"],
    ))
    # Start
    ok = bridge.start_endpoint("echo")
    print(f"Start endpoint: {ok}")
    if ok:
        resp = bridge.call("echo", "hello", {"test": 1}, timeout=2.0)
        print(f"Call result: {resp.result}")
    # Stats
    print(f"\nStats: {bridge.stats()}")
    bridge.stop_endpoint("echo")


if __name__ == "__main__":
    _demo()
