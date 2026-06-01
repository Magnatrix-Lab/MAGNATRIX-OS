"""Intent Recognition & Query Planner — Decompose complex queries into sub-tasks.

Modul ini menyediakan:
- IntentClassifier: classify user intent (question, command, analysis, etc.)
- QueryDecomposer: break complex queries into sub-queries
- TaskPlanner: create execution plan with dependencies
- QueryRouter: route sub-queries to appropriate modules
- ExecutionPlanner: full pipeline from raw query to execution plan
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum, auto


class IntentType(Enum):
    QUESTION = auto()
    COMMAND = auto()
    ANALYSIS = auto()
    COMPARISON = auto()
    SUMMARIZATION = auto()
    CODE = auto()
    CREATIVE = auto()
    CONVERSATION = auto()
    UNKNOWN = auto()


class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class Intent:
    """Classified intent with confidence."""
    intent_type: IntentType
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""


@dataclass
class SubQuery:
    """Decomposed sub-query."""
    subquery_id: str
    description: str
    intent: IntentType
    target_module: str = ""
    dependencies: List[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_tokens: int = 0
    context_required: bool = True


@dataclass
class TaskNode:
    """Node in execution plan."""
    task_id: str
    subquery: SubQuery
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    execution_time: float = 0.0


@dataclass
class ExecutionPlan:
    """Full plan from query to execution."""
    plan_id: str
    original_query: str
    intent: Intent
    subqueries: List[SubQuery]
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    parallel_groups: List[List[str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "original_query": self.original_query[:200],
            "intent": self.intent.intent_type.name,
            "confidence": self.intent.confidence,
            "subqueries": len(self.subqueries),
            "parallel_groups": len(self.parallel_groups)
        }


class IntentClassifier:
    """Classify user intent with keyword and pattern matching."""

    KEYWORDS = {
        IntentType.QUESTION: ["what", "why", "how", "when", "where", "who", "is", "are", "does", "can"],
        IntentType.COMMAND: ["run", "execute", "do", "perform", "create", "build", "generate", "make"],
        IntentType.ANALYSIS: ["analyze", "evaluate", "assess", "examine", "review", "study", "compare"],
        IntentType.COMPARISON: ["compare", "versus", "vs", "difference", "better", "best", "worse"],
        IntentType.SUMMARIZATION: ["summarize", "summary", "tl;dr", "brief", "overview", "recap"],
        IntentType.CODE: ["code", "function", "script", "program", "debug", "implement", "write code"],
        IntentType.CREATIVE: ["story", "poem", "write", "creative", "imagine", "design", "draw"],
        IntentType.CONVERSATION: ["chat", "talk", "discuss", "hello", "hi", "hey"]
    }

    def classify(self, query: str) -> Intent:
        query_lower = query.lower()
        scores: Dict[IntentType, float] = {}
        for intent, keywords in self.KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            scores[intent] = score / max(len(keywords), 1)
        if scores:
            best = max(scores, key=scores.get)
            max_score = scores[best]
            if max_score == 0:
                return Intent(IntentType.UNKNOWN, 0.3, {}, query)
            confidence = min(0.95, max_score * 0.5 + 0.3)
            entities = self._extract_entities(query)
            return Intent(best, round(confidence, 3), entities, query)
        return Intent(IntentType.UNKNOWN, 0.3, {}, query)

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        entities = {}
        # Extract numbers
        numbers = re.findall(r"\d+", query)
        if numbers:
            entities["numbers"] = numbers
        # Extract quoted strings
        quotes = re.findall(r'"([^"]+)"', query)
        if quotes:
            entities["quoted"] = quotes
        # Extract code blocks
        code = re.findall(r"```([\s\S]*?)```", query)
        if code:
            entities["code_blocks"] = code
        return entities


class QueryDecomposer:
    """Break complex queries into sub-queries."""

    SPLIT_PATTERNS = [
        r"\band\b",
        r"\bthen\b",
        r"\bafter\b",
        r";\s+",
        r"\n",
        r"\.\s+(?=(?:compare|analyze|summarize|find|get|show|calculate|what|how))"
    ]

    def __init__(self, classifier: Optional[IntentClassifier] = None):
        self.classifier = classifier or IntentClassifier()

    def decompose(self, query: str) -> List[SubQuery]:
        parts = self._split(query)
        subqueries = []
        for i, part in enumerate(parts):
            intent = self.classifier.classify(part)
            sq = SubQuery(
                subquery_id=str(uuid.uuid4())[:8],
                description=part.strip(),
                intent=intent.intent_type,
                target_module=self._route_target(intent.intent_type),
                estimated_tokens=len(part.split())
            )
            subqueries.append(sq)
        # Add sequential dependencies
        for i in range(1, len(subqueries)):
            subqueries[i].dependencies.append(subqueries[i-1].subquery_id)
        return subqueries

    def _split(self, query: str) -> List[str]:
        parts = [query]
        for pattern in self.SPLIT_PATTERNS:
            new_parts = []
            for part in parts:
                splits = re.split(pattern, part, flags=re.IGNORECASE)
                new_parts.extend(s.strip() for s in splits if s.strip())
            parts = new_parts
        return parts

    def _route_target(self, intent: IntentType) -> str:
        routing = {
            IntentType.CODE: "code_engine",
            IntentType.ANALYSIS: "analysis_engine",
            IntentType.COMPARISON: "comparison_engine",
            IntentType.SUMMARIZATION: "summarizer",
            IntentType.QUESTION: "qa_engine",
            IntentType.CREATIVE: "creative_engine",
            IntentType.COMMAND: "command_executor"
        }
        return routing.get(intent, "general_llm")


class TaskPlanner:
    """Create execution plan with dependency resolution."""

    def create_plan(self, query: str, decomposer: Optional[QueryDecomposer] = None) -> ExecutionPlan:
        decomp = decomposer or QueryDecomposer()
        subqueries = decomp.decompose(query)
        # Build dependency graph
        deps: Dict[str, List[str]] = {}
        for sq in subqueries:
            deps[sq.subquery_id] = sq.dependencies
        # Compute parallel groups via topological levels
        groups = self._compute_parallel_groups(deps)
        # Classify overall intent from first subquery
        intent = decomp.classifier.classify(query)
        return ExecutionPlan(
            plan_id=str(uuid.uuid4())[:12],
            original_query=query,
            intent=intent,
            subqueries=subqueries,
            dependencies=deps,
            parallel_groups=groups
        )

    def _compute_parallel_groups(self, deps: Dict[str, List[str]]) -> List[List[str]]:
        """BFS to find nodes at each level."""
        levels: Dict[str, int] = {}
        queue = [nid for nid, d in deps.items() if not d]
        for nid in queue:
            levels[nid] = 0
        # Build reverse adjacency
        rev: Dict[str, List[str]] = {}
        for nid, dlist in deps.items():
            for dep in dlist:
                rev.setdefault(dep, []).append(nid)
        # BFS
        while queue:
            curr = queue.pop(0)
            for nxt in rev.get(curr, []):
                if nxt not in levels:
                    levels[nxt] = levels[curr] + 1
                    queue.append(nxt)
        # Group by level
        max_level = max(levels.values()) if levels else 0
        groups = []
        for i in range(max_level + 1):
            group = [nid for nid, lvl in levels.items() if lvl == i]
            if group:
                groups.append(group)
        return groups


class QueryRouter:
    """Route sub-queries to appropriate execution modules."""

    def __init__(self):
        self._handlers: Dict[str, Callable[[str], Any]] = {}
        self._routes: Dict[str, str] = {
            "code_engine": "code",
            "analysis_engine": "analysis",
            "comparison_engine": "comparison",
            "summarizer": "summary",
            "qa_engine": "qa",
            "creative_engine": "creative",
            "command_executor": "command"
        }

    def register(self, module_name: str, handler: Callable[[str], Any]) -> None:
        self._handlers[module_name] = handler

    def route(self, subquery: SubQuery) -> Tuple[str, Any]:
        handler = self._handlers.get(subquery.target_module)
        if handler:
            return subquery.target_module, handler(subquery.description)
        return "general", f"[SIMULATED] {subquery.target_module}: {subquery.description[:60]}"

    def execute_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        results = {}
        for group in plan.parallel_groups:
            for sqid in group:
                sq = next(s for s in plan.subqueries if s.subquery_id == sqid)
                module, result = self.route(sq)
                results[sqid] = {"module": module, "result": result}
        return results


class ExecutionPlanner:
    """Full pipeline: query -> intent -> decompose -> plan -> route."""

    def __init__(self):
        self.classifier = IntentClassifier()
        self.decomposer = QueryDecomposer(self.classifier)
        self.planner = TaskPlanner()
        self.router = QueryRouter()
        self._history: List[ExecutionPlan] = []

    def plan(self, query: str) -> ExecutionPlan:
        plan = self.planner.create_plan(query, self.decomposer)
        self._history.append(plan)
        return plan

    def execute(self, query: str) -> Dict[str, Any]:
        plan = self.plan(query)
        results = self.router.execute_plan(plan)
        return {
            "plan": plan.to_dict(),
            "results": results,
            "subqueries": len(plan.subqueries),
            "parallel_groups": len(plan.parallel_groups)
        }

    def get_history(self) -> List[ExecutionPlan]:
        return self._history

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([p.to_dict() for p in self._history], f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("INTENT RECOGNITION & QUERY PLANNER DEMO")
    print("=" * 70)

    # 1. Intent Classification
    print("\n[1] Intent Classification")
    ic = IntentClassifier()
    queries = [
        "What is the capital of France?",
        "Run a Python script to analyze the CSV file",
        "Compare GPT-4 and Claude 3.5 on coding tasks",
        "Summarize the article about quantum computing",
        "Write a function to sort a list of dictionaries",
        "Tell me a short story about space exploration",
        "Hello, how are you doing today?",
        "Analyze the market trends and then summarize the findings"
    ]
    for q in queries:
        intent = ic.classify(q)
        print(f"  [{intent.intent_type.name:15}] {intent.confidence:.2f} | {q[:50]}...")

    # 2. Query Decomposition
    print("\n[2] Query Decomposition")
    qd = QueryDecomposer(ic)
    complex_query = "Analyze the stock market data and compare Tesla vs NVIDIA, then summarize the findings"
    subqueries = qd.decompose(complex_query)
    print(f"  Original: {complex_query}")
    for sq in subqueries:
        print(f"    [{sq.subquery_id}] {sq.intent.name} -> {sq.target_module}")
        print(f"      Desc: {sq.description[:70]}")
        print(f"      Deps: {sq.dependencies}")

    # 3. Task Planner
    print("\n[3] Task Planner")
    tp = TaskPlanner()
    plan = tp.create_plan("Compare Python vs JavaScript performance, then write a benchmark script to test it", qd)
    print(f"  Plan ID: {plan.plan_id}")
    print(f"  Intent: {plan.intent.intent_type.name} ({plan.intent.confidence})")
    print(f"  Subqueries: {len(plan.subqueries)}")
    print(f"  Parallel groups: {len(plan.parallel_groups)}")
    for i, group in enumerate(plan.parallel_groups):
        print(f"    Group {i}: {group}")

    # 4. Query Router
    print("\n[4] Query Router")
    qr = QueryRouter()
    qr.register("code_engine", lambda q: f"[CODE] {q[:40]}...")
    qr.register("comparison_engine", lambda q: f"[COMPARISON] {q[:40]}...")
    qr.register("summarizer", lambda q: f"[SUMMARY] {q[:40]}...")
    results = qr.execute_plan(plan)
    for sqid, res in results.items():
        print(f"  {sqid} -> {res['module']}: {res['result']}")

    # 5. Full Execution Planner
    print("\n[5] Full Execution Planner")
    ep = ExecutionPlanner()
    ep.router.register("code_engine", lambda q: f"[CODE_EXEC] {q[:40]}")
    ep.router.register("comparison_engine", lambda q: f"[COMPARE_EXEC] {q[:40]}")
    result = ep.execute("Compare Python vs Go for backend development, then generate a sample API in Go")
    print(f"  Plan: {result['plan']}")
    print(f"  Results: {len(result['results'])}")
    for sqid, res in result['results'].items():
        print(f"    {sqid}: {res['result']}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
