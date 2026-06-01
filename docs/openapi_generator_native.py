#!/usr/bin/env python3
"""docs/openapi_generator_native.py — OpenAPI 3.0 Spec Generator for MAGNATRIX-OS"""
from __future__ import annotations
import json, re, inspect
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

@dataclass
class EndpointInfo:
    path: str
    method: str = "get"
    summary: str = ""
    description: str = ""
    parameters: List[Dict] = field(default_factory=list)
    request_body: Optional[Dict] = None
    responses: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

class OpenAPIGenerator:
    def __init__(self, title="MAGNATRIX-OS API", version="1.0.0"):
        self.title = title
        self.version = version
        self.endpoints: List[EndpointInfo] = []
        self.schemas: Dict[str, Dict] = {}

    def discover_from_module(self, module, prefix=""):
        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj) and hasattr(obj, "_api_endpoint"):
                meta = obj._api_endpoint
                ep = EndpointInfo(
                    path=prefix + meta.get("path", f"/{name.lower()}"),
                    method=meta.get("method", "get").lower(),
                    summary=meta.get("summary", name),
                    description=meta.get("description", ""),
                    tags=meta.get("tags", ["default"]),
                )
                self.endpoints.append(ep)

    def add_endpoint(self, endpoint: EndpointInfo):
        self.endpoints.append(endpoint)

    def extract_schema(self, cls_name: str, fields: Dict[str, str]):
        self.schemas[cls_name] = {
            "type": "object",
            "properties": {k: {"type": v} for k, v in fields.items()},
        }

    def generate(self) -> Dict[str, Any]:
        spec = {
            "openapi": "3.0.3",
            "info": {"title": self.title, "version": self.version},
            "paths": {},
            "components": {"schemas": self.schemas},
        }
        for ep in self.endpoints:
            if ep.path not in spec["paths"]:
                spec["paths"][ep.path] = {}
            spec["paths"][ep.path][ep.method] = {
                "summary": ep.summary,
                "description": ep.description,
                "parameters": ep.parameters,
                "tags": ep.tags,
                "responses": ep.responses or {"200": {"description": "OK"}},
            }
            if ep.request_body:
                spec["paths"][ep.path][ep.method]["requestBody"] = ep.request_body
        return spec

    def export_json(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.generate(), f, indent=2)

    def export_yaml(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(f"openapi: 3.0.3
")
            f.write(f"info:
  title: {self.title}
  version: {self.version}
")
            f.write(f"paths:
")
            for ep in self.endpoints:
                f.write(f"  {ep.path}:
")
                f.write(f"    {ep.method}:
")
                f.write(f"      summary: {ep.summary}
")

if __name__ == "__main__":
    gen = OpenAPIGenerator("MAGNATRIX", "1.0")
    gen.add_endpoint(EndpointInfo("/status", "get", "Get status", responses={"200": {"description": "System status"}}))
    gen.add_endpoint(EndpointInfo("/run", "post", "Run layer", request_body={"required": True, "content": {"application/json": {"schema": {"type": "object"}}}}, responses={"200": {"description": "Result"}}))
    gen.extract_schema("TaskRequest", {"name": "string", "args": "object"})
    gen.export_json("/tmp/openapi.json")
    print("OpenAPI generated: " + str(len(gen.endpoints)) + " endpoints")
