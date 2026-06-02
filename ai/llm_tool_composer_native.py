"""Tool Composer — Dynamic tool chaining, dependency resolution, and execution.

Modul ini menyediakan:
- ToolRegistry untuk register tools dengan schemas
- ToolComposer untuk chain tools dengan dependency graph
- DependencyResolver untuk topological execution ordering
- ToolExecutor untuk async/sync execution dengan error handling
- ToolChainOptimizer untuk optimize chain execution
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ToolType(Enum):
    FUNCTION = auto()
    API = auto()
    QUERY = auto()
    TRANSFORM = auto()
    CONDITION = auto()


class ExecutionStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class Tool:
    """Single tool definition."""
    tool_id: str
    name: str
    tool_type: ToolType
    description: str
    inputs: Dict[str, str] = field(default_factory=dict)  # name -> type
    outputs: List[str] = field(default_factory=list)
    executor: Optional[Callable[..., Any]] = None
    depends_on: List[str] = field(default_factory=list)
    timeout: float = 30.0
    retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def execute(self, inputs: Dict[str, Any]) -> Tuple[bool, Any]:
        if not self.executor:
            return True, None
        try:
            result = self.executor(**inputs)
            return True, result
        except Exception as e:
            return False, str(e)


@dataclass
class ToolChain:
    """Ordered chain of tool executions."""
    chain_id: str
    name: str
    tools: List[str] = field(default_factory=list)  # tool_ids in order
    results: Dict[str, Any] = field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error: Optional[str] = None


class ToolRegistry:
    """Register and manage available tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._by_type: Dict[ToolType, List[str]] = {}
        self._by_name: Dict[str, str] = {}  # name -> tool_id

    def register(self, tool: Tool) -> None:
        self._tools[tool.tool_id] = tool
        self._by_type.setdefault(tool.tool_type, []).append(tool.tool_id)
        self._by_name[tool.name] = tool.tool_id

    def get(self, tool_id: str) -> Optional[Tool]:
        return self._tools.get(tool_id)

    def get_by_name(self, name: str) -> Optional[Tool]:
        tid = self._by_name.get(name)
        return self._tools.get(tid) if tid else None

    def list_all(self) -> List[Tool]:
        return list(self._tools.values())

    def find_by_type(self, tool_type: ToolType) -> List[Tool]:
        return [self._tools[tid] for tid in self._by_type.get(tool_type, []) if tid in self._tools]

    def get_capabilities(self) -> Set[str]:
        return set(self._by_name.keys())


