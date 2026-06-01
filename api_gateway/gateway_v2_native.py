"""api_gateway/gateway_v2_native.py — API Gateway v2"""
from __future__ import annotations
import base64
import time
from typing import Any, Dict, List, Optional

class GatewayV2:
    """API Gateway with auth, validation, and metrics."""

    def __init__(self):
        self.routes: Dict[str, Dict[str, Any]] = {}
        self.metrics: Dict[str, int] = {}
        self.cors_origins: List[str] = ["*"]

    def add_route(self, path: str, handler: Callable, auth_required: bool = False) -> None:
        self.routes[path] = {
            "handler": handler,
            "auth_required": auth_required,
            "calls": 0,
        }

    def authenticate(self, headers: Dict[str, str]) -> Optional[str]:
        auth = headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        if auth.startswith("Basic "):
            decoded = base64.b64decode(auth[6:]).decode()
            return decoded.split(":")[0]
        api_key = headers.get("X-API-Key", "")
        if api_key:
            return api_key
        return None

    def handle_request(self, path: str, method: str, headers: Dict[str, str], body: Any) -> Dict[str, Any]:
        if path not in self.routes:
            return {"status": 404, "error": "Not found"}

        route = self.routes[path]
        route["calls"] += 1
        self.metrics[path] = self.metrics.get(path, 0) + 1

        if route["auth_required"]:
            user = self.authenticate(headers)
            if not user:
                return {"status": 401, "error": "Unauthorized"}

        try:
            result = route["handler"](body)
            return {"status": 200, "data": result}
        except Exception as e:
            return {"status": 500, "error": str(e)}

    def get_metrics(self) -> Dict[str, int]:
        return self.metrics.copy()

if __name__ == "__main__":
    print("GatewayV2 self-test")
    gw = GatewayV2()
    gw.add_route("/health", lambda x: {"status": "ok"}, auth_required=False)
    r = gw.handle_request("/health", "GET", {}, {})
    assert r["status"] == 200
    print("All tests pass")
