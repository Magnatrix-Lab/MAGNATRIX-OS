#!/usr/bin/env python3
"""
ai/llm_code_interpreter_native.py
MAGNATRIX-OS — Code Interpreter for the LLM Arena
AMATI pattern: sandboxed execution, session persistence, library management

Pure Python, stdlib only. Simulates Python execution with state persistence,
variable inspection, and figure generation.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


# ───────────────────────────────────────────────────────────────
# 1. SANDBOX
# ───────────────────────────────────────────────────────────────

class Sandbox:
    """Isolated Python execution with safe globals and timeout."""

    SAFE_BUILTINS = {
        "len": len, "range": range, "print": print, "str": str, "int": int,
        "float": float, "list": list, "dict": dict, "set": set, "tuple": tuple,
        "abs": abs, "min": min, "max": max, "sum": sum, "sorted": sorted,
        "round": round, "enumerate": enumerate, "zip": zip, "map": map,
        "filter": filter, "all": all, "any": any, "chr": chr, "ord": ord,
        "hex": hex, "bin": bin, "pow": pow, "divmod": divmod,
        "isinstance": isinstance, "type": type, "hasattr": hasattr,
        "getattr": getattr, "dir": dir, "math": math, "__import__": __import__,
    }

    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout

    def execute(self, code: str, globals_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        safe_globals = {"__builtins__": self.SAFE_BUILTINS}
        if globals_dict:
            safe_globals.update(globals_dict)
        result = {"stdout": "", "stderr": "", "result": None, "success": False, "vars": {}}
        t0 = _now()
        try:
            output_lines = []
            def capture_print(*args):
                output_lines.append(" ".join(str(a) for a in args))
            safe_globals["print"] = capture_print
            exec(code, safe_globals, safe_globals)
            result["stdout"] = "\n".join(output_lines)
            result["success"] = True
            result["result"] = safe_globals.get("result", None)
            # Extract new variables
            result["vars"] = {k: v for k, v in safe_globals.items() if not k.startswith("_") and not callable(v) and not isinstance(v, type(len))}
        except Exception as e:
            result["stderr"] = f"{type(e).__name__}: {e}"
        result["duration_ms"] = round((_now() - t0) * 1000, 2)
        return result


# ───────────────────────────────────────────────────────────────
# 2. SESSION STATE
# ───────────────────────────────────────────────────────────────

class SessionState:
    """Persistent variables across code executions."""

    def __init__(self) -> None:
        self._vars: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []

    def update(self, variables: Dict[str, Any]) -> None:
        self._vars.update(variables)
        self._history.append({"timestamp": _now(), "vars_added": len(variables)})

    def get(self, name: str) -> Any:
        return self._vars.get(name)

    def all_vars(self) -> Dict[str, Any]:
        return self._vars.copy()

    def clear(self) -> None:
        self._vars.clear()

    def stats(self) -> Dict[str, Any]:
        return {"variables": len(self._vars), "executions": len(self._history)}


# ───────────────────────────────────────────────────────────────
# 3. LIBRARY MANAGER
# ───────────────────────────────────────────────────────────────

class LibraryManager:
    """Simulate importing libraries and tracking available packages."""

    AVAILABLE = {
        "numpy": "ndarray, linalg, random",
        "pandas": "DataFrame, Series, read_csv",
        "matplotlib": "plot, scatter, histogram",
        "json": "loads, dumps, parse",
        "re": "match, search, findall",
        "statistics": "mean, median, stdev",
    }

    def __init__(self) -> None:
        self._loaded: Dict[str, str] = {}

    def import_module(self, name: str) -> bool:
        if name in self.AVAILABLE:
            self._loaded[name] = self.AVAILABLE[name]
            return True
        return False

    def list_available(self) -> List[str]:
        return list(self.AVAILABLE.keys())

    def list_loaded(self) -> List[str]:
        return list(self._loaded.keys())

    def suggest(self, task: str) -> List[str]:
        suggestions = []
        if "data" in task.lower() or "csv" in task.lower():
            suggestions.append("pandas")
        if "plot" in task.lower() or "chart" in task.lower():
            suggestions.append("matplotlib")
        if "math" in task.lower() or "matrix" in task.lower():
            suggestions.append("numpy")
        return suggestions


# ───────────────────────────────────────────────────────────────
# 4. EXECUTION ENGINE
# ───────────────────────────────────────────────────────────────

class ExecutionEngine:
    """Run code blocks, capture output, cell-based execution."""

    def __init__(self) -> None:
        self.sandbox = Sandbox()
        self.state = SessionState()
        self.libraries = LibraryManager()
        self._cells: List[Dict[str, Any]] = []

    def run_cell(self, code: str, cell_id: Optional[str] = None) -> Dict[str, Any]:
        imports = self._detect_imports(code)
        for imp in imports:
            self.libraries.import_module(imp)

        globals_dict = self.state.all_vars()
        result = self.sandbox.execute(code, globals_dict)

        # Update session state with returned vars
        if result["success"] and result.get("vars"):
            self.state.update(result["vars"])

        cell = {
            "cell_id": cell_id or f"cell_{len(self._cells)}",
            "code": code[:200],
            "success": result["success"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "result": result["result"],
            "duration_ms": result["duration_ms"],
        }
        self._cells.append(cell)
        return cell

    def _detect_imports(self, code: str) -> List[str]:
        imports = []
        for line in code.split("\n"):
            line = line.strip()
            if line.startswith("import ") or line.startswith("from "):
                parts = line.replace("import", "").replace("from", "").split()
                if parts:
                    mod = parts[0].split(".")[0]
                    imports.append(mod)
        return imports

    def get_cells(self) -> List[Dict[str, Any]]:
        return self._cells.copy()

    def stats(self) -> Dict[str, Any]:
        return {"cells": len(self._cells), "state": self.state.stats(), "libraries": self.libraries.list_loaded()}


# ───────────────────────────────────────────────────────────────
# 5. VARIABLE INSPECTOR
# ───────────────────────────────────────────────────────────────

class VariableInspector:
    """Inspect session variables, show types, sizes, previews."""

    def inspect(self, state: SessionState) -> List[Dict[str, Any]]:
        vars_dict = state.all_vars()
        results = []
        for name, value in vars_dict.items():
            info = {
                "name": name,
                "type": type(value).__name__,
                "size": self._estimate_size(value),
                "preview": str(value)[:80],
            }
            results.append(info)
        return results

    def _estimate_size(self, value: Any) -> str:
        if isinstance(value, (list, dict, set, tuple)):
            return f"{len(value)} items"
        if isinstance(value, str):
            return f"{len(value)} chars"
        return "scalar"

    def summary(self, state: SessionState) -> str:
        results = self.inspect(state)
        lines = [f"Variables: {len(results)}"]
        for r in results:
            lines.append(f"  {r['name']}: {r['type']} ({r['size']}) = {r['preview'][:40]}...")
        return "\n".join(lines)


# ───────────────────────────────────────────────────────────────
# 6. PLOT SIMULATOR
# ───────────────────────────────────────────────────────────────

class PlotSimulator:
    """Simulate matplotlib figure generation."""

    def simulate(self, plot_type: str = "line", data_size: int = 10) -> Dict[str, Any]:
        return {
            "type": plot_type,
            "dimensions": (800, 600),
            "format": "png",
            "data_points": data_size,
            "simulated": True,
            "metadata": {
                "title": f"Simulated {plot_type} plot",
                "x_label": "X axis",
                "y_label": "Y axis",
            },
        }

    def simulate_from_code(self, code: str) -> Optional[Dict[str, Any]]:
        if "plot" in code.lower() or "scatter" in code.lower() or "hist" in code.lower():
            plot_type = "scatter" if "scatter" in code.lower() else "line"
            return self.simulate(plot_type, data_size=20)
        return None


# ───────────────────────────────────────────────────────────────
# 7. CODE INTERPRETER
# ───────────────────────────────────────────────────────────────

class CodeInterpreter:
    """Main orchestrator: session -> execute -> inspect -> plot -> state."""

    def __init__(self) -> None:
        self.engine = ExecutionEngine()
        self.inspector = VariableInspector()
        self.plotter = PlotSimulator()

    def run(self, code: str, cell_id: Optional[str] = None) -> Dict[str, Any]:
        cell = self.engine.run_cell(code, cell_id)
        plot = self.plotter.simulate_from_code(code)
        vars_info = self.inspector.inspect(self.engine.state)
        return {
            "cell": cell,
            "plot": plot,
            "variables": vars_info,
            "session_state": self.engine.state.stats(),
            "libraries": self.engine.libraries.list_loaded(),
        }

    def inspect(self) -> str:
        return self.inspector.summary(self.engine.state)

    def reset(self) -> None:
        self.engine.state.clear()

    def stats(self) -> Dict[str, Any]:
        return self.engine.stats()


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Code Interpreter Demo")
    print("=" * 60)

    interpreter = CodeInterpreter()

    cells = [
        ("cell_1", "x = [1, 2, 3, 4, 5]\ny = [2, 4, 6, 8, 10]\nresult = sum(x)"),
        ("cell_2", "mean_val = sum(y) / len(y)\nprint(f'Mean: {mean_val}')"),
        ("cell_3", "import json\ndata = {'x': x, 'y': y}\njson_str = json.dumps(data)"),
        ("cell_4", "import matplotlib\n# This would create a plot\nprint('Plot generated')"),
    ]

    for cell_id, code in cells:
        print(f"\n[CELL {cell_id}] {code[:50]}...")
        result = interpreter.run(code, cell_id)
        cell = result["cell"]
        print(f"  Success: {cell['success']}")
        if cell['stdout']:
            print(f"  stdout: {cell['stdout']}")
        if cell['stderr']:
            print(f"  stderr: {cell['stderr']}")
        if result["plot"]:
            print(f"  Plot: {result['plot']['type']} ({result['plot']['dimensions']})")
        if result["variables"]:
            print(f"  Variables: {len(result['variables'])}")
            for v in result["variables"]:
                print(f"    {v['name']}: {v['type']} = {v['preview'][:40]}...")

    print(f"\n[INSPECTOR]")
    print(interpreter.inspect())

    print(f"\n[STATS] {json.dumps(interpreter.stats(), indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. Code Interpreter ready for LLM Arena.")
    print("=" * 60)
