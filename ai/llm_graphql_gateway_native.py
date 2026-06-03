"""
llm_graphql_gateway_native.py
MAGNATRIX-OS GraphQL Gateway Engine
Native Python, stdlib only.
Provides GraphQL query parsing, schema stitching, field resolution, query execution,
and response aggregation for unified API access across MAGNATRIX-OS services.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Union


class GraphQLType(Enum):
    QUERY = "query"
    MUTATION = "mutation"
    SUBSCRIPTION = "subscription"


@dataclass
class GraphQLField:
    name: str
    field_type: str
    args: Dict[str, str] = field(default_factory=dict)
    resolver: Optional[Callable] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "type": self.field_type, "args": self.args, "description": self.description}


@dataclass
class GraphQLType:
    name: str
    fields: Dict[str, GraphQLField]
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "fields": {k: v.to_dict() for k, v in self.fields.items()}, "description": self.description}


@dataclass
class GraphQLRequest:
    operation: str
    query: str
    variables: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"operation": self.operation, "query": self.query, "variables": self.variables, "headers": self.headers}


@dataclass
class GraphQLResponse:
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    extensions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"data": self.data, "errors": self.errors, "extensions": self.extensions}


class GraphQLGatewayEngine:
    """
    Lightweight GraphQL gateway with schema registration, query parsing, and field resolution.
    """

    def __init__(self) -> None:
        self._types: Dict[str, GraphQLType] = {}
        self._resolvers: Dict[str, Callable] = {}
        self._root_fields: Dict[str, GraphQLField] = {}
        self._middlewares: List[Callable[[GraphQLRequest, Callable], GraphQLResponse]] = []

    def register_type(self, gql_type: GraphQLType) -> None:
        self._types[gql_type.name] = gql_type

    def register_resolver(self, type_name: str, field_name: str, resolver: Callable) -> None:
        key = f"{type_name}.{field_name}"
        self._resolvers[key] = resolver

    def register_root_field(self, field: GraphQLField, resolver: Callable) -> None:
        self._root_fields[field.name] = field
        self._resolvers[f"Query.{field.name}"] = resolver

    def add_middleware(self, middleware: Callable[[GraphQLRequest, Callable], GraphQLResponse]) -> None:
        self._middlewares.append(middleware)

    def parse_query(self, query: str) -> GraphQLRequest:
        # Minimal parser for demonstration
        operation = "query"
        if query.strip().startswith("mutation"):
            operation = "mutation"
        elif query.strip().startswith("subscription"):
            operation = "subscription"
        # Extract operation name
        match = re.search(r'(query|mutation|subscription)\s+(\w+)', query)
        op_name = match.group(2) if match else "anonymous"
        # Extract variables from JSON if present (not standard GraphQL but simplified)
        return GraphQLRequest(operation=op_name, query=query)

    def _resolve_field(self, type_name: str, field_name: str, parent: Any, args: Dict[str, Any]) -> Any:
        resolver = self._resolvers.get(f"{type_name}.{field_name}")
        if resolver:
            return resolver(parent, args)
        # Fallback: return parent attribute
        if isinstance(parent, dict):
            return parent.get(field_name)
        return None

    def _extract_fields(self, query: str) -> List[str]:
        # Minimal field extraction: find field names after braces
        fields = []
        # Simple extraction of top-level fields in query
        body = re.search(r'\{([^}]+)\}', query)
        if body:
            text = body.group(1)
            # Match field names (alphanumeric with underscores)
            for match in re.finditer(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', text):
                fields.append(match.group(1))
        return fields

    def execute(self, request: GraphQLRequest) -> GraphQLResponse:
        # Apply middlewares
        if self._middlewares:
            def chain(req: GraphQLRequest, idx: int = 0) -> GraphQLResponse:
                if idx >= len(self._middlewares):
                    return self._execute_core(req)
                return self._middlewares[idx](req, lambda r: chain(r, idx + 1))
            return chain(request)
        return self._execute_core(request)

    def _execute_core(self, request: GraphQLRequest) -> GraphQLResponse:
        fields = self._extract_fields(request.query)
        if not fields:
            return GraphQLResponse(errors=["No fields found in query"])

        data: Dict[str, Any] = {}
        errors: List[str] = []

        for field_name in fields:
            if field_name not in self._root_fields:
                errors.append(f"Unknown field: {field_name}")
                continue
            try:
                result = self._resolve_field("Query", field_name, None, request.variables)
                data[field_name] = result
            except Exception as e:
                errors.append(f"Error resolving {field_name}: {e}")

        return GraphQLResponse(data=data if data else None, errors=errors)

    def introspect(self) -> Dict[str, Any]:
        return {
            "types": {k: v.to_dict() for k, v in self._types.items()},
            "root_fields": {k: v.to_dict() for k, v in self._root_fields.items()},
        }

    def export_schema(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.introspect(), f, indent=2, default=str)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS GraphQL Gateway Engine")
    print("=" * 60)

    gateway = GraphQLGatewayEngine()

    # Register types
    gateway.register_type(GraphQLType("LLM", {
        "id": GraphQLField("id", "String"),
        "model": GraphQLField("model", "String"),
        "status": GraphQLField("status", "String"),
    }))

    gateway.register_type(GraphQLType("Prompt", {
        "id": GraphQLField("id", "String"),
        "text": GraphQLField("text", "String"),
        "tokens": GraphQLField("tokens", "Int"),
    }))

    # Register root resolvers
    def resolve_llms(parent: Any, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"id": "llm-1", "model": "gpt-4o", "status": "active"},
            {"id": "llm-2", "model": "claude-3", "status": "active"},
        ]

    def resolve_prompts(parent: Any, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"id": "p1", "text": "Hello world", "tokens": 2},
            {"id": "p2", "text": "Generate a summary", "tokens": 4},
        ]

    def resolve_stats(parent: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"total_requests": 1500, "avg_latency_ms": 120.5}

    gateway.register_root_field(GraphQLField("llms", "[LLM]"), resolve_llms)
    gateway.register_root_field(GraphQLField("prompts", "[Prompt]"), resolve_prompts)
    gateway.register_root_field(GraphQLField("stats", "Stats"), resolve_stats)

    # Middleware example
    def logging_middleware(request: GraphQLRequest, next_fn: Callable) -> GraphQLResponse:
        print(f"  [Middleware] Executing: {request.operation}")
        return next_fn(request)

    gateway.add_middleware(logging_middleware)

    print("\n--- Query 1: llms ---")
    req1 = GraphQLRequest(operation="query", query="{ llms { id model status } }")
    resp1 = gateway.execute(req1)
    print(f"  Data: {resp1.data}")
    print(f"  Errors: {resp1.errors}")

    print("\n--- Query 2: prompts + stats ---")
    req2 = GraphQLRequest(operation="query", query="{ prompts { id text tokens } stats }")
    resp2 = gateway.execute(req2)
    print(f"  Data: {resp2.data}")
    print(f"  Errors: {resp2.errors}")

    print("\n--- Introspection ---")
    introspection = gateway.introspect()
    print(f"  Types: {list(introspection['types'].keys())}")
    print(f"  Root fields: {list(introspection['root_fields'].keys())}")

    print("\nGraphQL Gateway test complete.")


if __name__ == "__main__":
    run()
