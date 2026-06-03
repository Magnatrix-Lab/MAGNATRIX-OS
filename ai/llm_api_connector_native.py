"""LLM API Connector — Native Python (stdlib only)."""
from __future__ import annotations
import urllib.request, urllib.parse, json, ssl
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class HTTPMethod(Enum):
    GET = auto()
    POST = auto()
    PUT = auto()
    DELETE = auto()
    PATCH = auto()

@dataclass
class APIRequest:
    id: str
    url: str
    method: HTTPMethod = HTTPMethod.GET
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class APIResponse:
    status_code: int
    body: str
    headers: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

class APIConnector:
    def __init__(self) -> None:
        self._context = ssl._create_unverified_context()
        self._history: List[tuple] = []

    def send(self, request: APIRequest) -> APIResponse:
        try:
            data = request.body.encode("utf-8") if request.body else None
            req = urllib.request.Request(
                request.url,
                data=data,
                headers=request.headers,
                method=request.method.name
            )
            with urllib.request.urlopen(req, timeout=request.timeout, context=self._context) as resp:
                body = resp.read().decode("utf-8")
                headers = dict(resp.headers)
                self._history.append((request.id, resp.status))
                return APIResponse(resp.status, body, headers)
        except Exception as ex:
            self._history.append((request.id, 0))
            return APIResponse(0, "", error=str(ex))

    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> APIResponse:
        req = APIRequest("get_" + url, url, HTTPMethod.GET, headers or {})
        return self.send(req)

    def post(self, url: str, body: str, headers: Optional[Dict[str, str]] = None) -> APIResponse:
        req = APIRequest("post_" + url, url, HTTPMethod.POST, headers or {}, body)
        return self.send(req)

    def get_stats(self) -> Dict[str, Any]:
        success = sum(1 for _, status in self._history if status == 200)
        return {"total_requests": len(self._history), "success": success, "failure": len(self._history) - success}

def run() -> None:
    print("API Connector test")
    e = APIConnector()
    req = APIRequest("r1", "https://httpbin.org/get", HTTPMethod.GET, {"Accept": "application/json"})
    resp = e.send(req)
    print("  Status: " + str(resp.status_code))
    print("  Stats: " + str(e.get_stats()))
    print("API Connector test complete.")

if __name__ == "__main__":
    run()
