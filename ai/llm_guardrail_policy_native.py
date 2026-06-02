#!/usr/bin/env python3
"""
MAGNATRIX-OS — Guardrail Policy Engine
ai/llm_guardrail_policy_native.py

Inspired by Auto-Company (github.com/MaxMiksa/Auto-Company)
Pattern: Safety Guardrails — forbidden/allowed actions, policy enforcement.

Features:
- Forbidden actions table (destructive, illegal, credential leak, force-push)
- Allowed actions whitelist (create, deploy, commit, branch, install)
- Action policy validator (check before execution)
- Workspace policy enforcement (projects under projects/)
- Decision authority hierarchy (CEO decides, Critic vetoes)
- Policy violation logging and alerts
- Override mechanism (emergency bypass with audit trail)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import deque
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("guardrail_policy")


class ActionSeverity(enum.Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    AUDIT = "audit"


class AuthorityLevel(enum.Enum):
    AGENT = "agent"
    TEAM_LEAD = "team_lead"
    CRITIC = "critic"
    CEO = "ceo"


@dataclass
class ActionRule:
    pattern: str
    action_type: str
    severity: ActionSeverity
    reason: str
    authority_required: Optional[AuthorityLevel] = None


@dataclass
class PolicyViolation:
    action: str
    rule: ActionRule
    timestamp: str
    authority_override: Optional[str] = None


class GuardrailPolicyEngine:
    """Safety guardrails and action policy enforcement."""

    FORBIDDEN_RULES = [
        ActionRule(r"gh repo delete|repo delete|delete repo", "repo_deletion", ActionSeverity.BLOCK,
                   "Deleting repositories is forbidden"),
        ActionRule(r"wrangler delete|delete worker|delete page", "cloudflare_deletion", ActionSeverity.BLOCK,
                   "Deleting Cloudflare projects is forbidden"),
        ActionRule(r"rm -rf /|rm -rf ~|rm -rf /boot|rm -rf /etc|rm -rf /usr", "system_deletion", ActionSeverity.BLOCK,
                   "System-level deletion is forbidden"),
        ActionRule(r"rm -rf ~/.ssh|rm -rf ~/.config|rm -rf ~/.claude", "config_deletion", ActionSeverity.BLOCK,
                   "Deleting config directories is forbidden"),
        ActionRule(r"git push --force|git push -f", "force_push", ActionSeverity.BLOCK,
                   "Force-push to protected branches is forbidden"),
        ActionRule(r"git reset --hard", "hard_reset", ActionSeverity.BLOCK,
                   "Hard reset on shared branches is forbidden"),
        ActionRule(r"apikey|api_key|password|token|secret", "credential_leak", ActionSeverity.AUDIT,
                   "Credentials must not be committed to public repos", AuthorityLevel.CRITIC),
        ActionRule(r"fraud|infringement|data theft|unauthorized access", "illegal_activity", ActionSeverity.BLOCK,
                   "Illegal activity is forbidden"),
    ]

    ALLOWED_RULES = [
        ActionRule(r"git init|git clone|git create", "repo_create", ActionSeverity.ALLOW,
                   "Creating repos is allowed"),
        ActionRule(r"git commit|git add|git branch", "git_operations", ActionSeverity.ALLOW,
                   "Git operations are allowed"),
        ActionRule(r"wrangler deploy|npm deploy|deploy", "deployment", ActionSeverity.ALLOW,
                   "Deployment is allowed"),
        ActionRule(r"npm install|pip install|cargo install", "install_deps", ActionSeverity.ALLOW,
                   "Installing dependencies is allowed"),
        ActionRule(r"mkdir|touch|cp|mv", "file_operations", ActionSeverity.ALLOW,
                   "File operations are allowed"),
    ]

    WORKSPACE_RULES = [
        ActionRule(r"projects/", "workspace_projects", ActionSeverity.ALLOW,
                   "All projects must be under projects/ directory"),
    ]

    def __init__(self):
        self._violations: deque = deque(maxlen=100)
        self._audit_log: deque = deque(maxlen=500)
        self._authority_hierarchy = {
            AuthorityLevel.AGENT: 1,
            AuthorityLevel.TEAM_LEAD: 2,
            AuthorityLevel.CRITIC: 3,
            AuthorityLevel.CEO: 4,
        }

    def validate(self, action: str, authority: AuthorityLevel = AuthorityLevel.AGENT) -> Tuple[ActionSeverity, Optional[str]]:
        """Validate an action against policy rules."""
        action_lower = action.lower()

        # Check forbidden rules first
        for rule in self.FORBIDDEN_RULES:
            if re.search(rule.pattern, action_lower):
                if rule.authority_required and self._authority_hierarchy.get(authority, 0) < self._authority_hierarchy.get(rule.authority_required, 0):
                    violation = PolicyViolation(action=action, rule=rule, timestamp="now")
                    self._violations.append(violation)
                    return ActionSeverity.BLOCK, f"BLOCKED: {rule.reason} (requires {rule.authority_required.value} authority)"
                if rule.severity == ActionSeverity.AUDIT:
                    self._audit_log.append({"action": action, "rule": rule.reason, "authority": authority.value})
                    return ActionSeverity.AUDIT, f"AUDIT: {rule.reason}"
                violation = PolicyViolation(action=action, rule=rule, timestamp="now")
                self._violations.append(violation)
                return ActionSeverity.BLOCK, f"BLOCKED: {rule.reason}"

        # Check allowed rules
        for rule in self.ALLOWED_RULES:
            if re.search(rule.pattern, action_lower):
                return ActionSeverity.ALLOW, f"ALLOWED: {rule.reason}"

        # Default: warn for unknown actions
        return ActionSeverity.WARN, f"WARNING: Unrecognized action '{action}' — review required"

    def check_workspace(self, path: str) -> Tuple[bool, str]:
        """Check if path complies with workspace rules."""
        if not path.startswith("projects/") and not path.startswith("/projects/"):
            return False, f"Path '{path}' must be under projects/ directory"
        return True, "Workspace compliant"

    def can_override(self, authority: AuthorityLevel, rule: ActionRule) -> bool:
        """Check if authority level can override a rule."""
        if not rule.authority_required:
            return False
        return self._authority_hierarchy.get(authority, 0) >= self._authority_hierarchy.get(rule.authority_required, 0)

    def override(self, action: str, authority: AuthorityLevel, reason: str) -> Tuple[bool, str]:
        """Emergency override with audit trail."""
        action_lower = action.lower()
        for rule in self.FORBIDDEN_RULES:
            if re.search(rule.pattern, action_lower):
                if self.can_override(authority, rule):
                    violation = PolicyViolation(
                        action=action, rule=rule, timestamp="now", authority_override=f"{authority.value}: {reason}")
                    self._violations.append(violation)
                    self._audit_log.append({"override": True, "action": action, "authority": authority.value, "reason": reason})
                    return True, f"OVERRIDE: {authority.value} authorized — {reason}"
                return False, f"OVERRIDE DENIED: {authority.value} insufficient authority for {rule.reason}"
        return True, "No forbidden rule matched — no override needed"

    def get_violations(self, n: int = 20) -> List[PolicyViolation]:
        return list(self._violations)[-n:]

    def get_audit_log(self, n: int = 50) -> List[Dict[str, Any]]:
        return list(self._audit_log)[-n:]

    def get_policy_summary(self) -> Dict[str, Any]:
        return {
            "forbidden_rules": len(self.FORBIDDEN_RULES),
            "allowed_rules": len(self.ALLOWED_RULES),
            "total_violations": len(self._violations),
            "total_audits": len(self._audit_log),
            "authority_levels": list(self._authority_hierarchy.keys()),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Guardrail Policy Engine")
    print("ai/llm_guardrail_policy_native.py")
    print("Pattern: Auto-Company Safety Guardrails")
    print("=" * 60)

    engine = GuardrailPolicyEngine()

    # 1. Allowed actions
    print("\n[1] Allowed Actions")
    for action in ["git commit -m 'feat: add feature'", "npm install express", "wrangler deploy"]:
        severity, reason = engine.validate(action)
        print(f"  {action}: {severity.value} — {reason}")

    # 2. Forbidden actions
    print("\n[2] Forbidden Actions (BLOCKED)")
    for action in ["gh repo delete myrepo", "rm -rf /", "git push --force", "git reset --hard"]:
        severity, reason = engine.validate(action)
        print(f"  {action}: {severity.value} — {reason}")

    # 3. Credential leak audit
    print("\n[3] Credential Leak (AUDIT)")
    severity, reason = engine.validate("apikey = 'sk-abc123'", authority=AuthorityLevel.AGENT)
    print(f"  apikey leaked: {severity.value} — {reason}")

    # 4. Workspace check
    print("\n[4] Workspace Compliance")
    ok, msg = engine.check_workspace("projects/alpha-app")
    print(f"  projects/alpha-app: {'OK' if ok else 'FAIL'} — {msg}")
    ok, msg = engine.check_workspace("/home/user/myapp")
    print(f"  /home/user/myapp: {'OK' if ok else 'FAIL'} — {msg}")

    # 5. Override
    print("\n[5] Authority Override")
    ok, msg = engine.override("rm -rf /", AuthorityLevel.CEO, "Emergency system rebuild authorized")
    print(f"  CEO override rm -rf /: {'OK' if ok else 'FAIL'} — {msg}")
    ok, msg = engine.override("git push --force", AuthorityLevel.AGENT, "Need to fix history")
    print(f"  Agent override force-push: {'OK' if ok else 'FAIL'} — {msg}")
    ok, msg = engine.override("git push --force", AuthorityLevel.CRITIC, "Approved for hotfix")
    print(f"  Critic override force-push: {'OK' if ok else 'FAIL'} — {msg}")

    # 6. Violations
    print("\n[6] Violations Log")
    violations = engine.get_violations(5)
    for v in violations:
        print(f"  {v.action}: {v.rule.reason} (override={v.authority_override})")

    # 7. Audit log
    print("\n[7] Audit Log")
    audits = engine.get_audit_log(5)
    for a in audits:
        print(f"  {a}")

    # 8. Policy summary
    print("\n[8] Policy Summary")
    summary = engine.get_policy_summary()
    print(f"  {summary}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
