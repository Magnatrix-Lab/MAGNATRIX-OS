#!/usr/bin/env python3
"""
Natural Language Query Engine for MAGNATRIX-OS
Parse natural language → auto-generate query → execute → format result.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class NLQuery:
    """Parsed natural language query."""
    original: str
    intent: str
    target: str
    filters: Dict[str, Any] = field(default_factory=dict)
    aggregations: List[str] = field(default_factory=list)
    time_range: Optional[Tuple[float, float]] = None
    sort_by: Optional[str] = None
    limit: int = 10


@dataclass
class NLQResult:
    """Result of a natural language query."""
    query: NLQuery
    data: Any
    formatted: str
    confidence: float
    execution_time_ms: float


class NLQParser:
    """Parse natural language into structured query."""

    KEYWORDS = {
        "show": ["show", "list", "display", "get", "find", "what are", "what is"],
        "count": ["how many", "count", "total", "number of"],
        "sum": ["sum", "total", "add up"],
        "avg": ["average", "mean", "avg"],
        "max": ["maximum", "max", "highest", "most"],
        "min": ["minimum", "min", "lowest", "least"],
        "filter": ["where", "with", "having", "that", "only"],
        "time": ["today", "yesterday", "last week", "last month", "this week", "this month", "recently"],
        "sort": ["sort by", "order by", "sorted by", "arranged by"],
        "limit": ["top", "first", "last"],
    }

    TARGETS = {
        "modules": ["module", "modules", "component", "components"],
        "logs": ["log", "logs", "event", "events", "audit", "history"],
        "users": ["user", "users", "account", "accounts"],
        "metrics": ["metric", "metrics", "stat", "stats", "performance"],
        "errors": ["error", "errors", "failure", "failures", "bug", "bugs"],
        "documents": ["document", "documents", "file", "files", "doc"],
    }

    def parse(self, text: str) -> NLQuery:
        text_lower = text.lower()

        # Determine intent
        intent = "query"
        for intent_name, keywords in self.KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    intent = intent_name
                    break
            if intent != "query":
                break

        # Determine target
        target = "modules"
        for target_name, keywords in self.TARGETS.items():
            for kw in keywords:
                if kw in text_lower:
                    target = target_name
                    break
            if target != "modules":
                break

        # Extract filters
        filters = self._extract_filters(text_lower)

        # Extract aggregations
        aggregations = self._extract_aggregations(text_lower)

        # Extract time range
        time_range = self._extract_time_range(text_lower)

        # Extract sort
        sort_by = self._extract_sort(text_lower)

        # Extract limit
        limit = self._extract_limit(text_lower)

        return NLQuery(
            original=text,
            intent=intent,
            target=target,
            filters=filters,
            aggregations=aggregations,
            time_range=time_range,
            sort_by=sort_by,
            limit=limit,
        )

    def _extract_filters(self, text: str) -> Dict[str, Any]:
        filters = {}
        # State filter
        if "active" in text or "running" in text:
            filters["state"] = "active"
        if "error" in text or "failed" in text:
            filters["state"] = "error"
        if "disabled" in text or "offline" in text:
            filters["state"] = "disabled"
        # Name filter
        match = re.search(r"named?\s+['\"]?(\w+)['\"]?", text)
        if match:
            filters["name"] = match.group(1)
        return filters

    def _extract_aggregations(self, text: str) -> List[str]:
        aggs = []
        if any(w in text for w in ["count", "how many", "number"]):
            aggs.append("count")
        if any(w in text for w in ["average", "mean", "avg"]):
            aggs.append("avg")
        if any(w in text for w in ["sum", "total"]):
            aggs.append("sum")
        if any(w in text for w in ["max", "maximum", "highest"]):
            aggs.append("max")
        if any(w in text for w in ["min", "minimum", "lowest"]):
            aggs.append("min")
        return aggs

    def _extract_time_range(self, text: str) -> Optional[Tuple[float, float]]:
        now = time.time()
        if "today" in text:
            return (now - 86400, now)
        if "yesterday" in text:
            return (now - 172800, now - 86400)
        if "last week" in text:
            return (now - 604800, now)
        if "last month" in text:
            return (now - 2592000, now)
        if "recently" in text:
            return (now - 86400, now)
        return None

    def _extract_sort(self, text: str) -> Optional[str]:
        match = re.search(r"(?:sort|order)ed?\s+by\s+(\w+)", text)
        if match:
            return match.group(1)
        return None

    def _extract_limit(self, text: str) -> int:
        match = re.search(r"(?:top|first|last)\s+(\d+)", text)
        if match:
            return int(match.group(1))
        match = re.search(r"(\d+)\s+(?:most|least|top|recent)", text)
        if match:
            return int(match.group(1))
        return 10


class QueryExecutor:
    """Execute parsed NL query against MAGNATRIX-OS data."""

    def __init__(self, registry: Any) -> None:
        self.registry = registry

    def execute(self, query: NLQuery) -> Any:
        """Execute query and return raw data."""
        if query.target == "modules":
            return self._query_modules(query)
        elif query.target == "logs":
            return self._query_logs(query)
        elif query.target == "errors":
            return self._query_errors(query)
        elif query.target == "metrics":
            return self._query_metrics(query)
        elif query.target == "documents":
            return self._query_documents(query)
        else:
            return {"error": f"Unknown target: {query.target}"}

    def _query_modules(self, query: NLQuery) -> Any:
        modules = self.registry.list_modules() if self.registry else []

        # Apply filters
        if "state" in query.filters:
            modules = [m for m in modules if m.get("state") == query.filters["state"]]
        if "name" in query.filters:
            modules = [m for m in modules if query.filters["name"] in m.get("name", "")]

        # Apply aggregations
        if "count" in query.aggregations:
            return {"count": len(modules)}

        # Apply sort
        if query.sort_by:
            modules = sorted(modules, key=lambda m: m.get(query.sort_by, 0), reverse=True)

        # Apply limit
        modules = modules[:query.limit]

        return modules

    def _query_logs(self, query: NLQuery) -> Any:
        return {"message": "Log query requires logging module", "filters": query.filters}

    def _query_errors(self, query: NLQuery) -> Any:
        modules = self.registry.list_modules() if self.registry else []
        errors = [m for m in modules if m.get("state") == "error"]
        return errors[:query.limit]

    def _query_metrics(self, query: NLQuery) -> Any:
        stats = self.registry.stats() if self.registry else {}
        return stats

    def _query_documents(self, query: NLQuery) -> Any:
        return {"message": "Document query requires doc_intel module", "filters": query.filters}


class ResultFormatter:
    """Format query results into natural language."""

    def format(self, query: NLQuery, data: Any) -> str:
        if isinstance(data, dict) and "error" in data:
            return f"Sorry, I couldn't find that: {data['error']}"

        if query.intent == "count":
            if isinstance(data, dict) and "count" in data:
                return f"There are {data['count']} {query.target}."
            return f"Found {len(data) if isinstance(data, list) else 'some'} {query.target}."

        if query.intent == "show":
            if isinstance(data, list):
                if not data:
                    return f"No {query.target} found matching your criteria."
                items = []
                for item in data[:query.limit]:
                    if isinstance(item, dict):
                        name = item.get("name", "Unknown")
                        state = item.get("state", "")
                        items.append(f"- {name} ({state})")
                    else:
                        items.append(f"- {item}")
                return f"Here are the {query.target}:\n" + "\n".join(items)
            return f"Result: {json.dumps(data, indent=2)[:500]}"

        if query.intent == "avg" and isinstance(data, dict):
            return f"The average is {data.get('avg', 'N/A')}."

        return f"Query result: {json.dumps(data, ensure_ascii=False, default=str)[:200]}"


class NLQEngine:
    """Main NLQ engine."""

    def __init__(self, registry: Any) -> None:
        self.parser = NLQParser()
        self.executor = QueryExecutor(registry)
        self.formatter = ResultFormatter()
        self._history: List[NLQResult] = []

    def query(self, text: str) -> NLQResult:
        t0 = time.time()
        parsed = self.parser.parse(text)
        data = self.executor.execute(parsed)
        formatted = self.formatter.format(parsed, data)
        elapsed = (time.time() - t0) * 1000

        result = NLQResult(
            query=parsed,
            data=data,
            formatted=formatted,
            confidence=0.8 if parsed.target != "modules" else 0.95,
            execution_time_ms=elapsed,
        )
        self._history.append(result)
        return result

    def get_history(self, limit: int = 10) -> List[NLQResult]:
        return self._history[-limit:]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_queries": len(self._history),
            "avg_time_ms": sum(r.execution_time_ms for r in self._history) / len(self._history) if self._history else 0,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Natural Language Query Engine Demo ===\n")

    class MockRegistry:
        def list_modules(self):
            return [
                {"name": "config", "state": "active", "load_ms": 1.2},
                {"name": "llm", "state": "active", "load_ms": 2.5},
                {"name": "rag", "state": "active", "load_ms": 3.0},
                {"name": "websocket", "state": "error", "load_ms": 0.0},
                {"name": "doc_intel", "state": "active", "load_ms": 4.1},
            ]
        def stats(self):
            return {"total_registered": 116, "loaded": 114, "failed": 2}

    engine = NLQEngine(MockRegistry())

    queries = [
        "show all active modules",
        "how many modules are there",
        "what modules failed",
        "top 3 modules by load time",
        "show modules with errors",
        "count total modules",
    ]

    for q in queries:
        print(f"Q: {q}")
        result = engine.query(q)
        print(f"A: {result.formatted}")
        print(f"   [target: {result.query.target}, intent: {result.query.intent}, time: {result.execution_time_ms:.1f}ms]")
        print()

    print(f"Engine stats: {engine.stats()}")


if __name__ == "__main__":
    _demo()
