"""Function Calling Engine — Tool schema parsing, execution, validation, retry.

Modul ini menyediakan:
- SchemaParser untuk JSON schema validation dan coercion
- FunctionRegistry untuk tool discovery dan management
- ToolExecutor dengan argument validation dan error handling
- Retry mechanism dengan exponential backoff
- Result type coercion dan formatting
"""

from __future__ import annotations

import json
import time
import uuid
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from enum import Enum, auto


class ToolStatus(Enum):
    AVAILABLE = auto()
    DISABLED = auto()
    DEPRECATED = auto()
    ERROR = auto()


class ExecutionStatus(Enum):
    SUCCESS = auto()
    FAILED = auto()
    RETRYING = auto()
    TIMEOUT = auto()
    VALIDATION_ERROR = auto()


@dataclass
class ToolSchema:
    """JSON schema definition untuk sebuah tool."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    returns: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required
                }
            }
        }, indent=2)


@dataclass
class ToolCall:
    """Single function call request."""
    call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolResult:
    """Result dari tool execution."""
    call_id: str
    tool_name: str
    status: ExecutionStatus
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    attempts: int = 0


class SchemaValidator:
    """Validasi arguments terhadap schema."""

    def validate(self, schema: ToolSchema, arguments: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        # Check required fields
        for req in schema.required:
            if req not in arguments:
                errors.append(f"Missing required parameter: {req}")
        # Check type compatibility (simplified)
        for param, spec in schema.parameters.items():
            if param in arguments:
                expected_type = spec.get("type", "any")
                val = arguments[param]
                if not self._check_type(val, expected_type):
                    errors.append(f"Parameter {param}: expected {expected_type}, got {type(val).__name__}")
        return len(errors) == 0, errors

    def _check_type(self, val: Any, expected: str) -> bool:
        type_map = {
            "string": str, "integer": int, "number": (int, float),
            "boolean": bool, "array": list, "object": dict
        }
        expected_cls = type_map.get(expected)
        if expected_cls is None:
            return True
        if isinstance(expected_cls, tuple):
            return isinstance(val, expected_cls)
        return isinstance(val, expected_cls)

    def coerce(self, schema: ToolSchema, arguments: Dict[str, Any]) -> Dict[str, Any]:
        coerced = dict(arguments)
        for param, spec in schema.parameters.items():
            if param in coerced:
                expected_type = spec.get("type")
                coerced[param] = self._coerce_value(coerced[param], expected_type)
        return coerced

    def _coerce_value(self, val: Any, target_type: Optional[str]) -> Any:
        try:
            if target_type == "string":
                return str(val)
            elif target_type == "integer":
                return int(val) if not isinstance(val, bool) else int(val)
            elif target_type == "number":
                return float(val)
            elif target_type == "boolean":
                if isinstance(val, str):
                    return val.lower() in ("true", "1", "yes", "on")
                return bool(val)
        except (ValueError, TypeError):
            pass
        return val


class FunctionRegistry:
    """Register dan manage available tools."""

    def __init__(self):
        self._tools: Dict[str, Tuple[ToolSchema, Callable, ToolStatus]] = {}
        self._schemas: Dict[str, ToolSchema] = {}

    def register(self, schema: ToolSchema, fn: Callable, status: ToolStatus = ToolStatus.AVAILABLE) -> None:
        self._tools[schema.name] = (schema, fn, status)
        self._schemas[schema.name] = schema

    def register_from_function(self, fn: Callable, description: str = "", status: ToolStatus = ToolStatus.AVAILABLE) -> ToolSchema:
        sig = inspect.signature(fn)
        params = {}
        required = []
        for name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == list:
                param_type = "array"
            elif param.annotation == dict:
                param_type = "object"
            params[name] = {"type": param_type, "description": f"Parameter {name}"}
            if param.default == inspect.Parameter.empty:
                required.append(name)
        schema = ToolSchema(
            name=fn.__name__,
            description=description or fn.__doc__ or f"Function {fn.__name__}",
            parameters=params,
            required=required
        )
        self.register(schema, fn, status)
        return schema

    def get(self, tool_name: str) -> Optional[Tuple[ToolSchema, Callable, ToolStatus]]:
        return self._tools.get(tool_name)

    def get_schema(self, tool_name: str) -> Optional[ToolSchema]:
        return self._schemas.get(tool_name)

    def list_available(self) -> List[str]:
        return [name for name, (_, _, status) in self._tools.items() if status == ToolStatus.AVAILABLE]

    def list_all(self) -> List[ToolSchema]:
        return [s for s in self._schemas.values()]

    def disable(self, tool_name: str) -> None:
        if tool_name in self._tools:
            schema, fn, _ = self._tools[tool_name]
            self._tools[tool_name] = (schema, fn, ToolStatus.DISABLED)

    def export_schemas(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([json.loads(s.to_json()) for s in self._schemas.values()], f, indent=2)


class RetryPolicy:
    """Configurable retry policy."""

    def __init__(self, max_retries: int = 3, backoff_base: float = 1.0, backoff_max: float = 30.0, timeout: float = 10.0):
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.timeout = timeout

    def get_delay(self, attempt: int) -> float:
        return min(self.backoff_base * (2 ** attempt), self.backoff_max)


class ToolExecutor:
    """Execute tool calls dengan validation, retry, dan error handling."""

    def __init__(self, registry: FunctionRegistry, retry_policy: Optional[RetryPolicy] = None):
        self.registry = registry
        self.validator = SchemaValidator()
        self.retry = retry_policy or RetryPolicy()
        self._history: List[ToolResult] = []

    def execute(self, call: ToolCall) -> ToolResult:
        entry = self.registry.get(call.tool_name)
        if not entry:
            return ToolResult(call.call_id, call.tool_name, ExecutionStatus.FAILED, error=f"Tool '{call.tool_name}' not found")
        schema, fn, status = entry
        if status != ToolStatus.AVAILABLE:
            return ToolResult(call.call_id, call.tool_name, ExecutionStatus.FAILED, error=f"Tool '{call.tool_name}' is {status.name}")

        # Coerce types first, then validate
        args = self.validator.coerce(schema, call.arguments)
        valid, errors = self.validator.validate(schema, args)
        if not valid:
            return ToolResult(call.call_id, call.tool_name, ExecutionStatus.VALIDATION_ERROR, error="; ".join(errors))

        # Execute with retry
        start = time.time()
        attempts = 0
        while attempts <= self.retry.max_retries:
            attempts += 1
            try:
                if time.time() - start > self.retry.timeout:
                    return ToolResult(call.call_id, call.tool_name, ExecutionStatus.TIMEOUT, error="Timeout", duration=time.time()-start, attempts=attempts)
                output = fn(**args)
                dur = time.time() - start
                result = ToolResult(call.call_id, call.tool_name, ExecutionStatus.SUCCESS, output=output, duration=dur, attempts=attempts)
                self._history.append(result)
                return result
            except Exception as e:
                if attempts > self.retry.max_retries:
                    dur = time.time() - start
                    result = ToolResult(call.call_id, call.tool_name, ExecutionStatus.FAILED, error=str(e), duration=dur, attempts=attempts)
                    self._history.append(result)
                    return result
                time.sleep(self.retry.get_delay(attempts - 1))
        return ToolResult(call.call_id, call.tool_name, ExecutionStatus.FAILED, error="Retries exhausted", duration=time.time()-start, attempts=attempts)

    def execute_batch(self, calls: List[ToolCall]) -> List[ToolResult]:
        return [self.execute(c) for c in calls]

    def get_history(self) -> List[ToolResult]:
        return self._history

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._history)
        success = sum(1 for r in self._history if r.status == ExecutionStatus.SUCCESS)
        return {
            "total_calls": total,
            "successful": success,
            "failed": total - success,
            "success_rate": success / max(total, 1)
        }


class FunctionCallingEngine:
    """Main orchestrator untuk function calling."""

    def __init__(self):
        self.registry = FunctionRegistry()
        self.executor = ToolExecutor(self.registry)

    def register_tool(self, schema: ToolSchema, fn: Callable) -> None:
        self.registry.register(schema, fn)

    def call(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        call = ToolCall(
            call_id=str(uuid.uuid4())[:12],
            tool_name=tool_name,
            arguments=arguments
        )
        return self.executor.execute(call)

    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [json.loads(s.to_json()) for s in self.registry.list_all()]

    def export_tools(self, path: str) -> None:
        self.registry.export_schemas(path)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("FUNCTION CALLING ENGINE DEMO")
    print("=" * 70)

    # 1. Register tools
    print("\n[1] Register Tools")
    engine = FunctionCallingEngine()

    def add(a: int, b: int) -> int:
        return a + b

    def concat(strings: list) -> str:
        return " ".join(strings)

    def search(query: str, max_results: int = 5) -> List[str]:
        return [f"Result {i} for '{query}'" for i in range(1, max_results + 1)]

    engine.register_tool(ToolSchema(
        name="add", description="Add two numbers",
        parameters={"a": {"type": "integer"}, "b": {"type": "integer"}},
        required=["a", "b"]
    ), add)

    engine.register_tool(ToolSchema(
        name="concat", description="Concatenate strings",
        parameters={"strings": {"type": "array"}},
        required=["strings"]
    ), concat)

    engine.register_tool(ToolSchema(
        name="search", description="Search for results",
        parameters={"query": {"type": "string"}, "max_results": {"type": "integer"}},
        required=["query"]
    ), search)

    # Auto-register
    def divide(dividend: float, divisor: float) -> float:
        return dividend / divisor

    schema = engine.registry.register_from_function(divide, "Divide two numbers")
    print(f"  Auto-registered: {schema.name} with params {list(schema.parameters.keys())}")
    print(f"  Available tools: {engine.registry.list_available()}")

    # 2. Execute tool calls
    print("\n[2] Execute Tool Calls")
    r1 = engine.call("add", {"a": 5, "b": 3})
    print(f"  add(5,3): {r1.status.name} -> {r1.output} (in {r1.duration:.4f}s, {r1.attempts} attempts)")

    r2 = engine.call("concat", {"strings": ["Hello", "World"]})
    print(f"  concat(['Hello','World']): {r2.status.name} -> {r2.output}")

    r3 = engine.call("search", {"query": "Python", "max_results": 3})
    print(f"  search('Python', 3): {r3.status.name} -> {r3.output}")

    # 3. Validation errors
    print("\n[3] Validation")
    r4 = engine.call("add", {"a": "not_a_number"})
    print(f"  add('not_a_number', ?): {r4.status.name} -> {r4.error}")

    r5 = engine.call("add", {"a": 5})
    print(f"  add(5, missing): {r5.status.name} -> {r5.error}")

    # 4. Coercion
    print("\n[4] Type Coercion")
    r6 = engine.call("add", {"a": "10", "b": "20"})
    print(f"  add('10', '20') coerced: {r6.status.name} -> {r6.output}")

    r7 = engine.call("divide", {"dividend": "100", "divisor": "4"})
    print(f"  divide('100', '4') coerced: {r7.status.name} -> {r7.output}")

    # 5. Retry on error
    print("\n[5] Retry Mechanism")
    fail_count = 0
    def sometimes_fails() -> str:
        nonlocal fail_count
        fail_count += 1
        if fail_count < 3:
            raise RuntimeError("Simulated failure")
        return "Success after retries!"

    engine.register_tool(ToolSchema(name="fragile", description="Sometimes fails", parameters={}, required=[]), sometimes_fails)
    retry_exec = ToolExecutor(engine.registry, RetryPolicy(max_retries=3, backoff_base=0.1))
    r8 = retry_exec.execute(ToolCall("c1", "fragile", {}))
    print(f"  fragile(): {r8.status.name} -> {r8.output} (attempts: {r8.attempts})")

    # 6. Stats and export
    print("\n[6] Stats and Export")
    print(f"  Execution stats: {engine.executor.get_stats()}")
    engine.export_tools("/tmp/tools_schema.json")
    print(f"  Exported schemas to /tmp/tools_schema.json")

    # 7. Disabled tool
    print("\n[7] Tool Status Management")
    engine.registry.disable("add")
    r9 = engine.call("add", {"a": 1, "b": 2})
    print(f"  add after disable: {r9.status.name} -> {r9.error}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