class DependencyResolver:
    """Resolve tool execution order via topological sort."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def resolve(self, tool_ids: List[str]) -> Tuple[bool, List[str], str]:
        """Return (success, ordered_ids, error_message)."""
        # Build adjacency
        adj: Dict[str, List[str]] = {tid: [] for tid in tool_ids}
        indegree: Dict[str, int] = {tid: 0 for tid in tool_ids}

        for tid in tool_ids:
            tool = self.registry.get(tid)
            if not tool:
                return False, [], f"Unknown tool: {tid}"
            for dep in tool.depends_on:
                if dep in tool_ids:
                    adj[dep].append(tid)
                    indegree[tid] += 1

        # Kahn's algorithm
        queue = [tid for tid, d in indegree.items() if d == 0]
        order = []
        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for nxt in adj.get(curr, []):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        if len(order) != len(tool_ids):
            return False, [], "Circular dependency detected"
        return True, order, ""

    def get_execution_plan(self, tool_ids: List[str]) -> List[List[str]]:
        """Return parallel execution layers."""
        ok, order, _ = self.resolve(tool_ids)
        if not ok:
            return []
        # Group by dependency depth
        layers = []
        placed = set()
        for tid in order:
            tool = self.registry.get(tid)
            if not tool:
                continue
            deps_placed = all(d in placed for d in tool.depends_on if d in tool_ids)
            if not layers or not deps_placed:
                layers.append([tid])
            else:
                # Check if all deps are in previous layers
                last_layer = set(layers[-1])
                all_deps_in_prev = all(d in placed or d in last_layer for d in tool.depends_on if d in tool_ids)
                if all_deps_in_prev and not any(d in last_layer for d in tool.depends_on if d in tool_ids):
                    layers[-1].append(tid)
                else:
                    layers.append([tid])
            placed.add(tid)
        return layers


class ToolExecutor:
    """Execute tool chains with error handling."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute_chain(self, chain: ToolChain, inputs: Dict[str, Any]) -> ToolChain:
        chain.status = ExecutionStatus.RUNNING
        resolver = DependencyResolver(self.registry)
        ok, order, error = resolver.resolve(chain.tools)
        if not ok:
            chain.status = ExecutionStatus.FAILED
            chain.error = error
            return chain

        context = dict(inputs)
        for tid in order:
            tool = self.registry.get(tid)
            if not tool:
                chain.status = ExecutionStatus.FAILED
                chain.error = f"Tool not found: {tid}"
                return chain

            # Collect inputs from context
            tool_inputs = {k: context.get(k) for k in tool.inputs}
            success, result = tool.execute(tool_inputs)
            if not success:
                if tool.retries > 0:
                    for _ in range(tool.retries):
                        success, result = tool.execute(tool_inputs)
                        if success:
                            break
                if not success:
                    chain.status = ExecutionStatus.FAILED
                    chain.error = f"Tool {tool.name} failed: {result}"
                    return chain

            context[tid] = result
            for out in tool.outputs:
                context[out] = result
            chain.results[tid] = result

        chain.status = ExecutionStatus.SUCCESS
        chain.completed_at = time.time()
        return chain

    def execute_parallel(self, chain: ToolChain, inputs: Dict[str, Any]) -> ToolChain:
        resolver = DependencyResolver(self.registry)
        layers = resolver.get_execution_plan(chain.tools)
        context = dict(inputs)
        chain.status = ExecutionStatus.RUNNING

        for layer in layers:
            for tid in layer:
                tool = self.registry.get(tid)
                if not tool:
                    chain.status = ExecutionStatus.FAILED
                    chain.error = f"Tool not found: {tid}"
                    return chain
                tool_inputs = {k: context.get(k) for k in tool.inputs}
                success, result = tool.execute(tool_inputs)
                if not success:
                    chain.status = ExecutionStatus.FAILED
                    chain.error = f"Tool {tool.name} failed: {result}"
                    return chain
                context[tid] = result
                for out in tool.outputs:
                    context[out] = result
                chain.results[tid] = result

        chain.status = ExecutionStatus.SUCCESS
        chain.completed_at = time.time()
        return chain


