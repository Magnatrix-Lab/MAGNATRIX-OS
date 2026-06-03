#!/usr/bin/env python3
"""
MAGNATRIX-OS — API Documentation Engine
ai/llm_api_documentation_native.py

Features:
- OpenAPI spec generation from endpoint definitions
- Request/response schema documentation
- Authentication flow documentation
- Example generation (curl, python, javascript)
- API changelog tracking

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("api_documentation")


@dataclass
class Endpoint:
    path: str
    method: str
    summary: str
    params: List[Dict[str, Any]]
    responses: Dict[str, Any]
    auth_required: bool


class APIDocumentationEngine:
    """Generate API docs and examples."""

    def __init__(self):
        self._endpoints: List[Endpoint] = []
        self._changelog: List[Dict[str, Any]] = []

    def add_endpoint(self, ep: Endpoint) -> None:
        self._endpoints.append(ep)

    def generate_openapi(self, title: str = "API", version: str = "1.0") -> Dict[str, Any]:
        paths = {}
        for ep in self._endpoints:
            if ep.path not in paths:
                paths[ep.path] = {}
            paths[ep.path][ep.method.lower()] = {
                "summary": ep.summary,
                "parameters": ep.params,
                "responses": ep.responses,
                "security": [{"apiKey": []}] if ep.auth_required else [],
            }
        return {
            "openapi": "3.0.0",
            "info": {"title": title, "version": version},
            "paths": paths,
        }

    def generate_curl(self, ep: Endpoint) -> str:
        auth = "-H 'Authorization: Bearer TOKEN' " if ep.auth_required else ""
        return f"curl {auth}-X {ep.method.upper()} https://api.example.com{ep.path}"

    def generate_python_example(self, ep: Endpoint) -> str:
        return f"import requests\nresponse = requests.{ep.method.lower()}('https://api.example.com{ep.path}')\nprint(response.json())"

    def add_changelog(self, version: str, changes: List[str]) -> None:
        self._changelog.append({"version": version, "changes": changes})

    def get_stats(self) -> Dict[str, Any]:
        return {"endpoints": len(self._endpoints), "changelog_entries": len(self._changelog)}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — API Documentation Engine")
    print("ai/llm_api_documentation_native.py")
    print("=" * 60)

    engine = APIDocumentationEngine()

    engine.add_endpoint(Endpoint("/users", "GET", "List users", [{"name": "page", "in": "query"}], {"200": {"description": "Success"}}, True))
    engine.add_endpoint(Endpoint("/users", "POST", "Create user", [{"name": "body", "in": "body"}], {"201": {"description": "Created"}}, True))
    engine.add_endpoint(Endpoint("/health", "GET", "Health check", [], {"200": {"description": "OK"}}, False))

    print("\n[1] OpenAPI Spec")
    spec = engine.generate_openapi()
    print(json.dumps(spec, indent=2)[:500])

    print("\n[2] cURL Examples")
    for ep in engine._endpoints:
        print(f"  {ep.method.upper()} {ep.path}: {engine.generate_curl(ep)}")

    print("\n[3] Python Examples")
    for ep in engine._endpoints[:2]:
        print(f"  {engine.generate_python_example(ep)}")

    print(f"\n[4] Stats: {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
