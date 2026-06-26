#!/usr/bin/env python3
"""
GraphQL Interface for MAGNATRIX-OS
Native GraphQL server with schema introspection, query/mutation/subscription.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import importlib
import inspect
import json
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class GraphQLParser:
    """Parse GraphQL query strings into AST-like structure."""

    def parse(self, query: str) -> Dict[str, Any]:
        """Parse a GraphQL query string."""
        query = query.strip()
        if not query:
            return {"error": "Empty query"}

        # Determine operation type
        op_type = "query"
        if query.startswith("mutation"):
            op_type = "mutation"
        elif query.startswith("subscription"):
            op_type = "subscription"

        # Extract operation name and fields
        pattern = r"(?:query|mutation|subscription)\s*(?:\w+)?\s*\{([^}]*)\}"
        match = re.search(pattern, query, re.DOTALL)
        if not match:
            # Try without operation keyword
            if query.startswith("{"):
                match = re.search(r"\{([^}]*)\}", query, re.DOTALL)
            if not match:
                return {"error": "Invalid query syntax"}

        body = match.group(1)
        fields = self._parse_fields(body)

        return {
            "operation": op_type,
            "fields": fields,
            "raw": query,
        }

    def _parse_fields(self, body: str) -> Dict[str, Any]:
        """Parse field selection into dict."""
        fields = {}
        depth = 0
        current = ""
        for char in body:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            if char == " " and depth == 0 and current.strip():
                parts = current.strip().split("(", 1)
                name = parts[0].strip()
                args = {}
                if len(parts) > 1:
                    args = self._parse_args("(" + parts[1])
                sub = body[body.find("{", body.find(current)) + 1:body.find("}", body.find(current))] if "{" in body[body.find(current):] else ""
                fields[name] = {"args": args, "subfields": self._parse_fields(sub) if sub else {}}
                current = ""
            else:
                current += char
        if current.strip():
            parts = current.strip().split("(", 1)
            name = parts[0].strip()
            args = {}
            if len(parts) > 1:
                args = self._parse_args("(" + parts[1])
            fields[name] = {"args": args, "subfields": {}}
        return fields

    def _parse_args(self, arg_str: str) -> Dict[str, Any]:
        """Parse GraphQL arguments."""
        args = {}
        # Simple key: value parsing
        for match in re.finditer(r'(\w+):\s*([^,\)]+)', arg_str):
            key = match.group(1)
            val = match.group(2).strip().strip('"').strip("'")
            # Try to convert types
            if val.lower() in ("true", "false"):
                val = val.lower() == "true"
            elif val.isdigit():
                val = int(val)
            elif val.replace(".", "", 1).isdigit():
                val = float(val)
            args[key] = val
        return args


class GraphQLSchema:
    """Build GraphQL schema from MAGNATRIX-OS modules."""

    TYPE_MAP = {
        str: "String",
        int: "Int",
        float: "Float",
        bool: "Boolean",
        list: "List",
        dict: "Object",
        None: "Void",
    }

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._types: Dict[str, Dict[str, Any]] = {}
        self._queries: Dict[str, Dict[str, Any]] = {}
        self._mutations: Dict[str, Dict[str, Any]] = {}
        self._subscriptions: Dict[str, Dict[str, Any]] = {}

    def build_from_modules(self) -> None:
        """Auto-build schema from all core modules."""
        sys.path.insert(0, str(self.root))
        try:
            core_dir = self.root / "core"
            if not core_dir.exists():
                return
            for f in sorted(core_dir.glob("*_native.py")):
                mod_name = f"core.{f.stem}"
                try:
                    mod = importlib.import_module(mod_name)
                    self._scan_module(mod, f.stem)
                except Exception:
                    pass
        finally:
            sys.path.pop(0)

        # Add built-in types
        self._types["Module"] = {
            "fields": {
                "name": "String",
                "state": "String",
                "description": "String",
                "loadTimeMs": "Float",
            }
        }
        self._types["SystemStatus"] = {
            "fields": {
                "modules": "Int",
                "active": "Int",
                "failed": "Int",
                "uptime": "String",
            }
        }
        self._types["Query"] = {
            "fields": {
                "modules": "List",
                "module": "Module",
                "status": "SystemStatus",
                "health": "Boolean",
            }
        }
        self._types["Mutation"] = {
            "fields": {
                "startModule": "Boolean",
                "stopModule": "Boolean",
                "reboot": "Boolean",
            }
        }

    def _scan_module(self, mod: Any, mod_name: str) -> None:
        for name in dir(mod):
            obj = getattr(mod, name)
            if callable(obj) and not name.startswith("_"):
                sig = inspect.signature(obj) if hasattr(obj, "__code__") else None
                args = {}
                if sig:
                    for param_name, param in sig.parameters.items():
                        if param_name != "self":
                            args[param_name] = self.TYPE_MAP.get(type(param.default), "String")

                return_type = "String"
                if hasattr(obj, "__annotations__") and "return" in obj.__annotations__:
                    ann = obj.__annotations__["return"]
                    return_type = self.TYPE_MAP.get(ann, "String")

                # Classify as query or mutation based on naming
                if any(name.startswith(p) for p in ("get", "list", "fetch", "read", "query", "search", "find")):
                    self._queries[f"{mod_name}_{name}"] = {
                        "args": args, "returns": return_type, "module": mod_name, "func": name,
                    }
                elif any(name.startswith(p) for p in ("set", "create", "update", "delete", "write", "save", "post", "put")):
                    self._mutations[f"{mod_name}_{name}"] = {
                        "args": args, "returns": return_type, "module": mod_name, "func": name,
                    }

    def introspect(self) -> Dict[str, Any]:
        """Generate GraphQL introspection schema."""
        return {
            "__schema": {
                "queryType": {"name": "Query", "fields": list(self._queries.keys())},
                "mutationType": {"name": "Mutation", "fields": list(self._mutations.keys())},
                "subscriptionType": {"name": "Subscription", "fields": list(self._subscriptions.keys())},
                "types": self._types,
            }
        }

    def get_type(self, name: str) -> Optional[Dict[str, Any]]:
        return self._types.get(name)


class GraphQLResolver:
    """Resolve GraphQL queries against MAGNATRIX-OS modules."""

    def __init__(self, schema: GraphQLSchema, registry: Any) -> None:
        self.schema = schema
        self.registry = registry

    def resolve(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a parsed query."""
        op = parsed.get("operation", "query")
        fields = parsed.get("fields", {})

        if "error" in parsed:
            return {"errors": [{"message": parsed["error"]}]}

        data = {}
        for field_name, field_info in fields.items():
            try:
                result = self._resolve_field(op, field_name, field_info)
                data[field_name] = result
            except Exception as e:
                return {"errors": [{"message": str(e)}], "data": data}

        return {"data": data}

    def _resolve_field(self, op: str, field_name: str, field_info: Dict[str, Any]) -> Any:
        """Resolve a single field."""
        args = field_info.get("args", {})

        # Built-in fields
        if field_name == "modules" and op == "query":
            modules = self.registry.list_modules() if self.registry else []
            return [{"name": m["name"], "state": m["state"], "loadTimeMs": m.get("load_ms", 0)} for m in modules]

        if field_name == "module" and op == "query":
            name = args.get("name", "")
            status = self.registry.get_status(name) if self.registry else {}
            return {"name": name, "state": status.get("state", "unknown"), "loadTimeMs": status.get("load_ms", 0)}

        if field_name == "status" and op == "query":
            stats = self.registry.stats() if self.registry else {}
            return {
                "modules": stats.get("total_registered", 0),
                "active": stats.get("loaded", 0),
                "failed": stats.get("failed", 0),
                "uptime": "running",
            }

        if field_name == "health" and op == "query":
            return True

        # Dynamic module resolution
        if op == "query":
            query_def = self.schema._queries.get(field_name)
            if query_def:
                return self._call_module(query_def, args)

        if op == "mutation":
            mutation_def = self.schema._mutations.get(field_name)
            if mutation_def:
                return self._call_module(mutation_def, args)

        return None

    def _call_module(self, defn: Dict[str, Any], args: Dict[str, Any]) -> Any:
        """Call a module function dynamically."""
        mod_name = defn.get("module")
        func_name = defn.get("func")
        if not mod_name or not func_name:
            return None
        instance = self.registry.get_module(mod_name) if self.registry else None
        if instance and hasattr(instance, func_name):
            func = getattr(instance, func_name)
            try:
                return func(**args)
            except Exception:
                return None
        return None


