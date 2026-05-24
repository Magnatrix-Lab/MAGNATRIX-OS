#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Syscall Layer (Layer 1 Extension)
Inspired by: agiresearch/AIOS aios/syscall/
System call abstraction for LLM, Memory, Storage, Tool, and Terminal operations.
Provides unified interface for agents to request kernel services.
================================================================================
Zero-dependency syscall dispatcher with schema validation and async support.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# =============================================================================
# Constants
# =============================================================================
SYSCALL_TIMEOUT = 30.0


# =============================================================================
# Data Types
# =============================================================================
class SyscallType(Enum):
    LLM = "llm"
    MEMORY = "memory"
    STORAGE = "storage"
    TOOL = "tool"
    TERMINAL = "terminal"
    SCHEDULER = "scheduler"
    NETWORK = "network"


class SyscallStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class SyscallRequest:
    syscall_id: str
    type: SyscallType
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    agent_id: str = ""
    timestamp: float = field(default_factory=time.time)
    timeout: float = SYSCALL_TIMEOUT
    trace_id: str = ""


@dataclass
class SyscallResponse:
    syscall_id: str
    status: SyscallStatus
    result: Any = None
    error: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Schema Validator
# =============================================================================
class SchemaValidator:
    """Validate syscall parameters against JSON-like schemas."""

    @staticmethod
    def validate(params: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, str]:
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        for key in required:
            if key not in params:
                return False, f"Missing required parameter: {key}"
        for key, val in params.items():
            prop = properties.get(key, {})
            expected_type = prop.get("type")
            if expected_type and not SchemaValidator._type_check(val, expected_type):
                return False, f"Parameter '{key}' expected {expected_type}, got {type(val).__name__}"
        return True, ""

    @staticmethod
    def _type_check(val: Any, expected: str) -> bool:
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected_cls = type_map.get(expected)
        if expected_cls is None:
            return True
        if isinstance(expected_cls, tuple):
            return isinstance(val, expected_cls)
        return isinstance(val, expected_cls)


