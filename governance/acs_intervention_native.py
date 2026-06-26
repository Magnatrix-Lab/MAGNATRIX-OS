"""
ACS Intervention Points — MAGNATRIX-OS Governance Layer
8 lifecycle hooks untuk agent governance sesuai Microsoft AGT ACS.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable
from governance.acs_policy_engine_native import ACSPolicyEngine, Verdict, VerdictType


class InterventionPoint(Enum):
    AGENT_STARTUP = "agent_startup"
    INPUT = "input"
    PRE_MODEL_CALL = "pre_model_call"
    POST_MODEL_CALL = "post_model_call"
    PRE_TOOL_CALL = "pre_tool_call"
    POST_TOOL_CALL = "post_tool_call"
    OUTPUT = "output"
    AGENT_SHUTDOWN = "agent_shutdown"


@dataclass
class InterventionBinding:
    """Bind satu intervention point ke satu policy bundle."""
    point: InterventionPoint
    bundle_id: str
    policy_target: str = ""
    policy_target_kind: str = "snapshot"
    tool_name_from: str = ""


@dataclass
class InterventionSnapshot:
    """Complete JSON snapshot yang dikirim host ke policy engine."""
    point: InterventionPoint
    agent_id: str
    session_id: str
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    previous_verdicts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "point": self.point.value,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "metadata": self.metadata,
            "previous_verdicts": self.previous_verdicts,
        }


class ACSInterventionHandler:
    """
    Handler untuk 8 ACS intervention points.
    Host (agent) panggil handler dengan snapshot lengkap.
    Handler evaluasi policy dan return verdict.
    """

    def __init__(self, engine: ACSPolicyEngine) -> None:
        self.engine = engine
        self._bindings: Dict[InterventionPoint, List[InterventionBinding]] = {
            p: [] for p in InterventionPoint
        }
        self._hooks: Dict[InterventionPoint, List[Callable[[InterventionSnapshot, Verdict], None]]] = {
            p: [] for p in InterventionPoint
        }
        self._history: List[Dict[str, Any]] = []

    def bind(self, binding: InterventionBinding) -> None:
        """Bind intervention point ke policy bundle."""
        self._bindings[binding.point].append(binding)

    def unbind(self, point: InterventionPoint, bundle_id: str) -> None:
        self._bindings[point] = [b for b in self._bindings[point] if b.bundle_id != bundle_id]

    def add_hook(self, point: InterventionPoint, hook: Callable[[InterventionSnapshot, Verdict], None]) -> None:
        """Register post-intervention hook."""
        self._hooks[point].append(hook)

    def handle(self, snapshot: InterventionSnapshot) -> Verdict:
        """
        Main intervention handler. Evaluates snapshot against all bound policies.
        Returns composed verdict. Stateless.
        """
        point = snapshot.point
        bindings = self._bindings.get(point, [])

        if not bindings:
            return Verdict(verdict_type=VerdictType.ALLOW, reason=f"No policy bound for {point.value}")

        verdicts: List[Verdict] = []
        for binding in bindings:
            # Extract policy target from snapshot
            eval_payload = self._extract_target(snapshot, binding)
            verdict = self.engine.evaluate(binding.bundle_id, eval_payload)
            verdicts.append(verdict)

        # Compose: all must allow
        final = self._compose_verdicts(verdicts)

        # Record
        self._history.append({
            "timestamp": time.time(),
            "point": point.value,
            "agent_id": snapshot.agent_id,
            "session_id": snapshot.session_id,
            "verdict": final.to_dict(),
            "individual_verdicts": [v.to_dict() for v in verdicts],
        })

        # Execute hooks
        for hook in self._hooks.get(point, []):
            try:
                hook(snapshot, final)
            except Exception:
                pass

        return final

    def _extract_target(self, snapshot: InterventionSnapshot, binding: InterventionBinding) -> Dict[str, Any]:
        """Extract policy target dari snapshot sesuai binding."""
        payload = snapshot.payload
        if binding.policy_target and binding.policy_target.startswith("$."):
            path = binding.policy_target.replace("$.", "").split(".")
            current = payload
            for part in path:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    current = {}
            return {"_extracted": current, "_full_snapshot": payload}
        return payload

    def _compose_verdicts(self, verdicts: List[Verdict]) -> Verdict:
        if not verdicts:
            return Verdict(verdict_type=VerdictType.ALLOW, reason="No policies to evaluate")
        # All must allow
        if all(v.is_allowed() for v in verdicts):
            return Verdict(verdict_type=VerdictType.ALLOW, reason="All policies allowed", evidence={"count": len(verdicts)})
        # Return first non-allow
        for v in verdicts:
            if not v.is_allowed():
                return v
        return verdicts[0]

    def get_history(self, point: Optional[InterventionPoint] = None) -> List[Dict[str, Any]]:
        if point:
            return [h for h in self._history if h["point"] == point.value]
        return list(self._history)

    def stats(self) -> Dict[str, Any]:
        return {
            "intervention_points": len(InterventionPoint),
            "bindings": sum(len(b) for b in self._bindings.values()),
            "history_entries": len(self._history),
            "points": {p.value: len(self._bindings[p]) for p in InterventionPoint},
        }


class AgentLifecycleGovernor:
    """High-level wrapper untuk intercept seluruh agent lifecycle."""

    def __init__(self, handler: ACSInterventionHandler) -> None:
        self.handler = handler

    def on_startup(self, agent_id: str, session_id: str, metadata: Dict[str, Any]) -> Verdict:
        snap = InterventionSnapshot(
            point=InterventionPoint.AGENT_STARTUP,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"metadata": metadata},
        )
        return self.handler.handle(snap)

    def on_input(self, agent_id: str, session_id: str, user_input: Dict[str, Any]) -> Verdict:
        snap = InterventionSnapshot(
            point=InterventionPoint.INPUT,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"input": user_input},
        )
        return self.handler.handle(snap)

    def on_pre_model(self, agent_id: str, session_id: str, messages: List[Dict], tools: List[Dict]) -> Verdict:
        snap = InterventionSnapshot(
            point=InterventionPoint.PRE_MODEL_CALL,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"messages": messages, "tools": tools},
        )
        return self.handler.handle(snap)

    def on_post_model(self, agent_id: str, session_id: str, response: Dict[str, Any]) -> Verdict:
        snap = InterventionSnapshot(
            point=InterventionPoint.POST_MODEL_CALL,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"response": response},
        )
        return self.handler.handle(snap)

    def on_pre_tool(self, agent_id: str, session_id: str, tool_call: Dict[str, Any]) -> Verdict:
        snap = InterventionSnapshot(
            point=InterventionPoint.PRE_TOOL_CALL,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"tool_call": tool_call},
        )
        return self.handler.handle(snap)

    def on_post_tool(self, agent_id: str, session_id: str, tool_result: Dict[str, Any]) -> Verdict:
        snap = InterventionSnapshot(
            point=InterventionPoint.POST_TOOL_CALL,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"tool_result": tool_result},
        )
        return self.handler.handle(snap)

    def on_output(self, agent_id: str, session_id: str, output: Dict[str, Any]) -> Verdict:
        snap = InterventionSnapshot(
            point=InterventionPoint.OUTPUT,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"output": output},
        )
        return self.handler.handle(snap)

    def on_shutdown(self, agent_id: str, session_id: str, summary: Dict[str, Any]) -> Verdict:
        snap = InterventionSnapshot(
            point=InterventionPoint.AGENT_SHUTDOWN,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"summary": summary},
        )
        return self.handler.handle(snap)


def run():
    print("=" * 60)
    print("ACS Intervention Points — Demo")
    print("=" * 60)

    from acs_policy_engine_native import PolicyBundle, PolicyRule

    engine = ACSPolicyEngine()
    # Load a simple tool policy
    tool_bundle = PolicyBundle(
        bundle_id="tool_guard",
        name="Tool Guard",
        rules=[
            PolicyRule(
                rule_id="block_file_delete",
                name="Block file deletion",
                conditions=[{"field": "$.tool_call.name", "operator": "eq", "value": "delete_file"}],
                action=VerdictType.DENY,
                priority=100,
            ),
            PolicyRule(
                rule_id="allow_safe_tools",
                name="Allow safe tools",
                conditions=[{"field": "$.tool_call.name", "operator": "in", "value": ["read_file", "calculate", "search"]}],
                action=VerdictType.ALLOW,
                priority=10,
            ),
        ],
    )
    engine.load_bundle(tool_bundle)

    handler = ACSInterventionHandler(engine)
    handler.bind(InterventionBinding(InterventionPoint.PRE_TOOL_CALL, "tool_guard", "$.tool_call"))

    governor = AgentLifecycleGovernor(handler)

    # Simulate lifecycle
    print("\n[1] Agent startup")
    v = governor.on_startup("agent_1", "sess_123", {"version": "1.0"})
    print(f"   Verdict: {v.verdict_type.value}")

    print("\n[2] Pre-tool call: delete_file")
    v = governor.on_pre_tool("agent_1", "sess_123", {"name": "delete_file", "args": {"path": "/etc/passwd"}})
    print(f"   Verdict: {v.verdict_type.value} — {v.reason}")

    print("\n[3] Pre-tool call: read_file")
    v = governor.on_pre_tool("agent_1", "sess_123", {"name": "read_file", "args": {"path": "./data.txt"}})
    print(f"   Verdict: {v.verdict_type.value}")

    print(f"\n[STATS] {handler.stats()}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
