#!/usr/bin/env python3
"""
MAGNATRIX-OS — Tool Discovery & Auto-Selection Engine
ai/llm_tool_discovery_native.py

Features:
- Tool registry (register tools with descriptions, parameters, capabilities)
- Intent-to-tool matching (match user intent to available tools)
- Capability scoring (score tools by relevance to task)
- Auto-selection (pick best tool or tool chain for task)
- Tool chain composition (combine multiple tools in sequence)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("tool_discovery")


class ToolType(enum.Enum):
    API = "api"
    FUNCTION = "function"
    SEARCH = "search"
    CALCULATION = "calculation"
    FILE = "file"
    DATABASE = "database"


@dataclass
class ToolParameter:
    name: str
    type: str
    required: bool
    description: str
    default: Any = None


@dataclass
class ToolCapability:
    name: str
    description: str
    keywords: List[str]


@dataclass
class Tool:
    id: str
    name: str
    description: str
    tool_type: ToolType
    parameters: List[ToolParameter]
    capabilities: List[ToolCapability]
    handler: Optional[Callable] = None
    score: float = 0.0


@dataclass
class ToolMatch:
    tool: Tool
    score: float
    reason: str
    parameter_bindings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolChain:
    tools: List[ToolMatch]
    total_score: float
    estimated_steps: int


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.id] = tool
        logger.info(f"Registered tool: {tool.name} ({tool.id})")

    def unregister(self, tool_id: str) -> bool:
        if tool_id in self._tools:
            del self._tools[tool_id]
            return True
        return False

    def get(self, tool_id: str) -> Optional[Tool]:
        return self._tools.get(tool_id)

    def list_all(self) -> List[Tool]:
        return list(self._tools.values())

    def find_by_type(self, tool_type: ToolType) -> List[Tool]:
        return [t for t in self._tools.values() if t.tool_type == tool_type]

    def find_by_keyword(self, keyword: str) -> List[Tool]:
        results = []
        kw_lower = keyword.lower()
        for tool in self._tools.values():
            if kw_lower in tool.name.lower() or kw_lower in tool.description.lower():
                results.append(tool)
                continue
            for cap in tool.capabilities:
                if kw_lower in cap.name.lower() or any(kw_lower in k.lower() for k in cap.keywords):
                    results.append(tool)
                    break
        return results


class IntentMatcher:
    """Match user intent to tools."""

    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    def match(self, intent: str, context: Optional[Dict[str, Any]] = None) -> List[ToolMatch]:
        """Score all tools against the intent and return sorted matches."""
        matches = []
        intent_lower = intent.lower()
        intent_words = set(re.findall(r'\\w+', intent_lower))

        for tool in self._registry.list_all():
            score, reason = self._score_tool(tool, intent_words, intent_lower, context)
            if score > 0.0:
                bindings = self._extract_parameters(tool, intent_lower)
                matches.append(ToolMatch(tool=tool, score=score, reason=reason, parameter_bindings=bindings))

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

    def _score_tool(self, tool: Tool, intent_words: set, intent_text: str, context: Optional[Dict]) -> Tuple[float, str]:
        score = 0.0
        reasons = []

        # Name match
        tool_name_words = set(re.findall(r'\\w+', tool.name.lower()))
        name_overlap = len(intent_words & tool_name_words)
        score += name_overlap * 0.3
        if name_overlap > 0:
            reasons.append(f"name overlap ({name_overlap})")

        # Description match
        desc_words = set(re.findall(r'\\w+', tool.description.lower()))
        desc_overlap = len(intent_words & desc_words)
        score += desc_overlap * 0.2
        if desc_overlap > 0:
            reasons.append(f"description overlap ({desc_overlap})")

        # Capability keywords match
        for cap in tool.capabilities:
            cap_matches = sum(1 for kw in cap.keywords if kw.lower() in intent_text)
            score += cap_matches * 0.25
            if cap_matches > 0:
                reasons.append(f"capability '{cap.name}' ({cap_matches})")

        # Type-based boost
        if context and "preferred_type" in context:
            if tool.tool_type.value == context["preferred_type"]:
                score += 0.5
                reasons.append("preferred type match")

        return min(score, 1.0), "; ".join(reasons) if reasons else "no match"

    def _extract_parameters(self, tool: Tool, intent_text: str) -> Dict[str, Any]:
        bindings = {}
        for param in tool.parameters:
            # Simple extraction: look for "param=value" or "param is value"
            patterns = [
                rf'{param.name}[\s=:]+([^\s,;]+)',
                rf'{param.name}\s+is\s+([^\s,;]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, intent_text, re.IGNORECASE)
                if match:
                    bindings[param.name] = match.group(1).strip()
                    break
        return bindings


class ToolChainComposer:
    """Compose chains of tools for complex tasks."""

    def compose(self, matches: List[ToolMatch], max_tools: int = 3) -> ToolChain:
        """Create a tool chain from top matches."""
        selected = matches[:max_tools]
        total_score = sum(m.score for m in selected) / max(len(selected), 1)
        return ToolChain(tools=selected, total_score=total_score, estimated_steps=len(selected))

    def validate_chain(self, chain: ToolChain) -> List[str]:
        """Validate that a tool chain is executable."""
        issues = []
        for i, match in enumerate(chain.tools):
            missing = [p.name for p in match.tool.parameters if p.required and p.name not in match.parameter_bindings]
            if missing:
                issues.append(f"Step {i+1} ({match.tool.name}): missing required parameters: {missing}")
        return issues


class ToolDiscoveryEngine:
    """Unified tool discovery and selection engine."""

    def __init__(self):
        self.registry = ToolRegistry()
        self.matcher = IntentMatcher(self.registry)
        self.composer = ToolChainComposer()

    def discover(self, intent: str, context: Optional[Dict[str, Any]] = None,
                 require_chain: bool = False, max_tools: int = 3) -> Dict[str, Any]:
        """Discover and select tools for an intent."""
        matches = self.matcher.match(intent, context)

        result = {
            "intent": intent,
            "matches_found": len(matches),
            "top_matches": [],
            "chain": None,
            "chain_valid": True,
            "chain_issues": [],
        }

        for match in matches[:5]:
            result["top_matches"].append({
                "tool_id": match.tool.id,
                "tool_name": match.tool.name,
                "score": match.score,
                "reason": match.reason,
                "bindings": match.parameter_bindings,
            })

        if matches and require_chain:
            chain = self.composer.compose(matches, max_tools)
            issues = self.composer.validate_chain(chain)
            result["chain"] = {
                "tools": [m.tool.name for m in chain.tools],
                "total_score": chain.total_score,
                "estimated_steps": chain.estimated_steps,
            }
            result["chain_valid"] = len(issues) == 0
            result["chain_issues"] = issues

        return result

    def auto_select(self, intent: str, context: Optional[Dict[str, Any]] = None) -> Optional[ToolMatch]:
        """Auto-select the best single tool."""
        matches = self.matcher.match(intent, context)
        return matches[0] if matches else None


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Tool Discovery & Auto-Selection Engine")
    print("ai/llm_tool_discovery_native.py")
    print("=" * 60)

    engine = ToolDiscoveryEngine()

    # Register tools
    tools = [
        Tool(
            id="web_search", name="Web Search", description="Search the web for information",
            tool_type=ToolType.SEARCH,
            parameters=[ToolParameter("query", "string", True, "Search query")],
            capabilities=[ToolCapability("information_retrieval", "Find info online", ["search", "web", "google", "find"])],
        ),
        Tool(
            id="calculator", name="Calculator", description="Perform mathematical calculations",
            tool_type=ToolType.CALCULATION,
            parameters=[ToolParameter("expression", "string", True, "Math expression")],
            capabilities=[ToolCapability("math", "Do math", ["calculate", "math", "sum", "multiply", "divide"])],
        ),
        Tool(
            id="file_reader", name="File Reader", description="Read contents of a file",
            tool_type=ToolType.FILE,
            parameters=[ToolParameter("path", "string", True, "File path")],
            capabilities=[ToolCapability("file_access", "Read files", ["file", "read", "open", "document"])],
        ),
        Tool(
            id="weather_api", name="Weather API", description="Get weather information for a location",
            tool_type=ToolType.API,
            parameters=[ToolParameter("location", "string", True, "City name")],
            capabilities=[ToolCapability("weather", "Weather data", ["weather", "temperature", "rain", "forecast"])],
        ),
        Tool(
            id="db_query", name="Database Query", description="Query a database",
            tool_type=ToolType.DATABASE,
            parameters=[ToolParameter("sql", "string", True, "SQL query")],
            capabilities=[ToolCapability("data_query", "Query data", ["database", "sql", "query", "select"])],
        ),
    ]

    for t in tools:
        engine.registry.register(t)

    # 1. Simple intent matching
    print("")
    print("[1] Intent Matching - Web Search")
    result = engine.discover("Search for Python tutorials on web")
    print(f"  Intent: {result['intent']}")
    for m in result["top_matches"][:3]:
        print(f"  {m['tool_name']}: score={m['score']:.2f} ({m['reason']})")

    # 2. Math intent
    print("")
    print("[2] Intent Matching - Calculator")
    result = engine.discover("calculate 15 times 27 plus 100")
    for m in result["top_matches"][:3]:
        print(f"  {m['tool_name']}: score={m['score']:.2f} ({m['reason']})")

    # 3. Auto-select
    print("")
    print("[3] Auto-Select Best Tool")
    match = engine.auto_select("What is the weather in Paris?")
    if match:
        print(f"  Selected: {match.tool.name} (score={match.score:.2f})")
        print(f"  Bindings: {match.parameter_bindings}")

    # 4. Tool chain composition
    print("")
    print("[4] Tool Chain Composition")
    result = engine.discover("Find weather in Paris and calculate temperature difference from yesterday", require_chain=True, max_tools=3)
    if result["chain"]:
        print(f"  Chain: {result['chain']['tools']}")
        print(f"  Total score: {result['chain']['total_score']:.2f}")
        print(f"  Valid: {result['chain_valid']}")
        if result["chain_issues"]:
            for issue in result["chain_issues"]:
                print(f"  Issue: {issue}")

    # 5. Parameter extraction
    print("")
    print("[5] Parameter Extraction")
    match = engine.auto_select("Read file path=/data/report.txt")
    if match:
        print(f"  Tool: {match.tool.name}")
        print(f"  Extracted bindings: {match.parameter_bindings}")

    print("")
    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