class GraphQLServer:
    """HTTP server serving GraphQL endpoint."""

    def __init__(self, host: str = "0.0.0.0", port: int = 4000, repo_root: str = "") -> None:
        self.host = host
        self.port = port
        self.root = Path(repo_root).resolve() if repo_root else Path.cwd()
        self.schema = GraphQLSchema(str(self.root))
        self.schema.build_from_modules()
        self.resolver: Optional[GraphQLResolver] = None
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def set_registry(self, registry: Any) -> None:
        self.resolver = GraphQLResolver(self.schema, registry)

    def _make_handler(self) -> type:
        server = self
        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def _send_json(self, data: Any, status: int = 200) -> None:
                body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self) -> None:
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def do_GET(self) -> None:
                if self.path == "/graphql":
                    self._send_json({"message": "Use POST for GraphQL queries"})
                elif self.path == "/graphql/schema":
                    self._send_json(server.schema.introspect())
                else:
                    self._send_json({"error": "Not found"}, 404)

            def do_POST(self) -> None:
                if self.path != "/graphql":
                    self._send_json({"error": "Not found"}, 404)
                    return
                length = int(self.headers.get("Content-Length", 0))
                if not length:
                    self._send_json({"error": "Empty body"}, 400)
                    return
                try:
                    body = json.loads(self.rfile.read(length).decode("utf-8"))
                    query = body.get("query", "")
                    parser = GraphQLParser()
                    parsed = parser.parse(query)
                    if server.resolver:
                        result = server.resolver.resolve(parsed)
                    else:
                        result = {"data": parsed}
                    self._send_json(result)
                except Exception as e:
                    self._send_json({"errors": [{"message": str(e)}]}, 500)

        return _Handler

    def start(self, blocking: bool = False) -> None:
        self._running = True
        handler = self._make_handler()
        self._server = HTTPServer((self.host, self.port), handler)
        if blocking:
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True, name="GraphQLServer")
            self._thread.start()
            print(f"[GraphQL] Server at http://{self.host}:{self.port}/graphql")

    def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    def stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "host": self.host, "port": self.port,
            "queries": len(self.schema._queries),
            "mutations": len(self.schema._mutations),
            "types": len(self.schema._types),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== GraphQL Interface Demo ===\n")
    server = GraphQLServer(port=4001, repo_root="/mnt/agents/MAGNATRIX-OS")

    parser = GraphQLParser()
    queries = [
        "{ modules { name state } }",
        "{ status { modules active failed } }",
        "{ health }",
    ]

    for q in queries:
        print(f"Query: {q}")
        parsed = parser.parse(q)
        print(f"Parsed: {json.dumps(parsed, indent=2)}")
        print()

    print(f"Schema types: {list(server.schema._types.keys())}")
    print(f"Server stats: {server.stats()}")


if __name__ == "__main__":
    _demo()
