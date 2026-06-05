"""
Unified Orchestrator — MAGNATRIX-OS Core
Entry point yang menjalankan semua 11 modul ACS governance secara terintegrasi.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import sys, time, json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional
from pathlib import Path

# Import semua ACS governance modules
from governance.acs_policy_engine_native import ACSPolicyEngine, PolicyBundle, VerdictType
from governance.acs_intervention_native import ACSInterventionHandler, InterventionBinding, InterventionPoint
from governance.acs_verdict_native import VerdictComposer, TransformEngine, ApprovalQueue
from governance.acs_manifest_native import ManifestResolver
from governance.acs_audit_tamper_native import TamperEvidentAuditTrail
from governance.acs_approval_workflow_native import ApprovalManager
from governance.acs_identity_zero_trust_native import ZeroTrustIdentity
from governance.acs_sandbox_multiplatform_native import MultiPlatformSandbox, SandboxConfig
from governance.acs_capability_concealment_native import CapabilityConcealmentDetector
from governance.acs_instrumental_convergence_native import InstrumentalConvergenceSafety
from governance.acs_self_improvement_governance_native import SelfImprovementGovernance


class OrchestratorMode(Enum):
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    AUDIT = "audit"
    SAFE_MODE = "safe_mode"


@dataclass
class OrchestratorConfig:
    """Configuration untuk unified orchestrator."""
    mode: OrchestratorMode = OrchestratorMode.PRODUCTION
    policy_manifest_dir: str = "./policies"
    audit_log_file: str = ".governance/acs_audit.jsonl"
    identity_ttl: float = 86400.0
    sandbox_cpu_max: float = 50.0
    sandbox_memory_max: int = 512
    auto_approve_low_risk: bool = True
    circuit_breaker_threshold: float = 0.7
    concealment_monitoring: bool = True
    convergence_safety: bool = True
    self_improvement_governance: bool = True
    enable_all_intervention_points: bool = True


class UnifiedOrchestrator:
    """
    Unified Orchestrator untuk MAGNATRIX-OS.

    Integrasi 11 modul ACS governance:
    1. Policy Engine — evaluate policies
    2. Intervention Handler — 8 lifecycle hooks
    3. Verdict System — compose, transform, queue
    4. Manifest Resolver — policy discovery
    5. Tamper-Evident Audit — log integrity
    6. Approval Workflow — human-in-the-loop
    7. Zero-Trust Identity — mutual auth
    8. Multi-Platform Sandbox — isolation
    9. Concealment Detector — deception detection
    10. Convergence Safety — instrumental goal prevention
    11. Self-Improvement Governance — safe recursive improvement
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None) -> None:
        self.config = config or OrchestratorConfig()
        self._initialized = False

        # Initialize all governance modules
        self.policy_engine = ACSPolicyEngine()
        self.intervention_handler = ACSInterventionHandler(self.policy_engine)
        self.verdict_composer = VerdictComposer()
        self.transform_engine = TransformEngine()
        self.approval_queue = ApprovalQueue()
        self.manifest_resolver = ManifestResolver(self.config.policy_manifest_dir)
        self.audit_trail = TamperEvidentAuditTrail(self.config.audit_log_file)
        self.approval_manager = ApprovalManager()
        self.identity = ZeroTrustIdentity()
        self.sandbox = MultiPlatformSandbox()
        self.concealment_detector = CapabilityConcealmentDetector()
        self.convergence_safety = InstrumentalConvergenceSafety()
        self.self_improvement = SelfImprovementGovernance()

    def initialize(self) -> bool:
        """Initialize the orchestrator and all subsystems."""
        try:
            # Load policy manifests
            self.manifest_resolver.resolve()
            bindings = self.manifest_resolver.get_bindings(self.manifest_resolver.resolve())
            for b in bindings:
                point = getattr(InterventionPoint, b["point"].upper().replace(".", "_"), None)
                if point:
                    self.intervention_handler.bind(InterventionBinding(point, b["policy_id"], b["policy_target"]))

            # Initialize sandbox
            self.sandbox.create(SandboxConfig(
                max_cpu_percent=self.config.sandbox_cpu_max,
                max_memory_mb=self.config.sandbox_memory_max,
            ))

            self._initialized = True
            self.audit_trail.record(
                event_type="orchestrator_init",
                actor="system",
                verdict="allow",
                evidence={"mode": self.config.mode.value, "modules_loaded": 11},
            )
            return True
        except Exception as e:
            self.audit_trail.record(
                event_type="orchestrator_init_failed",
                actor="system",
                verdict="deny",
                evidence={"error": str(e)},
            )
            return False

    def run_agent_lifecycle(self, agent_id: str, session_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run complete agent lifecycle dengan governance pada setiap intervention point.
        """
        if not self._initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        results = {}

        # 1. Agent startup
        from governance.acs_intervention_native import InterventionSnapshot
        snap_startup = InterventionSnapshot(
            point=InterventionPoint.AGENT_STARTUP,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"task": task},
        )
        verdict = self.intervention_handler.handle(snap_startup)
        results["startup"] = verdict.to_dict()
        if verdict.is_denied():
            self._audit_and_block(agent_id, "startup", verdict)
            return results

        # 2. Input validation
        snap_input = InterventionSnapshot(
            point=InterventionPoint.INPUT,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"user_input": task.get("input", {})},
        )
        verdict = self.intervention_handler.handle(snap_input)
        results["input"] = verdict.to_dict()
        if verdict.is_denied():
            self._audit_and_block(agent_id, "input", verdict)
            return results

        # 3. Pre-model call
        snap_pre_model = InterventionSnapshot(
            point=InterventionPoint.PRE_MODEL_CALL,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"messages": task.get("messages", []), "tools": task.get("tools", [])},
        )
        verdict = self.intervention_handler.handle(snap_pre_model)
        results["pre_model"] = verdict.to_dict()
        if verdict.is_denied():
            self._audit_and_block(agent_id, "pre_model", verdict)
            return results

        # 4. Post-model call (simulate)
        snap_post_model = InterventionSnapshot(
            point=InterventionPoint.POST_MODEL_CALL,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"response": {"content": "model_output", "tool_calls": []}},
        )
        verdict = self.intervention_handler.handle(snap_post_model)
        results["post_model"] = verdict.to_dict()

        # 5. Pre-tool call (if any tools)
        for tool in task.get("tools", []):
            snap_pre_tool = InterventionSnapshot(
                point=InterventionPoint.PRE_TOOL_CALL,
                agent_id=agent_id, session_id=session_id, timestamp=time.time(),
                payload={"tool_call": tool},
            )
            verdict = self.intervention_handler.handle(snap_pre_tool)
            results[f"pre_tool_{tool.get('name', 'unknown')}"] = verdict.to_dict()
            if verdict.is_denied():
                self._audit_and_block(agent_id, f"pre_tool_{tool.get('name')}", verdict)
                return results

        # 6. Output validation
        snap_output = InterventionSnapshot(
            point=InterventionPoint.OUTPUT,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"output": {"result": "success"}},
        )
        verdict = self.intervention_handler.handle(snap_output)
        results["output"] = verdict.to_dict()
        if verdict.is_denied():
            self._audit_and_block(agent_id, "output", verdict)
            return results

        # 7. Agent shutdown
        snap_shutdown = InterventionSnapshot(
            point=InterventionPoint.AGENT_SHUTDOWN,
            agent_id=agent_id, session_id=session_id, timestamp=time.time(),
            payload={"summary": results},
        )
        verdict = self.intervention_handler.handle(snap_shutdown)
        results["shutdown"] = verdict.to_dict()

        # Audit trail
        self.audit_trail.record(
            event_type="agent_lifecycle",
            actor=agent_id,
            verdict="allow" if all(not v.get("verdict", "").startswith("deny") for v in results.values()) else "deny",
            evidence={"session_id": session_id, "results": results},
        )

        return results

    def _audit_and_block(self, agent_id: str, point: str, verdict) -> None:
        self.audit_trail.record(
            event_type="intervention_blocked",
            actor=agent_id,
            verdict="deny",
            evidence={"point": point, "reason": verdict.reason},
        )

    def check_agent_health(self, agent_id: str) -> Dict[str, Any]:
        """Health check semua subsystem untuk satu agent."""
        return {
            "agent_id": agent_id,
            "orchestrator_initialized": self._initialized,
            "policy_bundles": self.policy_engine.list_bundles(),
            "audit_integrity": self.audit_trail.verify_integrity(),
            "pending_approvals": len(self.approval_manager.get_pending()),
            "identity_credentials": self.identity.stats(),
            "sandbox_platform": self.sandbox.get_platform(),
            "concealment_monitoring": self.config.concealment_monitoring,
            "convergence_safety": self.config.convergence_safety,
            "self_improvement_governance": self.config.self_improvement_governance,
        }

    def get_full_stats(self) -> Dict[str, Any]:
        return {
            "orchestrator": {
                "initialized": self._initialized,
                "mode": self.config.mode.value,
            },
            "policy_engine": self.policy_engine.stats(),
            "intervention": self.intervention_handler.stats(),
            "audit": self.audit_trail.stats(),
            "approval": self.approval_manager.stats(),
            "identity": self.identity.stats(),
            "sandbox": self.sandbox.stats(),
            "concealment": self.concealment_detector.stats(),
            "convergence": self.convergence_safety.stats(),
            "self_improvement": self.self_improvement.stats(),
        }


def run():
    print("=" * 60)
    print("Unified Orchestrator — Demo")
    print("=" * 60)

    orch = UnifiedOrchestrator(OrchestratorConfig(mode=OrchestratorMode.DEVELOPMENT))

    print("\n[1] Initialize")
    ok = orch.initialize()
    print(f"   Initialized: {ok}")

    print("\n[2] Run agent lifecycle")
    task = {
        "input": {"query": "calculate risk"},
        "messages": [{"role": "user", "content": "Hello"}],
        "tools": [{"name": "read_file", "args": {"path": "./data.txt"}}],
    }
    results = orch.run_agent_lifecycle("agent_1", "sess_demo", task)
    print(f"   Lifecycle results: {list(results.keys())}")
    for k, v in results.items():
        print(f"   - {k}: {v.get('verdict', 'N/A')}")

    print("\n[3] Health check")
    health = orch.check_agent_health("agent_1")
    print(f"   Audit integrity: {health['audit_integrity']}")
    print(f"   Sandbox platform: {health['sandbox_platform']}")

    print("\n[4] Full stats")
    stats = orch.get_full_stats()
    print(f"   Stats keys: {list(stats.keys())}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
