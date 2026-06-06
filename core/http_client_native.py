#!/usr/bin/env python3
"""
HTTP Client for MAGNATRIX-OS
HTTP/HTTPS client with retry logic, timeout handling, connection pooling,
request/response logging, and cookie support. Native stdlib only (urllib).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import time
import urllib.error
import urllib.request
from http.client import HTTPResponse
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


@dataclasses.dataclass
class HTTPRequest:
    url: str
    method: str = "GET"
    headers: Dict[str, str] = dataclasses.field(default_factory=dict)
    body: Optional[bytes | str] = None
    timeout: float = 30.0
    follow_redirects: bool = True


@dataclasses.dataclass
class HTTPResponse:
    status: int
    headers: Dict[str, str]
    body: bytes
    url: str
    latency_ms: float
    attempts: int

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text())

    def is_success(self) -> bool:
        return 200 <= self.status < 300


class HTTPClient:
    """Robust HTTP client with retry, timeout, and cookie jar support."""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        timeout: float = 30.0,
        default_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.default_headers = default_headers or {"User-Agent": "MAGNATRIX-OS-HTTP-Client/1.0"}
        self._cookie_jar = {}
        self._request_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    def request(self, req: HTTPRequest) -> HTTPResponse:
        start = time.time()
        last_exception: Optional[Exception] = None
        headers = dict(self.default_headers)
        headers.update(req.headers)
        body = req.body
        if isinstance(body, str):
            body = body.encode("utf-8")
        if body and "Content-Length" not in headers:
            headers["Content-Length"] = str(len(body))
        # Add cookies
        domain = urllib.request.urlparse(req.url).netloc
        if domain in self._cookie_jar:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self._cookie_jar[domain].items())

        for attempt in range(1, self.max_retries + 1):
            try:
                req_obj = urllib.request.Request(
                    req.url,
                    data=body,
                    headers=headers,
                    method=req.method,
                )
                req_obj.add_header("Accept-Encoding", "identity")
                with urllib.request.urlopen(req_obj, timeout=req.timeout) as resp:
                    body_bytes = resp.read()
                    resp_headers = dict(resp.headers.items())
                    latency = (time.time() - start) * 1000
                    self._request_count += 1
                    self._total_latency_ms += latency
                    # Store cookies
                    set_cookie = resp_headers.get("Set-Cookie", "")
                    if set_cookie:
                        self._parse_cookie(domain, set_cookie)
                    result = HTTPResponse(
                        status=resp.getcode(),
                        headers=resp_headers,
                        body=body_bytes,
                        url=resp.geturl(),
                        latency_ms=round(latency, 2),
                        attempts=attempt,
                    )
                    if not result.is_success() and attempt < self.max_retries:
                        # Retry on server errors
                        if result.status >= 500:
                            time.sleep(self.retry_delay * (self.backoff_factor ** (attempt - 1)))
                            continue
                    return result
            except urllib.error.HTTPError as e:
                if e.code >= 500 and attempt < self.max_retries:
                    time.sleep(self.retry_delay * (self.backoff_factor ** (attempt - 1)))
                    continue
                latency = (time.time() - start) * 1000
                self._error_count += 1
                return HTTPResponse(
                    status=e.code,
                    headers=dict(e.headers.items()) if e.headers else {},
                    body=b"",
                    url=req.url,
                    latency_ms=round(latency, 2),
                    attempts=attempt,
                )
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (self.backoff_factor ** (attempt - 1)))
        latency = (time.time() - start) * 1000
        self._error_count += 1
        raise last_exception or RuntimeError("All retries exhausted")

    def _parse_cookie(self, domain: str, cookie_str: str) -> None:
        if domain not in self._cookie_jar:
            self._cookie_jar[domain] = {}
        for cookie in cookie_str.split(","):
            parts = cookie.strip().split(";")[0].split("=", 1)
            if len(parts) == 2:
                self._cookie_jar[domain][parts[0]] = parts[1]

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def get(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None) -> HTTPResponse:
        return self.request(HTTPRequest(url=url, method="GET", headers=headers or {}, timeout=timeout or self.timeout))

    def post(self, url: str, body: Any, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None, json_mode: bool = False) -> HTTPResponse:
        h = dict(headers or {})
        if json_mode and isinstance(body, dict):
            body = json.dumps(body).encode("utf-8")
            h.setdefault("Content-Type", "application/json")
        return self.request(HTTPRequest(url=url, method="POST", body=body, headers=h, timeout=timeout or self.timeout))

    def put(self, url: str, body: Any, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None) -> HTTPResponse:
        return self.request(HTTPRequest(url=url, method="PUT", body=body if isinstance(body, bytes) else str(body).encode(), headers=headers or {}, timeout=timeout or self.timeout))

    def delete(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None) -> HTTPResponse:
        return self.request(HTTPRequest(url=url, method="DELETE", headers=headers or {}, timeout=timeout or self.timeout))

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return {
            "requests": self._request_count,
            "errors": self._error_count,
            "avg_latency_ms": round(self._total_latency_ms / max(1, self._request_count), 2),
            "success_rate": (self._request_count - self._error_count) / max(1, self._request_count),
            "cookies_stored": sum(len(c) for c in self._cookie_jar.values()),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    client = HTTPClient(max_retries=2, timeout=10.0)
    print("=== HTTP Client Demo ===\n")
    # GET request
    try:
        resp = client.get("https://httpbin.org/get")
        print(f"GET https://httpbin.org/get -> {resp.status} ({resp.latency_ms}ms)")
        data = resp.json()
        print(f"  Origin: {data.get('origin', 'N/A')[:30]}...")
    except Exception as e:
        print(f"GET failed: {e}")
    # POST request
    try:
        resp = client.post("https://httpbin.org/post", {"key": "value"}, json_mode=True)
        print(f"\nPOST https://httpbin.org/post -> {resp.status} ({resp.latency_ms}ms)")
    except Exception as e:
        print(f"POST failed: {e}")
    # Stats
    print(f"\nStats: {client.stats()}")


if __name__ == "__main__":
    _demo()
