"""
agentic_workflow_native.py — Native Agentic Workflow Orchestrator
Pure Python stdlib. LangGraph-style state machine, conditional edges,
multi-step reasoning, error recovery. NativeAgenticWorkflow with run().
"""
from __future__ import annotations

import copy
import json
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class NativeAgenticWorkflow:
    """
    Native agentic workflow orchestrator.

    Simulates a LangGraph-style state machine with nodes, conditional edges,
    state persistence, and error recovery. Pure stdlib.

    Attributes:
        nodes: name -> callable that receives and returns state.
        edges: name -> list of next node names (or conditional callable).
        state: Current workflow state dict.
        history: Execution trace.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.edges: Dict[str, List[str] | Callable[[Dict[str, Any]], List[str]]] = {}
        self.state: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self._max_steps = 50

    def add_node(
        self,
        name: str,
        func: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        """Register a node function."""
        self.nodes[name] = func

    def add_edge(
        self,
        from_node: str,
        to_nodes: List[str] | Callable[[Dict[str, Any]], List[str]],
    ) -> None:
        """
        Add edges from a node to next nodes.

        to_nodes can be a static list or a callable returning a list
        based on current state (conditional edges).
        """
        self.edges[from_node] = to_nodes

    def add_conditional_edge(
        self,
        from_node: str,
        condition: Callable[[Dict[str, Any]], str],
        mapping: Dict[str, str],
    ) -> None:
        """
        Add a conditional edge: condition(state) -> key, then key -> node.

        Args:
            from_node: Source node name.
            condition: Function returning a key string.
            mapping: Dict of key -> next node name.
        """
        def router(state: Dict[str, Any]) -> List[str]:
            key = condition(state)
            target = mapping.get(key)
            return [target] if target else []
        self.edges[from_node] = router

    def set_entry(self, node_name: str) -> None:
        """Set the entry node."""
        self._entry = node_name

    def run(
        self,
        initial_state: Optional[Dict[str, Any]] = None,
        entry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the workflow from entry node.

        Args:
            initial_state: Starting state dict.
            entry: Override entry node name.

        Returns:
            Final state dict with `_history` and `_metadata`.
        """
        self.state = copy.deepcopy(initial_state) if initial_state else {}
        self.history = []
        start = entry or getattr(self, "_entry", None)
        if not start or start not in self.nodes:
            raise ValueError(f"Entry node not set or missing: {start}")

        current = start
        visited: Set[str] = set()
        step = 0

        while current and step < self._max_steps:
            step += 1
            if current in visited:
                # Cycle detected — break and mark terminated
                self.history.append({
                    "step": step,
                    "node": current,
                    "error": "cycle detected",
                    "state": copy.deepcopy(self.state),
                })
                terminated = True
                break
            visited.add(current)

            node_fn = self.nodes.get(current)
            if not node_fn:
                self.history.append({
                    "step": step,
                    "node": current,
                    "error": f"node {current} not found",
                    "state": copy.deepcopy(self.state),
                })
                break

            try:
                before = copy.deepcopy(self.state)
                self.state = node_fn(copy.deepcopy(self.state))
                self.history.append({
                    "step": step,
                    "node": current,
                    "before": before,
                    "after": copy.deepcopy(self.state),
                })
            except Exception as e:
                # Error recovery: record and try to continue to fallback if set
                self.state["_error"] = str(e)
                self.state["_error_node"] = current
                self.history.append({
                    "step": step,
                    "node": current,
                    "error": str(e),
                    "state": copy.deepcopy(self.state),
                })
                # If there's an error handler edge, use it
                if f"{current}_error" in self.nodes:
                    current = f"{current}_error"
                    continue
                break

            # Determine next nodes
            edge_def = self.edges.get(current)
            if edge_def is None:
                break
            if callable(edge_def):
                next_nodes = edge_def(self.state)
            else:
                next_nodes = edge_def

            if not next_nodes:
                break
            # For deterministic branching, pick the first
            current = next_nodes[0]

        self.state["_history"] = self.history
        self.state["_metadata"] = {
            "steps": step,
            "terminated": locals().get("terminated", False) or current is None or step >= self._max_steps,
            "timestamp": time.time(),
        }
        return self.state

    def reset(self) -> None:
        """Reset state and history."""
        self.state = {}
        self.history = []

    def trace(self) -> List[Dict[str, Any]]:
        """Return execution trace."""
        return self.history

    def self_test(self) -> Dict[str, Any]:
        """
        Self-test demo.

        Returns:
            Dict with test results and a sample workflow trace.
        """
        results: Dict[str, Any] = {"status": "ok", "tests": []}

        # Test 1: Linear workflow
        wf = NativeAgenticWorkflow()
        def start_node(state: Dict[str, Any]) -> Dict[str, Any]:
            state["stage"] = "started"
            state["count"] = 0
            return state
        def middle_node(state: Dict[str, Any]) -> Dict[str, Any]:
            state["stage"] = "processing"
            state["count"] = state.get("count", 0) + 1
            return state
        def end_node(state: Dict[str, Any]) -> Dict[str, Any]:
            state["stage"] = "finished"
            return state
        wf.add_node("start", start_node)
        wf.add_node("middle", middle_node)
        wf.add_node("end", end_node)
        wf.add_edge("start", ["middle"])
        wf.add_edge("middle", ["end"])
        wf.set_entry("start")
        final = wf.run({"input": "test"})
        assert final["stage"] == "finished", f"Expected finished, got {final['stage']}"
        assert final["count"] == 1, f"Expected count=1, got {final['count']}"
        results["tests"].append({"name": "linear_workflow", "pass": True})

        # Test 2: Conditional edges
        wf2 = NativeAgenticWorkflow()
        def route_decision(state: Dict[str, Any]) -> Dict[str, Any]:
            state["decision"] = state.get("input", "")
            return state
        def left_path(state: Dict[str, Any]) -> Dict[str, Any]:
            state["path"] = "left"
            return state
        def right_path(state: Dict[str, Any]) -> Dict[str, Any]:
            state["path"] = "right"
            return state
        wf2.add_node("decide", route_decision)
        wf2.add_node("left", left_path)
        wf2.add_node("right", right_path)
        wf2.add_conditional_edge(
            "decide",
            lambda s: "left" if "go_left" in s.get("input", "") else "right",
            {"left": "left", "right": "right"},
        )
        wf2.set_entry("decide")
        final_left = wf2.run({"input": "go_left"})
        assert final_left["path"] == "left", f"Expected left path, got {final_left['path']}"
        final_right = wf2.run({"input": "go_right"})
        assert final_right["path"] == "right", f"Expected right path, got {final_right['path']}"
        results["tests"].append({"name": "conditional_edges", "pass": True})

        # Test 3: Error recovery
        wf3 = NativeAgenticWorkflow()
        def fail_node(state: Dict[str, Any]) -> Dict[str, Any]:
            raise RuntimeError("intentional failure")
        def recover_node(state: Dict[str, Any]) -> Dict[str, Any]:
            state["recovered"] = True
            state["error_handled"] = state.get("_error", "")
            return state
        wf3.add_node("fail", fail_node)
        wf3.add_node("fail_error", recover_node)  # error handler
        wf3.add_edge("fail", ["end"])  # never reached
        wf3.set_entry("fail")
        final_err = wf3.run({})
        assert final_err.get("recovered") is True, "Error recovery failed"
        results["tests"].append({"name": "error_recovery", "pass": True})

        # Test 4: Cycle detection
        wf4 = NativeAgenticWorkflow()
        def loop_node(state: Dict[str, Any]) -> Dict[str, Any]:
            state["iter"] = state.get("iter", 0) + 1
            return state
        wf4.add_node("loop", loop_node)
        wf4.add_edge("loop", ["loop"])  # self-loop
        wf4.set_entry("loop")
        final_loop = wf4.run({})
        assert final_loop["_metadata"]["terminated"] is True, "Cycle should terminate"
        assert any(h.get("error") == "cycle detected" for h in final_loop["_history"]), "Cycle detection missing"
        results["tests"].append({"name": "cycle_detection", "pass": True})

        # Test 5: History trace
        trace = wf.trace()
        assert len(trace) > 0, "Trace should not be empty"
        results["tests"].append({"name": "trace", "pass": True})

        # Test 6: Reset
        wf.reset()
        assert wf.state == {} and wf.history == [], "Reset failed"
        results["tests"].append({"name": "reset", "pass": True})

        results["summary"] = f"{sum(1 for t in results['tests'] if t['pass'])}/{len(results['tests'])} tests passed"
        return results


if __name__ == "__main__":
    wf = NativeAgenticWorkflow()
    print(wf.self_test())
