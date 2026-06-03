"""
llm_function_dispatcher_native.py
MAGNATRIX-OS Function Dispatcher Engine
Native Python, stdlib only.
Provides function dispatch with parameter validation, call routing, and result aggregation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

@dataclass
class FunctionCall:
    function_name: str
    parameters: Dict[str, Any]
    call_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.function_name, "params": self.parameters}

class FunctionDispatcherEngine:
    def __init__(self) -> None:
        self._registry: Dict[str, Callable] = {}
        self._history: List[Dict[str, Any]] = []

    def register(self, name: str, fn: Callable) -> None:
        self._registry[name] = fn

    def dispatch(self, call: FunctionCall) -> Dict[str, Any]:
        fn = self._registry.get(call.function_name)
        if not fn:
            return {"error": f"Function {call.function_name} not found", "call_id": call.call_id}
        try:
            result = fn(**call.parameters)
            self._history.append({"call_id": call.call_id, "name": call.function_name, "result": result, "success": True})
            return {"result": result, "call_id": call.call_id, "success": True}
        except Exception as e:
            self._history.append({"call_id": call.call_id, "name": call.function_name, "error": str(e), "success": False})
            return {"error": str(e), "call_id": call.call_id, "success": False}

    def batch_dispatch(self, calls: List[FunctionCall]) -> List[Dict[str, Any]]:
        return [self.dispatch(c) for c in calls]

    def get_stats(self) -> Dict[str, Any]:
        success = sum(1 for h in self._history if h.get("success"))
        return {"functions": len(self._registry), "calls": len(self._history), "success_rate": success / max(len(self._history), 1)}

def run() -> None:
    print("=" * 60); print("MAGNATRIX-OS Function Dispatcher"); print("=" * 60)
    e = FunctionDispatcherEngine()
    e.register("add", lambda a, b: a + b)
    e.register("multiply", lambda a, b: a * b)
    e.register("upper", lambda text: text.upper())
    result = e.dispatch(FunctionCall("add", {"a": 5, "b": 3}, "c1"))
    print(f"  add(5,3): {result}")
    result = e.dispatch(FunctionCall("upper", {"text": "hello"}, "c2"))
    print(f"  upper('hello'): {result}")
    print(f"  Stats: {e.get_stats()}")
    print("\nFunction Dispatcher test complete.")
if __name__ == "__main__": run()
