"""LLM API Doc Builder — Native Python (stdlib only)."""
from __future__ import annotations
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
class APIEndpoint:
    id: str
    path: str
    method: HTTPMethod
    description: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    responses: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class APIDocBuilder:
    def __init__(self) -> None:
        self._endpoints: List[APIEndpoint] = []

    def add_endpoint(self, endpoint: APIEndpoint) -> None:
        self._endpoints.append(endpoint)

    def to_openapi(self) -> Dict[str, Any]:
        paths = {}
        for ep in self._endpoints:
            if ep.path not in paths:
                paths[ep.path] = {}
            paths[ep.path][ep.method.name.lower()] = {
                "summary": ep.description,
                "parameters": ep.parameters,
                "responses": {r["code"]: {"description": r["description"]} for r in ep.responses}
            }
        return {"openapi": "3.0.0", "paths": paths}

    def to_markdown(self) -> str:
        lines = ["# API Documentation", ""]
        for ep in self._endpoints:
            lines.append("## " + ep.method.name + " " + ep.path)
            lines.append(ep.description)
            lines.append("")
            if ep.parameters:
                lines.append("**Parameters:**")
                for p in ep.parameters:
                    lines.append("- " + p.get("name", "") + " (" + p.get("type", "") + ")")
                lines.append("")
            if ep.responses:
                lines.append("**Responses:**")
                for r in ep.responses:
                    lines.append("- " + str(r.get("code", "")) + ": " + r.get("description", ""))
                lines.append("")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        return {"endpoints": len(self._endpoints), "methods": len(set(ep.method for ep in self._endpoints))}

def run() -> None:
    print("API Doc Builder test")
    e = APIDocBuilder()
    e.add_endpoint(APIEndpoint("e1", "/chat", HTTPMethod.POST, "Send a chat message", [{"name": "message", "type": "string"}], [{"code": 200, "description": "Success"}, {"code": 400, "description": "Bad request"}]))
    e.add_endpoint(APIEndpoint("e2", "/models", HTTPMethod.GET, "List available models", [], [{"code": 200, "description": "List of models"}]))
    print("  Endpoints: " + str(len(e._endpoints)))
    print("  Markdown:\n" + e.to_markdown()[:200] + "...")
    print("API Doc Builder test complete.")

if __name__ == "__main__":
    run()
