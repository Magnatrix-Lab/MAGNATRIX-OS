"""
nuclei_dsl_executor_native.py
MAGNATRIX-OS — Nuclei DSL Executor

Execute Nuclei DSL expressions (duration, status_code, body length, contains). Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class DSLResult:
    expression: str
    result: bool
    context: Dict[str, Any]


class NucleiDSLExecutor:
    """Execute Nuclei DSL expressions for matchers and extractors."""

    def __init__(self, cache_dir: str = "./dsl_executor"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, DSLResult] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.results[rid] = DSLResult(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.results.items()}, f, indent=2)

    def evaluate(self, result_id: str, expression: str, context: Dict[str, Any]) -> DSLResult:
        """Evaluate a DSL expression against context."""
        result = False
        expr_lower = expression.lower()

        # duration checks
        if "duration" in expr_lower and ">=" in expr_lower:
            try:
                threshold = float(expression.split(">=")[1].strip().split()[0])
                result = context.get("duration", 0) >= threshold
            except ValueError:
                pass
        elif "duration" in expr_lower and ">" in expr_lower:
            try:
                threshold = float(expression.split(">")[1].strip().split()[0])
                result = context.get("duration", 0) > threshold
            except ValueError:
                pass

        # status_code checks
        elif "status_code" in expr_lower and "==" in expr_lower:
            try:
                expected = int(expression.split("==")[1].strip().split()[0])
                result = context.get("status_code", -1) == expected
            except ValueError:
                pass
        elif "status_code" in expr_lower and "!=" in expr_lower:
            try:
                expected = int(expression.split("!=")[1].strip().split()[0])
                result = context.get("status_code", -1) != expected
            except ValueError:
                pass

        # body length checks
        elif "len(body)" in expr_lower and ">" in expr_lower:
            try:
                threshold = int(expression.split(">")[1].strip().split()[0])
                result = len(context.get("body", "")) > threshold
            except ValueError:
                pass
        elif "len(body)" in expr_lower and "<" in expr_lower:
            try:
                threshold = int(expression.split("<")[1].strip().split()[0])
                result = len(context.get("body", "")) < threshold
            except ValueError:
                pass

        # contains checks
        elif "contains(" in expr_lower and "body" in expr_lower:
            try:
                # Extract string argument from contains(body, "string")
                args = expression.split("contains(")[1].split(")")[0]
                parts = args.split(",")
                if len(parts) >= 2:
                    search_str = parts[1].strip().strip('"\'')
                    result = search_str in context.get("body", "")
            except Exception:
                pass

        # version comparison
        elif "version" in expr_lower and "(" in expr_lower:
            try:
                # Simple version check: compare("version", "< 1.2.3")
                if "<" in expression:
                    ver_str = expression.split("<")[1].strip().strip('"\'')
                    body = context.get("body", "")
                    result = ver_str in body
            except Exception:
                pass

        r = DSLResult(expression=expression, result=result, context=context)
        self.results[result_id] = r
        self._save()
        return r

    def evaluate_batch(self, expressions: List[str], context: Dict[str, Any]) -> Dict[str, bool]:
        return {expr: self.evaluate(f"batch_{i}", expr, context).result for i, expr in enumerate(expressions)}

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        true_count = sum(1 for r in self.results.values() if r.result)
        return {"total_evaluated": total, "true": true_count, "false": total - true_count}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["NucleiDSLExecutor", "DSLResult"]