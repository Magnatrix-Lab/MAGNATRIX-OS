#!/usr/bin/env python3
"""
Tool Registry for MAGNATRIX-OS
Manages external tool registration, versioning, dependency tracking,
and runtime invocation interfaces. Provides a unified contract for
tools that the UnifiedOrchestrator can dispatch to.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple


class ToolKind(enum.Enum):
    """Classification of tool implementation."""
    PYTHON_MODULE = "python_module"
    CLI_BINARY = "cli_binary"
    REST_API = "rest_api"
    WASM_PLUGIN = "wasm_plugin"
    BUILT_IN = "built_in"


class ToolHealth(enum.Enum):
    """Runtime health status of a registered tool."""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class PermissionLevel(enum.Enum):
    """Execution permission levels."""
    SAFE = "safe"              # read-only, no side effects
    CAUTION = "caution"        # file writes, local network
    DANGEROUS = "dangerous"    # privileged operations, external network
    FORBIDDEN = "forbidden"    # blocked by policy


@dataclasses.dataclass(frozen=True)
class ToolVersion:
    """SemVer-like version record."""
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, text: str) -> ToolVersion:
        parts = [int(p) for p in text.strip().lstrip("v").split(".")]
        while len(parts) < 3:
            parts.append(0)
        return cls(major=parts[0], minor=parts[1], patch=parts[2])


@dataclasses.dataclass
class ToolContract:
    """Input/output contract for a tool."""
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    required_params: List[str] = dataclasses.field(default_factory=list)
    optional_params: List[str] = dataclasses.field(default_factory=list)
    examples: List[Dict[str, Any]] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class ToolRecord:
    """Full registration record for a single tool."""
    tool_id: str
    name: str
    description: str
    kind: ToolKind
    health: ToolHealth
    permission: PermissionLevel
    version: ToolVersion
    entry_point: str  # module path, CLI path, or URL
    contract: ToolContract
    dependencies: List[str] = dataclasses.field(default_factory=list)
    tags: Set[str] = dataclasses.field(default_factory=set)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    registered_at: float = dataclasses.field(default_factory=time.time)
    last_invoked: Optional[float] = None
    invoke_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "kind": self.kind.value,
            "health": self.health.value,
            "permission": self.permission.value,
            "version": str(self.version),
            "entry_point": self.entry_point,
            "contract": {
                "input_schema": self.contract.input_schema,
                "output_schema": self.contract.output_schema,
                "required_params": self.contract.required_params,
                "optional_params": self.contract.optional_params,
            },
            "dependencies": self.dependencies,
            "tags": sorted(self.tags),
            "metadata": self.metadata,
            "registered_at": self.registered_at,
            "last_invoked": self.last_invoked,
            "invoke_count": self.invoke_count,
            "error_count": self.error_count,
            "avg_latency_ms": self.avg_latency_ms,
        }


class ToolRegistry:
    """Central registry for all executable tools in MAGNATRIX-OS."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolRecord] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        tool_id: str,
        name: str,
        description: str,
        kind: ToolKind,
        entry_point: str,
        contract: ToolContract,
        version: str = "1.0.0",
        permission: PermissionLevel = PermissionLevel.SAFE,
        dependencies: Optional[List[str]] = None,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolRecord:
        if tool_id in self._tools:
            raise ValueError(f"Tool '{tool_id}' already registered")
        record = ToolRecord(
            tool_id=tool_id,
            name=name,
            description=description,
            kind=kind,
            health=ToolHealth.UNKNOWN,
            permission=permission,
            version=ToolVersion.parse(version),
            entry_point=entry_point,
            contract=contract,
            dependencies=dependencies or [],
            tags=tags or set(),
            metadata=metadata or {},
        )
        self._tools[tool_id] = record
        return record

    def unregister(self, tool_id: str) -> bool:
        if tool_id in self._tools:
            del self._tools[tool_id]
            self._handlers.pop(tool_id, None)
            return True
        return False

    def register_handler(self, tool_id: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Bind a Python callable as the runtime handler for a tool."""
        if tool_id not in self._tools:
            raise KeyError(f"Tool '{tool_id}' not registered")
        self._handlers[tool_id] = handler

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get(self, tool_id: str) -> Optional[ToolRecord]:
        return self._tools.get(tool_id)

    def list_all(self) -> List[ToolRecord]:
        return list(self._tools.values())

    def search(self, keyword: str) -> List[ToolRecord]:
        kw = keyword.lower()
        return [
            t for t in self._tools.values()
            if kw in t.name.lower() or kw in t.description.lower() or any(kw in tag.lower() for tag in t.tags)
        ]

    def filter_by_kind(self, kind: ToolKind) -> List[ToolRecord]:
        return [t for t in self._tools.values() if t.kind == kind]

    def filter_by_permission(self, level: PermissionLevel) -> List[ToolRecord]:
        return [t for t in self._tools.values() if t.permission == level]

    def filter_by_tag(self, tag: str) -> List[ToolRecord]:
        return [t for t in self._tools.values() if tag in t.tags]

    # ------------------------------------------------------------------
    # Health & Runtime
    # ------------------------------------------------------------------

    def probe(self, tool_id: str) -> ToolHealth:
        """Probe a tool to determine its runtime health."""
        tool = self._tools.get(tool_id)
        if not tool:
            return ToolHealth.UNKNOWN
        if tool.kind == ToolKind.PYTHON_MODULE:
            try:
                spec = importlib.util.find_spec(tool.entry_point.replace("/", ".").rstrip(".py"))
                tool.health = ToolHealth.AVAILABLE if spec else ToolHealth.UNREACHABLE
            except Exception:
                tool.health = ToolHealth.UNREACHABLE
        elif tool.kind == ToolKind.CLI_BINARY:
            try:
                result = subprocess.run([tool.entry_point, "--version"], capture_output=True, timeout=5)
                tool.health = ToolHealth.AVAILABLE if result.returncode == 0 else ToolHealth.DEGRADED
            except Exception:
                tool.health = ToolHealth.UNREACHABLE
        elif tool.kind == ToolKind.REST_API:
            # Minimal probe without external deps — just validate URL shape
            tool.health = ToolHealth.AVAILABLE if tool.entry_point.startswith("http") else ToolHealth.UNKNOWN
        else:
            tool.health = ToolHealth.AVAILABLE
        return tool.health

    def probe_all(self) -> Dict[str, ToolHealth]:
        return {tid: self.probe(tid) for tid in self._tools}

    def invoke(self, tool_id: str, params: Dict[str, Any], timeout: float = 30.0) -> Any:
        """Execute a registered tool by ID."""
        tool = self._tools.get(tool_id)
        if not tool:
            raise KeyError(f"Tool '{tool_id}' not found")
        if tool.health == ToolHealth.DISABLED or tool.health == ToolHealth.FORBIDDEN:
            raise RuntimeError(f"Tool '{tool_id}' is disabled or forbidden")

        # Validate required params
        for req in tool.contract.required_params:
            if req not in params:
                raise ValueError(f"Missing required param: {req}")

        start = time.perf_counter()
        try:
            handler = self._handlers.get(tool_id)
            if handler:
                result = handler(params)
            elif tool.kind == ToolKind.PYTHON_MODULE:
                result = self._invoke_python_module(tool, params)
            elif tool.kind == ToolKind.CLI_BINARY:
                result = self._invoke_cli(tool, params, timeout)
            else:
                raise NotImplementedError(f"No handler bound for tool kind {tool.kind.value}")
            tool.invoke_count += 1
            tool.error_count = 0
        except Exception as exc:
            tool.error_count += 1
            raise
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            tool.avg_latency_ms = (tool.avg_latency_ms * max(0, tool.invoke_count - 1) + elapsed) / max(1, tool.invoke_count)
            tool.last_invoked = time.time()
        return result

    def _invoke_python_module(self, tool: ToolRecord, params: Dict[str, Any]) -> Any:
        module_path = tool.entry_point.replace("/", ".").rstrip(".py")
        mod = importlib.import_module(module_path)
        # Convention: if module has a top-level function matching tool_id, call it
        func_name = tool.metadata.get("function_name", "run")
        if not hasattr(mod, func_name):
            raise RuntimeError(f"Module {module_path} has no function '{func_name}'")
        return getattr(mod, func_name)(**params)

    def _invoke_cli(self, tool: ToolRecord, params: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        cmd = [tool.entry_point]
        for k, v in params.items():
            cmd.append(f"--{k}")
            cmd.append(str(v))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_json(self, path: str) -> None:
        data = [t.to_dict() for t in self._tools.values()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_json(self, path: str) -> int:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for item in data:
            self.register(
                tool_id=item["tool_id"],
                name=item["name"],
                description=item["description"],
                kind=ToolKind(item["kind"]),
                entry_point=item["entry_point"],
                contract=ToolContract(
                    input_schema=item["contract"]["input_schema"],
                    output_schema=item["contract"]["output_schema"],
                    required_params=item["contract"].get("required_params", []),
                    optional_params=item["contract"].get("optional_params", []),
                ),
                version=item["version"],
                permission=PermissionLevel(item["permission"]),
                dependencies=item.get("dependencies", []),
                tags=set(item.get("tags", [])),
                metadata=item.get("metadata", {}),
            )
            count += 1
        return count

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        kinds: Dict[str, int] = {}
        perms: Dict[str, int] = {}
        total_invocations = 0
        total_errors = 0
        for t in self._tools.values():
            kinds[t.kind.value] = kinds.get(t.kind.value, 0) + 1
            perms[t.permission.value] = perms.get(t.permission.value, 0) + 1
            total_invocations += t.invoke_count
            total_errors += t.error_count
        return {
            "total_tools": len(self._tools),
            "kind_distribution": kinds,
            "permission_distribution": perms,
            "total_invocations": total_invocations,
            "total_errors": total_errors,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    reg = ToolRegistry()

    # Register a built-in echo tool
    reg.register(
        tool_id="echo",
        name="Echo Tool",
        description="Returns the input parameters unchanged.",
        kind=ToolKind.BUILT_IN,
        entry_point="built_in.echo",
        contract=ToolContract(
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            required_params=["message"],
        ),
        version="1.0.0",
        permission=PermissionLevel.SAFE,
        tags={"builtin", "utility"},
    )

    def _echo_handler(params: Dict[str, Any]) -> Any:
        return {"echoed": params.get("message")}

    reg.register_handler("echo", _echo_handler)

    # Register a Python module tool (example)
    reg.register(
        tool_id="health_check",
        name="System Health Check",
        description="Returns basic system health metrics.",
        kind=ToolKind.PYTHON_MODULE,
        entry_point="os",
        contract=ToolContract(
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        ),
        version="1.0.0",
        permission=PermissionLevel.SAFE,
        tags={"system", "health"},
    )

    reg.register_handler("health_check", lambda _p: {"platform": sys.platform, "python": sys.version})

    # Register a CLI tool placeholder
    reg.register(
        tool_id="git_status",
        name="Git Status",
        description="Runs git status and returns the output.",
        kind=ToolKind.CLI_BINARY,
        entry_point="git",
        contract=ToolContract(
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            required_params=["cwd"],
        ),
        version="2.40.0",
        permission=PermissionLevel.CAUTION,
        tags={"vcs", "git"},
    )

    # Probe all
    print("=== Tool Registry Demo ===")
    print(f"Total tools: {len(reg.list_all())}")
    health = reg.probe_all()
    for tid, h in health.items():
        print(f"  {tid}: {h.value}")

    # Invoke echo
    result = reg.invoke("echo", {"message": "Hello MAGNATRIX-OS"})
    print(f"\nInvoke 'echo': {result}")

    # Invoke health_check
    result = reg.invoke("health_check", {})
    print(f"Invoke 'health_check': {result}")

    # Stats
    print(f"\nRegistry stats: {reg.stats()}")

    # Export
    export_path = "/tmp/tool_registry.json"
    reg.export_json(export_path)
    print(f"\nExported to {export_path}")


if __name__ == "__main__":
    _demo()