# =============================================================================
# Syscall Handler Interface
# =============================================================================
class SyscallHandler(ABC):
    @abstractmethod
    def handle(self, request: SyscallRequest) -> SyscallResponse: ...

    @abstractmethod
    def get_schema(self, operation: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def list_operations(self) -> List[str]: ...


# =============================================================================
# LLM Syscall Handler
# =============================================================================
class LLMSyscallHandler(SyscallHandler):
    """Handle LLM inference syscalls."""

    def __init__(self, inference_engine: Any = None) -> None:
        self.engine = inference_engine
        self._schemas = {
            "generate": {
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string"},
                    "max_tokens": {"type": "integer"},
                    "temperature": {"type": "number"},
                },
            },
            "embed": {
                "required": ["text"],
                "properties": {
                    "text": {"type": "string"},
                    "model": {"type": "string"},
                },
            },
        }

    def handle(self, request: SyscallRequest) -> SyscallResponse:
        t0 = time.perf_counter()
        op = request.operation
        if op == "generate":
            prompt = request.parameters.get("prompt", "")
            # Stub: return echo
            result = f"[LLM Response to: {prompt[:50]}...]"
            return SyscallResponse(
                syscall_id=request.syscall_id,
                status=SyscallStatus.SUCCESS,
                result=result,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        elif op == "embed":
            text = request.parameters.get("text", "")
            # Stub: return hash-based embedding
            emb = [hash(text + str(i)) % 1000 / 1000.0 for i in range(128)]
            return SyscallResponse(
                syscall_id=request.syscall_id,
                status=SyscallStatus.SUCCESS,
                result=emb,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        return SyscallResponse(
            syscall_id=request.syscall_id,
            status=SyscallStatus.FAILED,
            error=f"Unknown operation: {op}",
        )

    def get_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        return self._schemas.get(operation)

    def list_operations(self) -> List[str]:
        return list(self._schemas.keys())


# =============================================================================
# Memory Syscall Handler
# =============================================================================
class MemorySyscallHandler(SyscallHandler):
    """Handle memory read/write syscalls."""

    def __init__(self, memory_store: Any = None) -> None:
        self.store = memory_store or {}
        self._schemas = {
            "read": {
                "required": ["key"],
                "properties": {"key": {"type": "string"}, "namespace": {"type": "string"}},
            },
            "write": {
                "required": ["key", "value"],
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "object"},
                    "namespace": {"type": "string"},
                    "ttl": {"type": "integer"},
                },
            },
            "delete": {
                "required": ["key"],
                "properties": {"key": {"type": "string"}, "namespace": {"type": "string"}},
            },
        }

    def handle(self, request: SyscallRequest) -> SyscallResponse:
        t0 = time.perf_counter()
        op = request.operation
        ns = request.parameters.get("namespace", "default")
        key = request.parameters.get("key", "")
        if op == "read":
            ns_store = self.store.get(ns, {})
            val = ns_store.get(key)
            return SyscallResponse(
                syscall_id=request.syscall_id,
                status=SyscallStatus.SUCCESS if val is not None else SyscallStatus.FAILED,
                result=val,
                error="" if val is not None else "Key not found",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        elif op == "write":
            if ns not in self.store:
                self.store[ns] = {}
            self.store[ns][key] = request.parameters.get("value")
            return SyscallResponse(
                syscall_id=request.syscall_id,
                status=SyscallStatus.SUCCESS,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        elif op == "delete":
            ns_store = self.store.get(ns, {})
            removed = ns_store.pop(key, None) is not None
            return SyscallResponse(
                syscall_id=request.syscall_id,
                status=SyscallStatus.SUCCESS if removed else SyscallStatus.FAILED,
                error="" if removed else "Key not found",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        return SyscallResponse(
            syscall_id=request.syscall_id,
            status=SyscallStatus.FAILED,
            error=f"Unknown operation: {op}",
        )

    def get_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        return self._schemas.get(operation)

    def list_operations(self) -> List[str]:
        return list(self._schemas.keys())


# =============================================================================
# Storage Syscall Handler
# =============================================================================
class StorageSyscallHandler(SyscallHandler):
    """Handle file/storage syscalls."""

    def __init__(self) -> None:
        self._schemas = {
            "read_file": {"required": ["path"], "properties": {"path": {"type": "string"}}},
            "write_file": {"required": ["path", "content"], "properties": {"path": {"type": "string"}, "content": {"type": "string"}}},
            "list_dir": {"required": ["path"], "properties": {"path": {"type": "string"}}},
        }

    def handle(self, request: SyscallRequest) -> SyscallResponse:
        t0 = time.perf_counter()
        op = request.operation
        import os
        path = request.parameters.get("path", "")
        try:
            if op == "read_file":
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                return SyscallResponse(
                    syscall_id=request.syscall_id,
                    status=SyscallStatus.SUCCESS,
                    result=content,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            elif op == "write_file":
                content = request.parameters.get("content", "")
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return SyscallResponse(
                    syscall_id=request.syscall_id,
                    status=SyscallStatus.SUCCESS,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            elif op == "list_dir":
                entries = os.listdir(path) if os.path.isdir(path) else []
                return SyscallResponse(
                    syscall_id=request.syscall_id,
                    status=SyscallStatus.SUCCESS,
                    result=entries,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
        except Exception as exc:
            return SyscallResponse(
                syscall_id=request.syscall_id,
                status=SyscallStatus.FAILED,
                error=str(exc),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        return SyscallResponse(
            syscall_id=request.syscall_id,
            status=SyscallStatus.FAILED,
            error=f"Unknown operation: {op}",
        )

    def get_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        return self._schemas.get(operation)

    def list_operations(self) -> List[str]:
        return list(self._schemas.keys())


# =============================================================================
# Tool Syscall Handler
# =============================================================================
class ToolSyscallHandler(SyscallHandler):
    """Handle tool execution syscalls."""

    def __init__(self, tool_registry: Any = None) -> None:
        self.tools = tool_registry or {}
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, name: str, schema: Dict[str, Any], fn: Callable[[Dict[str, Any]], Any]) -> None:
        self.tools[name] = fn
        self._schemas[name] = schema

    def handle(self, request: SyscallRequest) -> SyscallResponse:
        t0 = time.perf_counter()
        tool_name = request.operation
        fn = self.tools.get(tool_name)
        if not fn:
            return SyscallResponse(
                syscall_id=request.syscall_id,
                status=SyscallStatus.FAILED,
                error=f"Tool '{tool_name}' not found",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        try:
            result = fn(request.parameters)
            return SyscallResponse(
                syscall_id=request.syscall_id,
                status=SyscallStatus.SUCCESS,
                result=result,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return SyscallResponse(
                syscall_id=request.syscall_id,
                status=SyscallStatus.FAILED,
                error=str(exc),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    def get_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        return self._schemas.get(operation)

    def list_operations(self) -> List[str]:
        return list(self.tools.keys())


# =============================================================================
# Syscall Dispatcher
# =============================================================================
class SyscallDispatcher:
    """Central dispatcher routing syscalls to appropriate handlers."""

    def __init__(self) -> None:
        self._handlers: Dict[SyscallType, SyscallHandler] = {}
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []
        self._validators: Dict[str, SchemaValidator] = {}

    def register(self, type: SyscallType, handler: SyscallHandler) -> None:
        with self._lock:
            self._handlers[type] = handler

    def dispatch(self, request: SyscallRequest) -> SyscallResponse:
        t0 = time.perf_counter()
        handler = self._handlers.get(request.type)
        if not handler:
            return SyscallResponse(
                syscall_id=request.syscall_id,
                status=SyscallStatus.FAILED,
                error=f"No handler for syscall type: {request.type.value}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        # Validate schema
        schema = handler.get_schema(request.operation)
        if schema:
            ok, err = SchemaValidator.validate(request.parameters, schema)
            if not ok:
                return SyscallResponse(
                    syscall_id=request.syscall_id,
                    status=SyscallStatus.FAILED,
                    error=f"Schema validation failed: {err}",
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
        resp = handler.handle(request)
        with self._lock:
            self._history.append({
                "syscall_id": request.syscall_id,
                "type": request.type.value,
                "operation": request.operation,
                "status": resp.status.value,
                "duration_ms": resp.duration_ms,
                "agent_id": request.agent_id,
            })
        return resp

    def list_types(self) -> List[SyscallType]:
        with self._lock:
            return list(self._handlers.keys())

    def list_operations(self, type: SyscallType) -> List[str]:
        handler = self._handlers.get(type)
        return handler.list_operations() if handler else []

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)[-limit:]


# =============================================================================
# Syscall Factory
# =============================================================================
class SyscallFactory:
    """Create pre-configured syscall dispatchers."""

    @staticmethod
    def create_standard() -> SyscallDispatcher:
        dispatcher = SyscallDispatcher()
        dispatcher.register(SyscallType.LLM, LLMSyscallHandler())
        dispatcher.register(SyscallType.MEMORY, MemorySyscallHandler())
        dispatcher.register(SyscallType.STORAGE, StorageSyscallHandler())
        dispatcher.register(SyscallType.TOOL, ToolSyscallHandler())
        return dispatcher


# =============================================================================
# Syscall Kernel Bridge
# =============================================================================
class SyscallKernelBridge:
    def __init__(self, dispatcher: SyscallDispatcher, event_bus: Any = None) -> None:
        self.dispatcher = dispatcher
        self.bus = event_bus

    def call(self, agent_id: str, type: SyscallType, operation: str, parameters: Dict[str, Any]) -> SyscallResponse:
        req = SyscallRequest(
            syscall_id=hashlib.sha256(f"{agent_id}:{time.time()}".encode()).hexdigest()[:16],
            type=type,
            operation=operation,
            parameters=parameters,
            agent_id=agent_id,
        )
        resp = self.dispatcher.dispatch(req)
        if self.bus:
            self.bus.publish("syscall.completed", {
                "syscall_id": resp.syscall_id,
                "type": type.value,
                "operation": operation,
                "status": resp.status.value,
                "agent_id": agent_id,
            })
        return resp


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Syscall Layer Demo")
    print("=" * 60)
    dispatcher = SyscallFactory.create_standard()
    bridge = SyscallKernelBridge(dispatcher)

    # LLM syscall
    resp1 = bridge.call("agent-1", SyscallType.LLM, "generate", {"prompt": "What is AI?", "model": "gpt-4"})
    print(f"LLM: {resp1.status.value} — {resp1.result}")

    # Memory syscall
    resp2 = bridge.call("agent-1", SyscallType.MEMORY, "write", {"key": "test", "value": {"data": 42}, "namespace": "demo"})
    print(f"Memory write: {resp2.status.value}")
    resp3 = bridge.call("agent-1", SyscallType.MEMORY, "read", {"key": "test", "namespace": "demo"})
    print(f"Memory read: {resp3.status.value} — {resp3.result}")

    # Tool syscall
    tool_handler = ToolSyscallHandler()
    tool_handler.register_tool("calculator", {"required": ["a", "b"]}, lambda p: p.get("a", 0) + p.get("b", 0))
    dispatcher.register(SyscallType.TOOL, tool_handler)
    resp4 = bridge.call("agent-1", SyscallType.TOOL, "calculator", {"a": 10, "b": 20})
    print(f"Tool: {resp4.status.value} — {resp4.result}")

    # Invalid syscall
    resp5 = bridge.call("agent-1", SyscallType.LLM, "nonexistent", {})
    print(f"Invalid: {resp5.status.value} — {resp5.error}")

    print("\nDemo complete.")


if __name__ == "__main__":
    run_demo()
