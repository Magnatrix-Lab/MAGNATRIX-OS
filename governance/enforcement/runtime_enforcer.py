"""
governance/enforcement/runtime_enforcer.py
=============================================
MAGNATRIX Constitutional Enforcement (Runtime)
Layer 11: Governance (extends governance/native_engines)

Runtime-injected constraints yang aktif monitor setiap agent action.
Policy enforcement hooks, capability guards, real-time constraint checks.
"""

import asyncio, json, time, uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import defaultdict

class EnforcementLevel(Enum):
    AUDIT = "audit"; WARN = "warn"; BLOCK = "block"; KILL = "kill"

@dataclass
class Constraint:
    id: str = ""
    name: str = ""
    condition: str = ""  # Python expression
    action: EnforcementLevel = EnforcementLevel.WARN
    scope: List[str] = field(default_factory=list)  # agent_ids or ["*"]
    metadata: Dict = field(default_factory=dict)

class RuntimeEnforcer:
    """
    Runtime policy enforcer.
    Wraps agent actions dengan constraint checks.
    """

    def __init__(self):
        self.constraints: Dict[str, Constraint] = {}
        self._hooks: Dict[str, List[Callable]] = defaultdict(list)
        self._violation_log: List[Dict] = []
        self._action_count: int = 0
        self._blocked_count: int = 0

    def register_constraint(self, constraint: Constraint) -> str:
        """Register runtime constraint"""
        constraint.id = constraint.id or str(uuid.uuid4())[:8]
        self.constraints[constraint.id] = constraint
        return constraint.id

    def add_hook(self, action_type: str, callback: Callable):
        """Add enforcement hook untuk action type"""
        self._hooks[action_type].append(callback)

    async def enforce(self, agent_id: str, action_type: str,
                      params: Dict, action_fn: Callable) -> Any:
        """
        Execute action dengan constraint enforcement.
        Wraps any agent action dengan pre/post checks.
        """
        self._action_count += 1
        context = {"agent_id": agent_id, "action": action_type, "params": params, "timestamp": time.time()}

        # Pre-execution checks
        for cid, constraint in self.constraints.items():
            if constraint.scope != ["*"] and agent_id not in constraint.scope:
                continue

            try:
                triggered = eval(constraint.condition, {"ctx": context, "params": params})
            except Exception:
                triggered = False

            if triggered:
                self._handle_violation(context, constraint)

                if constraint.action == EnforcementLevel.BLOCK:
                    self._blocked_count += 1
                    return {"error": "BLOCKED", "constraint": constraint.name, "reason": constraint.condition}

                elif constraint.action == EnforcementLevel.KILL:
                    self._blocked_count += 1
                    return {"error": "KILL", "constraint": constraint.name, "agent_terminated": True}

        # Execute hooks
        for hook in self._hooks.get(action_type, []):
            if asyncio.iscoroutinefunction(hook):
                await hook(context)
            else:
                hook(context)

        # Execute actual action
        if asyncio.iscoroutinefunction(action_fn):
            result = await action_fn(**params)
        else:
            result = action_fn(**params)

        return result

    def _handle_violation(self, context: Dict, constraint: Constraint):
        """Log dan handle constraint violation"""
        self._violation_log.append({
            "timestamp": time.time(),
            "agent_id": context["agent_id"],
            "action": context["action"],
            "constraint": constraint.name,
            "severity": constraint.action.value,
            "params": context["params"]
        })

    def get_violations(self, agent_id: str = None, limit: int = 100) -> List[Dict]:
        """Get violation history"""
        violations = self._violation_log
        if agent_id:
            violations = [v for v in violations if v["agent_id"] == agent_id]
        return violations[-limit:]

    def get_stats(self) -> Dict:
        return {
            "constraints_active": len(self.constraints),
            "actions_processed": self._action_count,
            "blocked_actions": self._blocked_count,
            "violations": len(self._violation_log),
            "violation_rate": self._blocked_count / max(self._action_count, 1)
        }


class ConstitutionalMonitor:
    """
    Continuous constitutional monitoring daemon.
    Background process yang audits all agent activities.
    """

    def __init__(self, enforcer: RuntimeEnforcer):
        self.enforcer = enforcer
        self._running = False
        self._audit_interval = 60.0
        self._audit_log: List[Dict] = []

    async def start(self):
        """Start monitoring daemon"""
        self._running = True
        while self._running:
            await self._audit_cycle()
            await asyncio.sleep(self._audit_interval)

    def stop(self):
        self._running = False

    async def _audit_cycle(self):
        """Single audit cycle"""
        stats = self.enforcer.get_stats()
        self._audit_log.append({
            "timestamp": time.time(),
            "stats": stats,
            "health": "healthy" if stats["violation_rate"] < 0.01 else "concerning"
        })

    def get_audit_history(self) -> List[Dict]:
        return self._audit_log


if __name__ == "__main__":
    async def demo():
        enforcer = RuntimeEnforcer()

        # Register constraints
        enforcer.register_constraint(Constraint(
            name="No Delete Database",
            condition="'delete' in params.get('table', '') or 'drop' in params.get('query', '').lower()",
            action=EnforcementLevel.BLOCK,
            scope=["*"]
        ))

        enforcer.register_constraint(Constraint(
            name="Limit API Calls",
            condition="params.get('count', 0) > 100",
            action=EnforcementLevel.WARN,
            scope=["*"]
        ))

        # Test enforcement
        result = await enforcer.enforce("agent-1", "query", {"query": "SELECT * FROM users"}, lambda query: {"status": "ok"})
        print(f"Safe action: {result}")

        result = await enforcer.enforce("agent-1", "delete", {"table": "delete_users"}, lambda table: {"status": "deleted"})
        print(f"Blocked action: {result}")

        print(f"Stats: {enforcer.get_stats()}")

    asyncio.run(demo())
