"""infrastructure/api_versioning_native.py — API Versioning for MAGNATRIX-OS.

Pure-stdlib API versioning with version negotiation (header/path/query),
compatibility mapping, deprecation warnings, version routing,
backward-compatibility layer, and auto-generated version docs.

Rules: no third-party deps, type hints, docstrings, self-test in __main__.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class VersionStrategy(Enum):
    HEADER = "header"
    PATH = "path"
    QUERY = "query"


@dataclass
class RouteRule:
    """Maps a versioned endpoint to a handler and metadata."""
    version: str
    path: str
    method: str
    handler: Callable[..., Any]
    deprecated: bool = False
    sunset: Optional[str] = None
    notes: str = ""


class APIVersioning:
    """API versioning router and compatibility engine.

    Features:
        - Version negotiation via header, path segment, or query param
        - Compatibility mapping (v1 → v2 field transforms)
        - Deprecation warnings and sunset tracking
        - Version-aware routing
        - Backward-compatibility adapter layer
        - Auto-generated version documentation
    """

    def __init__(
        self,
        default_version: str = "1.0",
        strategy: VersionStrategy = VersionStrategy.HEADER,
        header_name: str = "X-API-Version",
        query_param: str = "version",
    ) -> None:
        self.default_version = default_version
        self.strategy = strategy
        self.header_name = header_name
        self.query_param = query_param
        self._routes: Dict[str, List[RouteRule]] = defaultdict(list)
        self._compat: Dict[str, Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]] = defaultdict(dict)
        self._docs: Dict[str, Dict[str, Any]] = {}
        self._warnings: List[str] = []

    # ---- Registration -------------------------------------------------

    def register(
        self,
        version: str,
        path: str,
        method: str,
        handler: Callable[..., Any],
        deprecated: bool = False,
        sunset: Optional[str] = None,
        notes: str = "",
    ) -> None:
        """Register a versioned endpoint."""
        key = f"{method.upper()} {path}"
        rule = RouteRule(version=version, path=path, method=method.upper(), handler=handler, deprecated=deprecated, sunset=sunset, notes=notes)
        self._routes[key].append(rule)

    def add_compat(
        self,
        from_version: str,
        to_version: str,
        adapter: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        """Register a request/response adapter between versions."""
        self._compat[to_version][from_version] = adapter

    # ---- Version extraction ------------------------------------------

    def extract_version(self, request: Dict[str, Any]) -> str:
        """Pull version string from request based on strategy."""
        if self.strategy == VersionStrategy.HEADER:
            headers = request.get("headers", {})
            return headers.get(self.header_name, self.default_version)
        if self.strategy == VersionStrategy.PATH:
            path = request.get("path", "")
            m = re.search(r"/v(\d+(\.\d+)?)/", path)
            if m:
                return m.group(1)
            return self.default_version
        if self.strategy == VersionStrategy.QUERY:
            query = request.get("query", {})
            return query.get(self.query_param, self.default_version)
        return self.default_version

    # ---- Routing ------------------------------------------------------

    def route(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route a request to the appropriate versioned handler."""
        method = request.get("method", "GET").upper()
        path = request.get("path", "/")
        version = self.extract_version(request)
        key = f"{method} {path}"

        candidates = self._routes.get(key, [])
        exact = next((r for r in candidates if r.version == version), None)
        if exact is None:
            # Fallback: find nearest compatible lower version
            sorted_rules = sorted(candidates, key=lambda r: self._semver_key(r.version), reverse=True)
            fallback = next((r for r in sorted_rules if self._semver_key(r.version) <= self._semver_key(version)), None)
            if fallback is None:
                return {"status": 404, "error": f"No route for {key} at version {version}"}
            exact = fallback

        # Deprecation warning
        if exact.deprecated:
            msg = f"Version {exact.version} of {key} is deprecated."
            if exact.sunset:
                msg += f" Sunset on {exact.sunset}."
            self._warnings.append(msg)

        # Apply backward-compat adapter if needed
        body = request.get("body", {})
        if isinstance(body, dict):
            adapted = self._apply_compat(version, exact.version, body)
            request["body"] = adapted

        result = exact.handler(request)
        return {"status": 200, "version": exact.version, "data": result, "deprecated": exact.deprecated}

    def _semver_key(self, v: str) -> tuple:
        """Parse a simple x.y version into a sortable tuple."""
        parts = v.split(".")
        return tuple(int(p) for p in parts) + (0,) * (3 - len(parts))

    def _apply_compat(self, request_version: str, target_version: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Chain adapters from request_version down to target_version."""
        current = dict(body)
        # Simplification: just apply one-step adapter if exact match exists
        adapter = self._compat.get(target_version, {}).get(request_version)
        if adapter:
            current = adapter(current)
        return current

    # ---- Backward compatibility helpers -------------------------------

    def transform_field_rename(self, old: str, new: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        """Factory for simple field-rename adapters."""
        def adapter(data: Dict[str, Any]) -> Dict[str, Any]:
            if old in data:
                data[new] = data.pop(old)
            return data
        return adapter

    def transform_wrap_field(self, field: str, wrapper: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        """Factory to wrap a field inside a new parent key."""
        def adapter(data: Dict[str, Any]) -> Dict[str, Any]:
            if field in data:
                data[wrapper] = {field: data.pop(field)}
            return data
        return adapter

    # ---- Documentation ------------------------------------------------

    def generate_docs(self) -> Dict[str, Any]:
        """Generate versioned API documentation."""
        docs: Dict[str, Any] = {"default_version": self.default_version, "strategy": self.strategy.value, "endpoints": []}
        for key, rules in self._routes.items():
            for r in rules:
                docs["endpoints"].append({
                    "endpoint": key,
                    "version": r.version,
                    "deprecated": r.deprecated,
                    "sunset": r.sunset,
                    "notes": r.notes,
                })
        self._docs = docs
        return docs

    def get_warnings(self) -> List[str]:
        return self._warnings[:]

    def to_json(self) -> str:
        return json.dumps(self.generate_docs(), indent=2)


def run() -> None:
    """Self-test: register endpoints, route with version negotiation, compat, docs."""
    api = APIVersioning(default_version="1.0", strategy=VersionStrategy.HEADER, header_name="X-API-Version")

    # Handlers
    def v1_user_get(req: Dict[str, Any]) -> Any:
        return {"id": req["body"].get("user_id"), "name": "Alice"}

    def v2_user_get(req: Dict[str, Any]) -> Any:
        return {"id": req["body"].get("user_id"), "profile": {"name": "Alice", "tier": "pro"}}

    def v1_order_post(req: Dict[str, Any]) -> Any:
        return {"order_id": "ORD-001", "amount": req["body"].get("amount")}

    # Register
    api.register("1.0", "/users", "GET", v1_user_get, notes="Fetch user by ID")
    api.register("2.0", "/users", "GET", v2_user_get, deprecated=False)
    api.register("1.0", "/orders", "POST", v1_order_post, deprecated=True, sunset="2026-12-01")

    # Compatibility: v2 expects user_id inside 'profile' wrapper
    api.add_compat("1.0", "2.0", api.transform_wrap_field("user_id", "profile"))

    # Route v1 request
    r1 = api.route({"method": "GET", "path": "/users", "headers": {"X-API-Version": "1.0"}, "body": {"user_id": "u42"}})
    assert r1["status"] == 200
    assert r1["version"] == "1.0"
    assert r1["data"]["name"] == "Alice"

    # Route v2 request with compat adapter
    r2 = api.route({"method": "GET", "path": "/users", "headers": {"X-API-Version": "2.0"}, "body": {"user_id": "u42"}})
    assert r2["status"] == 200
    assert r2["version"] == "2.0"
    assert r2["data"]["profile"]["name"] == "Alice"

    # Route deprecated endpoint
    r3 = api.route({"method": "POST", "path": "/orders", "headers": {"X-API-Version": "1.0"}, "body": {"amount": 99}})
    assert r3["deprecated"] is True
    assert len(api.get_warnings()) == 1

    # Path-based versioning
    api_path = APIVersioning(strategy=VersionStrategy.PATH)
    api_path.register("1.0", "/v1.0/items", "GET", lambda req: {"items": []})
    rp = api_path.route({"method": "GET", "path": "/v1.0/items", "headers": {}, "body": {}})
    assert rp["version"] == "1.0"

    # Query-based versioning
    api_query = APIVersioning(strategy=VersionStrategy.QUERY, query_param="api_version")
    api_query.register("3.0", "/status", "GET", lambda req: {"ok": True})
    rq = api_query.route({"method": "GET", "path": "/status", "query": {"api_version": "3.0"}, "body": {}})
    assert rq["version"] == "3.0"

    # Docs
    docs = api.generate_docs()
    assert len(docs["endpoints"]) == 3

    print("api_versioning_native.py self-test passed.")
    print("  Warnings:", api.get_warnings())


if __name__ == "__main__":
    run()
