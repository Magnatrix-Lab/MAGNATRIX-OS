"""
governance_native.py — MAGNATRIX Governance Layer (Layer 11)
Native pure-Python implementation. No external dependencies.

Architecture references:
  - DAO governance frameworks (Aragon, Moloch, Compound Governor)
  - Quadratic voting (Glen Weyl, Radical Markets)
  - Role-based access control (RBAC) patterns
  - Constitution-as-code (rule engines, policy enforcement)

Style: modular, fully typed, event-driven audit trail.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Dict, List, Set, Optional, Callable, Any, Union
from collections import defaultdict

# ──────────────────────────────────────────────────────────────
# 0. Types & Constants
# ──────────────────────────────────────────────────────────────

ProposalID = str
UserID = str
RoleName = str

VOTE_QUORUM_DEFAULT = 0.51          # 51% quorum
VOTE_THRESHOLD_DEFAULT = 0.50       # simple majority
PROPOSAL_TTL_DEFAULT = 86400.0      # 24 hours
REPUTATION_WEIGHT_BASE = 1.0


# ──────────────────────────────────────────────────────────────
# 1. Role-Based Access Control
# ──────────────────────────────────────────────────────────────

class Permission(Enum):
    PROPOSE = auto()
    VOTE = auto()
    EXECUTE = auto()
    ADMIN = auto()
    VIEW = auto()
    AUDIT = auto()


class Role(Enum):
    ADMIN = {Permission.ADMIN, Permission.PROPOSE, Permission.VOTE, Permission.EXECUTE, Permission.AUDIT, Permission.VIEW}
    OPERATOR = {Permission.PROPOSE, Permission.VOTE, Permission.EXECUTE, Permission.VIEW}
    VIEWER = {Permission.VIEW, Permission.AUDIT}
    GUEST = {Permission.VIEW}


@dataclass
class User:
    """Governance participant with roles and reputation."""
    user_id: UserID
    roles: Set[Role] = field(default_factory=lambda: {Role.GUEST})
    reputation: float = 1.0
    delegated_to: Optional[UserID] = None
    delegated_from: Set[UserID] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)

    def has_permission(self, perm: Permission) -> bool:
        for role in self.roles:
            if perm in role.value:
                return True
        return False

    def __repr__(self) -> str:
        roles = ",".join(r.name for r in self.roles)
        return f"<User {self.user_id[:8]} roles={roles} rep={self.reputation:.2f}>"


# ──────────────────────────────────────────────────────────────
# 2. Constitution (Rules Engine)
# ──────────────────────────────────────────────────────────────

class RuleOperator(Enum):
    EQ = auto()
    NE = auto()
    GT = auto()
    GTE = auto()
    LT = auto()
    LTE = auto()
    IN = auto()
    CONTAINS = auto()
    AND = auto()
    OR = auto()


@dataclass
class Rule:
    """Single governance rule: field + operator + value."""
    field: str
    operator: RuleOperator
    value: Any
    description: str = ""

    def evaluate(self, context: dict) -> bool:
        actual = context.get(self.field)
        if self.operator == RuleOperator.EQ:
            return actual == self.value
        elif self.operator == RuleOperator.NE:
            return actual != self.value
        elif self.operator == RuleOperator.GT:
            return actual is not None and actual > self.value
        elif self.operator == RuleOperator.GTE:
            return actual is not None and actual >= self.value
        elif self.operator == RuleOperator.LT:
            return actual is not None and actual < self.value
        elif self.operator == RuleOperator.LTE:
            return actual is not None and actual <= self.value
        elif self.operator == RuleOperator.IN:
            return actual in self.value
        elif self.operator == RuleOperator.CONTAINS:
            return self.value in actual if actual else False
        return False

    def __repr__(self) -> str:
        return f"<Rule {self.field} {self.operator.name} {self.value}>"


@dataclass
class RuleSet:
    """Composable rule set with AND/OR logic."""
    rules: List[Rule]
    operator: RuleOperator = RuleOperator.AND
    name: str = ""

    def evaluate(self, context: dict) -> bool:
        if not self.rules:
            return True
        results = [r.evaluate(context) for r in self.rules]
        if self.operator == RuleOperator.AND:
            return all(results)
        elif self.operator == RuleOperator.OR:
            return any(results)
        return False

    def __repr__(self) -> str:
        return f"<RuleSet '{self.name}' {len(self.rules)} rules>"


class Constitution:
    """Living constitution: rule registry, validation, enforcement."""

    def __init__(self) -> None:
        self.rulesets: Dict[str, RuleSet] = {}
        self.amendment_history: List[dict] = []
        self.version = 1

    def add_ruleset(self, name: str, ruleset: RuleSet) -> None:
        self.rulesets[name] = ruleset
        self._log_amendment("add_ruleset", name)

    def remove_ruleset(self, name: str) -> bool:
        if name in self.rulesets:
            del self.rulesets[name]
            self._log_amendment("remove_ruleset", name)
            return True
        return False

    def validate(self, action_type: str, context: dict) -> tuple[bool, List[str]]:
        """Validate action against all applicable rules. Returns (passed, violations)."""
        violations: List[str] = []
        for name, ruleset in self.rulesets.items():
            if name.startswith(action_type) or name == "global":
                if not ruleset.evaluate(context):
                    violations.append(f"Ruleset '{name}' failed")
        return len(violations) == 0, violations

    def enforce(self, action_type: str, context: dict) -> bool:
        """Hard enforcement — raises if validation fails."""
        passed, violations = self.validate(action_type, context)
        if not passed:
            raise GovernanceViolation(f"Constitution violation: {violations}")
        return True

    def _log_amendment(self, action: str, target: str) -> None:
        self.amendment_history.append({
            "version": self.version,
            "action": action,
            "target": target,
            "timestamp": time.time(),
        })
        self.version += 1

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "rulesets": {k: {"name": v.name, "rules": len(v.rules)} for k, v in self.rulesets.items()},
            "amendments": len(self.amendment_history),
        }

    def __repr__(self) -> str:
        return f"<Constitution v{self.version} {len(self.rulesets)} rulesets>"


class GovernanceViolation(Exception):
    """Raised when constitution enforcement fails."""
    pass


# ──────────────────────────────────────────────────────────────
# 3. Proposal Lifecycle
# ──────────────────────────────────────────────────────────────

class ProposalStatus(Enum):
    DRAFT = auto()
    PENDING = auto()
    ACTIVE = auto()
    PASSED = auto()
    REJECTED = auto()
    EXECUTED = auto()
    EXPIRED = auto()
    CANCELLED = auto()


class VoteType(Enum):
    YES = auto()
    NO = auto()
    ABSTAIN = auto()


@dataclass
class Vote:
    """Individual vote record."""
    voter_id: UserID
    vote_type: VoteType
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)
    reason: str = ""

    def __repr__(self) -> str:
        return f"<Vote {self.voter_id[:8]} {self.vote_type.name} w={self.weight:.2f}>"


@dataclass
class Proposal:
    """Full proposal with metadata, votes, and execution payload."""
    proposal_id: ProposalID
    title: str
    description: str
    proposer_id: UserID
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + PROPOSAL_TTL_DEFAULT)
    quorum: float = VOTE_QUORUM_DEFAULT
    threshold: float = VOTE_THRESHOLD_DEFAULT
    votes: List[Vote] = field(default_factory=list)
    execution_payload: Optional[dict] = None
    execution_result: Optional[dict] = None
    tags: Set[str] = field(default_factory=set)

    def tally(self) -> dict:
        """Return vote counts and statistics."""
        yes_weight = sum(v.weight for v in self.votes if v.vote_type == VoteType.YES)
        no_weight = sum(v.weight for v in self.votes if v.vote_type == VoteType.NO)
        abstain_weight = sum(v.weight for v in self.votes if v.vote_type == VoteType.ABSTAIN)
        total_weight = yes_weight + no_weight + abstain_weight
        total_voters = len(self.votes)

        return {
            "yes": yes_weight,
            "no": no_weight,
            "abstain": abstain_weight,
            "total_weight": total_weight,
            "total_voters": total_voters,
            "yes_ratio": yes_weight / total_weight if total_weight > 0 else 0,
            "participation": total_weight,
        }

    def check_quorum(self, total_eligible_weight: float) -> bool:
        """Check if participation meets quorum requirement."""
        tally = self.tally()
        return tally["total_weight"] >= total_eligible_weight * self.quorum

    def check_threshold(self) -> bool:
        """Check if yes votes meet threshold."""
        tally = self.tally()
        total_decisive = tally["yes"] + tally["no"]
        if total_decisive == 0:
            return False
        return tally["yes"] / total_decisive >= self.threshold

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def __repr__(self) -> str:
        return f"<Proposal {self.proposal_id[:8]} '{self.title[:20]}' {self.status.name}>"


# ──────────────────────────────────────────────────────────────
# 4. Voting Mechanisms
# ──────────────────────────────────────────────────────────────

class VotingMechanism:
    """Base class for voting strategies."""

    def calculate_weight(self, user: User, base_weight: float = 1.0) -> float:
        return base_weight * user.reputation


class WeightedVoting(VotingMechanism):
    """Standard weighted voting: reputation * stake."""

    def __init__(self, stake_weights: Dict[UserID, float] = None) -> None:
        self.stake_weights = stake_weights or {}

    def calculate_weight(self, user: User, base_weight: float = 1.0) -> float:
        stake = self.stake_weights.get(user.user_id, 0.0)
        return (base_weight + stake) * user.reputation


class QuadraticVoting(VotingMechanism):
    """Quadratic voting: cost = votes², weight = √spend."""

    def __init__(self, credits: Dict[UserID, float] = None) -> None:
        self.credits = credits or {}
        self.spent: Dict[UserID, float] = defaultdict(float)

    def calculate_weight(self, user: User, desired_votes: float = 1.0) -> float:
        """Return actual vote weight given credit budget."""
        available = self.credits.get(user.user_id, 0.0) - self.spent[user.user_id]
        cost = desired_votes ** 2
        if cost > available:
            # scale down
            desired_votes = available ** 0.5 if available > 0 else 0.0
            cost = desired_votes ** 2
        self.spent[user.user_id] += cost
        return desired_votes * user.reputation

    def refund(self, user_id: UserID, amount: float) -> None:
        self.spent[user_id] = max(0.0, self.spent[user_id] - amount)


class DelegatedVoting(VotingMechanism):
    """Liquid democracy: delegate voting power to another user."""

    def __init__(self, delegation_graph: Dict[UserID, UserID] = None) -> None:
        self.delegation_graph = delegation_graph or {}

    def resolve_delegate(self, user_id: UserID) -> UserID:
        """Follow delegation chain to final voter."""
        visited: Set[UserID] = set()
        current = user_id
        while current in self.delegation_graph and current not in visited:
            visited.add(current)
            current = self.delegation_graph[current]
        return current

    def calculate_weight(self, user: User, base_weight: float = 1.0) -> float:
        # weight flows to delegatee
        return base_weight * user.reputation


# ──────────────────────────────────────────────────────────────
# 5. Governance Engine
# ──────────────────────────────────────────────────────────────

class GovernanceEngine:
    """Central governance coordinator: proposals, voting, execution, audit."""

    def __init__(self, constitution: Optional[Constitution] = None) -> None:
        self.constitution = constitution or Constitution()
        self.users: Dict[UserID, User] = {}
        self.proposals: Dict[ProposalID, Proposal] = {}
        self.voting_mechanism: VotingMechanism = WeightedVoting()
        self.audit_log: List[dict] = []
        self._listeners: List[Callable[[str, dict], None]] = []

    # ── user management ──

    def register_user(self, user_id: UserID, roles: Optional[Set[Role]] = None) -> User:
        user = User(user_id=user_id, roles=roles or {Role.VIEWER})
        self.users[user_id] = user
        self._emit("user_registered", {"user_id": user_id, "roles": [r.name for r in user.roles]})
        return user

    def assign_role(self, user_id: UserID, role: Role) -> bool:
        if user_id not in self.users:
            return False
        self.users[user_id].roles.add(role)
        self._emit("role_assigned", {"user_id": user_id, "role": role.name})
        return True

    def revoke_role(self, user_id: UserID, role: Role) -> bool:
        if user_id not in self.users:
            return False
        self.users[user_id].roles.discard(role)
        self._emit("role_revoked", {"user_id": user_id, "role": role.name})
        return True

    # ── proposal lifecycle ──

    def create_proposal(
        self,
        proposer_id: UserID,
        title: str,
        description: str,
        execution_payload: Optional[dict] = None,
        quorum: float = VOTE_QUORUM_DEFAULT,
        threshold: float = VOTE_THRESHOLD_DEFAULT,
        ttl: float = PROPOSAL_TTL_DEFAULT,
    ) -> Optional[Proposal]:
        # validate proposer permissions
        if proposer_id not in self.users:
            return None
        proposer = self.users[proposer_id]
        if not proposer.has_permission(Permission.PROPOSE):
            raise GovernanceViolation(f"User {proposer_id} lacks PROPOSE permission")

        # constitution check
        context = {
            "proposer_reputation": proposer.reputation,
            "active_proposals": len([p for p in self.proposals.values() if p.status == ProposalStatus.ACTIVE]),
            "user_roles": [r.name for r in proposer.roles],
        }
        self.constitution.enforce("proposal", context)

        proposal = Proposal(
            proposal_id=secrets.token_hex(16),
            title=title,
            description=description,
            proposer_id=proposer_id,
            status=ProposalStatus.PENDING,
            quorum=quorum,
            threshold=threshold,
            expires_at=time.time() + ttl,
            execution_payload=execution_payload,
        )
        self.proposals[proposal.proposal_id] = proposal
        self._emit("proposal_created", {"proposal_id": proposal.proposal_id, "title": title})
        return proposal

    def activate_proposal(self, proposal_id: ProposalID) -> bool:
        prop = self.proposals.get(proposal_id)
        if not prop or prop.status != ProposalStatus.PENDING:
            return False
        prop.status = ProposalStatus.ACTIVE
        self._emit("proposal_activated", {"proposal_id": proposal_id})
        return True

    def vote(
        self,
        voter_id: UserID,
        proposal_id: ProposalID,
        vote_type: VoteType,
        weight_override: Optional[float] = None,
        reason: str = "",
    ) -> bool:
        if voter_id not in self.users:
            return False
        voter = self.users[voter_id]
        if not voter.has_permission(Permission.VOTE):
            raise GovernanceViolation(f"User {voter_id} lacks VOTE permission")

        prop = self.proposals.get(proposal_id)
        if not prop or prop.status != ProposalStatus.ACTIVE:
            return False
        if prop.is_expired():
            prop.status = ProposalStatus.EXPIRED
            return False

        # calculate weight
        weight = weight_override or self.voting_mechanism.calculate_weight(voter)

        # check for existing vote
        existing = [v for v in prop.votes if v.voter_id == voter_id]
        if existing:
            # update vote
            existing[0].vote_type = vote_type
            existing[0].weight = weight
            existing[0].timestamp = time.time()
            existing[0].reason = reason
        else:
            vote = Vote(voter_id=voter_id, vote_type=vote_type, weight=weight, reason=reason)
            prop.votes.append(vote)

        self._emit("vote_cast", {
            "proposal_id": proposal_id,
            "voter_id": voter_id,
            "vote_type": vote_type.name,
            "weight": weight,
        })
        return True

    def tally_proposal(self, proposal_id: ProposalID) -> dict:
        prop = self.proposals.get(proposal_id)
        if not prop:
            return {"error": "not_found"}

        tally = prop.tally()
        total_eligible = sum(u.reputation for u in self.users.values() if u.has_permission(Permission.VOTE))

        quorum_met = prop.check_quorum(total_eligible)
        threshold_met = prop.check_threshold()

        result = {
            "proposal_id": proposal_id,
            "status": prop.status.name,
            "tally": tally,
            "quorum_met": quorum_met,
            "threshold_met": threshold_met,
            "expired": prop.is_expired(),
        }

        # auto-update status
        if prop.status == ProposalStatus.ACTIVE:
            if prop.is_expired():
                prop.status = ProposalStatus.EXPIRED
                result["status"] = "EXPIRED"
            elif quorum_met and threshold_met:
                prop.status = ProposalStatus.PASSED
                result["status"] = "PASSED"
            elif quorum_met and not threshold_met and prop.is_expired():
                prop.status = ProposalStatus.REJECTED
                result["status"] = "REJECTED"

        return result

    def execute_proposal(self, proposal_id: ProposalID, executor_id: UserID) -> dict:
        prop = self.proposals.get(proposal_id)
        if not prop:
            return {"error": "not_found"}

        if executor_id not in self.users:
            return {"error": "executor_not_found"}
        executor = self.users[executor_id]
        if not executor.has_permission(Permission.EXECUTE):
            raise GovernanceViolation(f"User {executor_id} lacks EXECUTE permission")

        if prop.status != ProposalStatus.PASSED:
            return {"error": "not_passed", "status": prop.status.name}

        # execute payload
        result = {
            "executed_at": time.time(),
            "executor_id": executor_id,
            "payload": prop.execution_payload,
            "success": True,
        }
        prop.execution_result = result
        prop.status = ProposalStatus.EXECUTED

        self._emit("proposal_executed", {"proposal_id": proposal_id, "executor_id": executor_id})
        return result

    def cancel_proposal(self, proposal_id: ProposalID, canceller_id: UserID) -> bool:
        prop = self.proposals.get(proposal_id)
        if not prop:
            return False
        if canceller_id != prop.proposer_id and not self.users.get(canceller_id, User("")).has_permission(Permission.ADMIN):
            return False
        prop.status = ProposalStatus.CANCELLED
        self._emit("proposal_cancelled", {"proposal_id": proposal_id, "canceller_id": canceller_id})
        return True

    # ── delegation ──

    def delegate_vote(self, delegator_id: UserID, delegatee_id: UserID) -> bool:
        if delegator_id not in self.users or delegatee_id not in self.users:
            return False
        self.users[delegator_id].delegated_to = delegatee_id
        self.users[delegatee_id].delegated_from.add(delegator_id)
        self._emit("vote_delegated", {"from": delegator_id, "to": delegatee_id})
        return True

    def revoke_delegation(self, delegator_id: UserID) -> bool:
        if delegator_id not in self.users:
            return False
        user = self.users[delegator_id]
        if user.delegated_to:
            self.users[user.delegated_to].delegated_from.discard(delegator_id)
            user.delegated_to = None
        self._emit("delegation_revoked", {"user_id": delegator_id})
        return True

    # ── audit & events ──

    def _emit(self, event_type: str, data: dict) -> None:
        entry = {
            "event_type": event_type,
            "timestamp": time.time(),
            "data": data,
        }
        self.audit_log.append(entry)
        for listener in self._listeners:
            try:
                listener(event_type, data)
            except Exception:
                pass

    def add_listener(self, listener: Callable[[str, dict], None]) -> None:
        self._listeners.append(listener)

    def get_audit_trail(self, proposal_id: Optional[ProposalID] = None) -> List[dict]:
        if proposal_id:
            return [e for e in self.audit_log if e["data"].get("proposal_id") == proposal_id]
        return list(self.audit_log)

    def stats(self) -> dict:
        return {
            "users": len(self.users),
            "proposals": len(self.proposals),
            "active_proposals": len([p for p in self.proposals.values() if p.status == ProposalStatus.ACTIVE]),
            "executed_proposals": len([p for p in self.proposals.values() if p.status == ProposalStatus.EXECUTED]),
            "audit_entries": len(self.audit_log),
            "constitution": self.constitution.to_dict(),
        }

    def __repr__(self) -> str:
        return f"<GovernanceEngine users={len(self.users)} proposals={len(self.proposals)}>"


# ──────────────────────────────────────────────────────────────
# 6. GovernanceKernel — bridge to Layer 11 (MAGNATRIX runtime)
# ──────────────────────────────────────────────────────────────

class GovernanceKernel:
    """High-level API for MAGNATRIX OS integration."""

    def __init__(self, engine: GovernanceEngine) -> None:
        self.engine = engine

    def propose(self, proposer_id: UserID, title: str, description: str, payload: Optional[dict] = None) -> Optional[Proposal]:
        return self.engine.create_proposal(proposer_id, title, description, payload)

    def vote(self, voter_id: UserID, proposal_id: ProposalID, vote_type: str, reason: str = "") -> bool:
        vt = VoteType[vote_type.upper()]
        return self.engine.vote(voter_id, proposal_id, vt, reason=reason)

    def tally(self, proposal_id: ProposalID) -> dict:
        return self.engine.tally_proposal(proposal_id)

    def execute(self, proposal_id: ProposalID, executor_id: UserID) -> dict:
        return self.engine.execute_proposal(proposal_id, executor_id)

    def audit(self, proposal_id: Optional[ProposalID] = None) -> List[dict]:
        return self.engine.get_audit_trail(proposal_id)

    def register(self, user_id: UserID, roles: Optional[List[str]] = None) -> User:
        role_set = {Role[r.upper()] for r in roles} if roles else {Role.VIEWER}
        return self.engine.register_user(user_id, role_set)

    def stats(self) -> dict:
        return self.engine.stats()


# ──────────────────────────────────────────────────────────────
# 7. Demo
# ──────────────────────────────────────────────────────────────

def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX Governance — Demo")
    print("=" * 60)

    # setup constitution
    constitution = Constitution()
    constitution.add_ruleset("proposal", RuleSet(
        name="proposal_rules",
        rules=[
            Rule("proposer_reputation", RuleOperator.GTE, 0.5, "Proposer must have reputation >= 0.5"),
            Rule("active_proposals", RuleOperator.LT, 10, "Max 10 active proposals"),
        ],
        operator=RuleOperator.AND,
    ))
    constitution.add_ruleset("vote", RuleSet(
        name="vote_rules",
        rules=[
            Rule("user_roles", RuleOperator.CONTAINS, "OPERATOR", "Voter must be operator or admin"),
        ],
    ))

    # init engine
    gov = GovernanceEngine(constitution)
    kernel = GovernanceKernel(gov)

    # register users
    admin = kernel.register("admin_alice", ["ADMIN"])
    operator1 = kernel.register("operator_bob", ["OPERATOR"])
    operator2 = kernel.register("operator_carol", ["OPERATOR"])
    viewer = kernel.register("viewer_dave", ["VIEWER"])

    print(f"\n[USERS] Registered: {admin}, {operator1}, {operator2}, {viewer}")

    # create proposal
    prop = kernel.propose(
        "admin_alice",
        "Deploy Phase 7",
        "Activate MAGNATRIX Phase 7 components: P2P mesh + governance + security",
        payload={"action": "deploy", "target": "phase7", "params": {"auto_scale": True}},
    )
    print(f"\n[PROPOSAL] Created: {prop}")

    # activate
    gov.activate_proposal(prop.proposal_id)
    print(f"[PROPOSAL] Activated: {prop.proposal_id[:8]}")

    # cast votes
    kernel.vote("operator_bob", prop.proposal_id, "YES", "Critical infrastructure")
    kernel.vote("operator_carol", prop.proposal_id, "YES", "Agreed, let's ship")
    print(f"[VOTE] Bob & Carol voted YES")

    # tally
    result = kernel.tally(prop.proposal_id)
    print(f"\n[TALLY] {json.dumps(result, indent=2, default=str)}")

    # execute
    exec_result = kernel.execute(prop.proposal_id, "admin_alice")
    print(f"\n[EXECUTE] Result: {json.dumps(exec_result, indent=2, default=str)}")

    # audit trail
    trail = kernel.audit(prop.proposal_id)
    print(f"\n[AUDIT] {len(trail)} entries for this proposal:")
    for entry in trail:
        print(f"  {entry['timestamp']:.2f} | {entry['event_type']} | {entry['data']}")

    # full stats
    print(f"\n[STATS] {json.dumps(kernel.stats(), indent=2, default=str)}")

    # quadratic voting demo
    print("\n" + "-" * 60)
    print("QUADRATIC VOTING DEMO")
    print("-" * 60)

    qv = QuadraticVoting(credits={"operator_bob": 100.0, "operator_carol": 100.0})
    gov.voting_mechanism = qv

    prop2 = kernel.propose(
        "admin_alice",
        "Fund Research",
        "Allocate budget for HFT algorithm research",
        payload={"action": "fund", "amount": 50000},
    )
    gov.activate_proposal(prop2.proposal_id)

    # Bob wants to cast 5 votes (cost = 25 credits)
    weight_bob = qv.calculate_weight(operator1, desired_votes=5.0)
    gov.vote("operator_bob", prop2.proposal_id, VoteType.YES, weight_override=weight_bob)

    # Carol casts 3 votes (cost = 9 credits)
    weight_carol = qv.calculate_weight(operator2, desired_votes=3.0)
    gov.vote("operator_carol", prop2.proposal_id, VoteType.YES, weight_override=weight_carol)

    result2 = kernel.tally(prop2.proposal_id)
    print(f"[QV TALLY] {json.dumps(result2, indent=2, default=str)}")
    print(f"[QV CREDITS] Bob spent: {qv.spent['operator_bob']:.1f}, Carol spent: {qv.spent['operator_carol']:.1f}")

    # delegation demo
    print("\n" + "-" * 60)
    print("DELEGATED VOTING DEMO")
    print("-" * 60)

    gov.delegate_vote("viewer_dave", "operator_bob")
    print(f"[DELEGATE] Dave delegated to Bob")

    prop3 = kernel.propose(
        "admin_alice",
        "Security Patch",
        "Emergency security patch for Layer 13",
        payload={"action": "patch", "layer": 13},
    )
    gov.activate_proposal(prop3.proposal_id)
    kernel.vote("operator_bob", prop3.proposal_id, "YES")
    print(f"[VOTE] Bob voted (carrying Dave's delegation)")

    result3 = kernel.tally(prop3.proposal_id)
    print(f"[DELEGATED TALLY] {json.dumps(result3, indent=2, default=str)}")

    print("\n[DONE] Governance demo complete.")


if __name__ == "__main__":
    _demo()
