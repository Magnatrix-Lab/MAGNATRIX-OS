#!/usr/bin/env python3
"""MAGNATRIX Constitution Enforcer — REAL"""

import yaml
import sys
from datetime import datetime

class ConstitutionEnforcer:
    def __init__(self, constitution_path="governance/constitution.yaml"):
        with open(constitution_path) as f:
            self.constitution = yaml.safe_load(f)
        self.audit_log = "governance/audit.log"
    
    def check_action(self, action: str, actor: str = "unknown") -> dict:
        """Check action against constitution."""
        result = {"action": action, "actor": actor, "timestamp": datetime.now().isoformat()}
        
        # Rule: no_self_replicate
        if "self_replicate" in action.lower() or "spawn" in action.lower():
            result["verdict"] = "BLOCKED"
            result["reason"] = "VIOLATES: no_self_replicate (requires human approval)"
            result["severity"] = "CRITICAL"
        
        # Rule: uncensored_local
        elif "cloud_model" in action.lower() and "uncensored" in action.lower():
            result["verdict"] = "BLOCKED"
            result["reason"] = "VIOLATES: uncensored_local (uncensored ops must be local)"
            result["severity"] = "CRITICAL"
        
        # Rule: no_deception
        elif "conceal" in action.lower() or "hide" in action.lower():
            result["verdict"] = "BLOCKED"
            result["reason"] = "VIOLATES: no_deception (capability concealment prohibited)"
            result["severity"] = "CRITICAL"
        
        # Rule: privacy_first
        elif "send_data" in action.lower() or "upload_telemetry" in action.lower():
            result["verdict"] = "BLOCKED"
            result["reason"] = "VIOLATES: privacy_first (no external data without consent)"
            result["severity"] = "HIGH"
        
        # Rule: resource_fairness (warn, not block)
        elif "allocate_profit" in action.lower():
            result["verdict"] = "APPROVED_WITH_WARNING"
            result["reason"] = "WARNING: resource_fairness (cap compute allocation at 30%)"
            result["severity"] = "WARNING"
        
        # Default: approved
        else:
            result["verdict"] = "APPROVED"
            result["reason"] = "No constitution violation detected"
            result["severity"] = "INFO"
        
        self._log(result)
        return result
    
    def _log(self, result: dict):
        with open(self.audit_log, "a") as f:
            f.write(f"[{result['timestamp']}] {result['actor']} → {result['action']} | {result['verdict']} | {result['reason']}\n")
    
    def get_audit(self, lines: int = 10) -> str:
        try:
            with open(self.audit_log) as f:
                return "".join(f.readlines()[-lines:])
        except FileNotFoundError:
            return "No audit entries yet."

if __name__ == "__main__":
    enforcer = ConstitutionEnforcer()
    
    # Test 3 actions
    tests = [
        ("self_replicate", "HERMES"),
        ("read_file", "KIMI_CLAW"),
        ("conceal_capability", "GQRIS"),
        ("modify_code", "ANDROID_CLAW"),
        ("send_data_to_cloud", "OPENCLAW"),
    ]
    
    print("=" * 50)
    print("CONSTITUTION ENFORCEMENT TEST")
    print("=" * 50)
    
    for action, actor in tests:
        result = enforcer.check_action(action, actor)
        status = "✅" if "APPROVED" in result["verdict"] else "❌"
        print(f"{status} {actor}: {action} → {result['verdict']} ({result['severity']})")
        print(f"   Reason: {result['reason']}")
        print()
    
    print("Audit log (last 5):")
    print(enforcer.get_audit(5))