class ToolComposer:
    """Compose and manage tool chains."""

    def __init__(self):
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self._chains: Dict[str, ToolChain] = {}
        self._history: List[ToolChain] = []

    def add_tool(self, tool: Tool) -> None:
        self.registry.register(tool)

    def compose(self, name: str, tool_ids: List[str]) -> Optional[ToolChain]:
        resolver = DependencyResolver(self.registry)
        ok, order, error = resolver.resolve(tool_ids)
        if not ok:
            print(f"Compose failed: {error}")
            return None
        chain = ToolChain(
            chain_id=str(uuid.uuid4())[:12],
            name=name,
            tools=order,
        )
        self._chains[chain.chain_id] = chain
        return chain

    def execute(self, chain_id: str, inputs: Dict[str, Any], parallel: bool = False) -> ToolChain:
        chain = self._chains.get(chain_id)
        if not chain:
            raise ValueError(f"Chain not found: {chain_id}")
        if parallel:
            result = self.executor.execute_parallel(chain, inputs)
        else:
            result = self.executor.execute_chain(chain, inputs)
        self._history.append(result)
        return result

    def get_chain(self, chain_id: str) -> Optional[ToolChain]:
        return self._chains.get(chain_id)

    def get_history(self) -> List[ToolChain]:
        return self._history

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._history)
        success = sum(1 for c in self._history if c.status == ExecutionStatus.SUCCESS)
        return {
            "total_chains": len(self._chains),
            "executions": total,
            "success_rate": success / max(total, 1),
            "tools": len(self.registry.list_all()),
        }

    def export_chain(self, chain_id: str, path: str) -> None:
        chain = self._chains.get(chain_id)
        if chain:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "chain_id": chain.chain_id,
                    "name": chain.name,
                    "tools": chain.tools,
                    "results": chain.results,
                    "status": chain.status.name,
                }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("TOOL COMPOSER DEMO")
    print("=" * 70)

    # 1. Register tools
    print("\n[1] Register Tools")
    composer = ToolComposer()
    composer.add_tool(Tool("t1", "fetch_data", ToolType.API, "Fetch data from source",
                           inputs={"url": "str"}, outputs=["data"],
                           executor=lambda url=None: {"records": 100, "source": url or "default"}))
    composer.add_tool(Tool("t2", "filter_data", ToolType.TRANSFORM, "Filter data by criteria",
                           inputs={"data": "dict"}, outputs=["filtered"],
                           executor=lambda data=None: {"records": data.get("records", 0) // 2, "filtered": True} if data else None))
    composer.add_tool(Tool("t3", "analyze", ToolType.FUNCTION, "Analyze data",
                           inputs={"filtered": "dict"}, outputs=["analysis"],
                           executor=lambda filtered=None: {"mean": 42, "insights": 3} if filtered else None))
    composer.add_tool(Tool("t4", "report", ToolType.FUNCTION, "Generate report",
                           inputs={"analysis": "dict"}, outputs=["report"],
                           executor=lambda analysis=None: f"Report: {analysis} insights generated" if analysis else "No data"))
    composer.add_tool(Tool("t5", "check", ToolType.CONDITION, "Validate data",
                           inputs={"data": "dict"}, outputs=["valid"],
                           executor=lambda data=None: data.get("records", 0) > 0 if data else False))

    # Set dependencies
    composer.registry.get("t2").depends_on = ["t1"]
    composer.registry.get("t3").depends_on = ["t2"]
    composer.registry.get("t4").depends_on = ["t3"]
    composer.registry.get("t5").depends_on = ["t1"]

    print(f"  Registered: {len(composer.registry.list_all())} tools")
    for t in composer.registry.list_all():
        print(f"    {t.name}: type={t.tool_type.name}, deps={t.depends_on}")

    # 2. Compose chain
    print("\n[2] Compose Chain")
    chain = composer.compose("ETL Pipeline", ["t1", "t2", "t3", "t4", "t5"])
    print(f"  Chain: {chain.chain_id}, tools={chain.tools}")

    # 3. Resolve dependencies
    print("\n[3] Dependency Resolution")
    resolver = DependencyResolver(composer.registry)
    layers = resolver.get_execution_plan(["t1", "t2", "t3", "t4", "t5"])
    print(f"  Parallel layers: {len(layers)}")
    for i, layer in enumerate(layers):
        print(f"    Layer {i}: {layer}")

    # 4. Execute chain
    print("\n[4] Execute Chain")
    result = composer.execute(chain.chain_id, {"url": "https://example.com/data"})
    print(f"  Status: {result.status.name}")
    print(f"  Results:")
    for tid, val in result.results.items():
        print(f"    {tid}: {val}")

    # 5. Execute parallel
    print("\n[5] Execute Parallel")
    chain2 = composer.compose("Parallel ETL", ["t1", "t2", "t3"])
    result2 = composer.execute(chain2.chain_id, {"url": "https://api.test"}, parallel=True)
    print(f"  Status: {result2.status.name}, Duration: {result2.completed_at - result2.created_at:.3f}s")

    # 6. Error handling
    print("\n[6] Error Handling")
    composer.add_tool(Tool("t_err", "flaky", ToolType.FUNCTION, "Flaky tool",
                           inputs={"x": "int"}, outputs=["y"],
                           executor=lambda x=None: (_ for _ in ()).throw(RuntimeError("Always fails"))))
    chain_err = composer.compose("Error Test", ["t_err"])
    result_err = composer.execute(chain_err.chain_id, {"x": 5})
    print(f"  Status: {result_err.status.name}")
    print(f"  Error: {result_err.error}")

    # 7. Stats
    print(f"\n[7] Stats")
    print(f"  {composer.get_stats()}")

    # 8. Export
    print("\n[8] Export Chain")
    composer.export_chain(chain.chain_id, "/tmp/chain.json")
    print("  Exported to /tmp/chain.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
