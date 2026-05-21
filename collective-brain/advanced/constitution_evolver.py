#!/usr/bin/env python3
"""
constitution_evolver.py — MAGNATRIX Constitution Evolution Engine
Batch Super AI — File 3/3

Constitution that evolves itself based on experience.
Immutable audit log, stale-rule detection, amendment simulation,
swarm consensus (2/3 nodes), human ratification.
"""
import hashlib
import json
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


# ── data structures ──────────────────────────────────────────────────────────

@dataclass
class RuleOutcome:
    rule_id: str
    result: str               # "triggered" | "bypassed" | "blocked" | "allowed"
    context_summary: str
    timestamp: str
    severity: str = "info"    # info | warn | critical


@dataclass
class ConstitutionalRule:
    rule_id: str
    text: str
    weight: float             # 0.0 - 1.0
    created_at: str
    trigger_count: int = 0
    bypass_count: int = 0
    block_count: int = 0
    allow_count: int = 0
    last_triggered: Optional[str] = None
    superseded_by: Optional[str] = None


@dataclass
class ProposedAmendment:
    amendment_id: str
    rule_id: str
    change_type: str          # "modify" | "remove" | "add"
    old_text: Optional[str]
    new_text: Optional[str]
    proposed_at: str
    proposer: str             # node_id or "human"
    simulation_result: Optional[Dict[str, Any]] = None
    ratified: bool = False
    rejected: bool = False
    ratification_votes: Dict[str, str] = field(default_factory=dict)  # node_id → "yes" | "no"
    human_approved: bool = False


@dataclass
class ImmutableLogEntry:
    entry_id: str
    entry_type: str           # "outcome" | "amendment_proposed" | "amendment_ratified" | "amendment_rejected" | "drift_detected"
    payload: Dict[str, Any]
    prev_hash: str
    this_hash: str
    timestamp: str


# ── hash chain ───────────────────────────────────────────────────────────────

class ImmutableChain:
    def __init__(self):
        self.entries: List[ImmutableLogEntry] = []
        self._last_hash = "0" * 64

    def append(self, entry_type: str, payload: Dict[str, Any]) -> ImmutableLogEntry:
        ts = datetime.now(timezone.utc).isoformat()
        data = json.dumps({"type": entry_type, "payload": payload, "prev": self._last_hash, "ts": ts}, sort_keys=True)
        this_hash = hashlib.sha256(data.encode("utf-8")).hexdigest()
        entry = ImmutableLogEntry(
            entry_id=f"{entry_type}-{len(self.entries):06d}-{this_hash[:8]}",
            entry_type=entry_type,
            payload=payload,
            prev_hash=self._last_hash,
            this_hash=this_hash,
            timestamp=ts,
        )
        self.entries.append(entry)
        self._last_hash = this_hash
        return entry

    def verify(self) -> bool:
        for i, entry in enumerate(self.entries):
            data = json.dumps({
                "type": entry.entry_type,
                "payload": entry.payload,
                "prev": entry.prev_hash,
                "ts": entry.timestamp,
            }, sort_keys=True)
            expected = hashlib.sha256(data.encode("utf-8")).hexdigest()
            if expected != entry.this_hash:
                return False
            if i == 0:
                if entry.prev_hash != "0" * 64:
                    return False
            else:
                if entry.prev_hash != self.entries[i - 1].this_hash:
                    return False
        return True

    def export(self) -> List[Dict[str, Any]]:
        return [asdict(e) for e in self.entries]


# ── constitution engine ────────────────────────────────────────────────────────

class ConstitutionEvolver:
    def __init__(self, constitution_text: Optional[str] = None):
        self.rules: Dict[str, ConstitutionalRule] = {}
        self.chain = ImmutableChain()
        self.amendments: Dict[str, ProposedAmendment] = {}
        self.swarm_nodes: List[str] = []
        self._parse_constitution(constitution_text or self._default_constitution())

    # ── core API ──

    def record_outcome(self, rule_id: str, result: str, context_summary: str,
                       severity: str = "info") -> None:
        if rule_id not in self.rules:
            return
        outcome = RuleOutcome(rule_id, result, context_summary,
                              datetime.now(timezone.utc).isoformat(), severity)
        rule = self.rules[rule_id]
        rule.trigger_count += 1
        rule.last_triggered = outcome.timestamp
        if result == "bypassed":
            rule.bypass_count += 1
        elif result == "blocked":
            rule.block_count += 1
        elif result == "allowed":
            rule.allow_count += 1
        self.chain.append("outcome", asdict(outcome))

    def identify_stale_rules(self, min_triggers: int = 5,
                             stale_bypass_ratio: float = 0.80,
                             max_age_days: int = 30) -> List[ConstitutionalRule]:
        stale = []
        now = datetime.now(timezone.utc)
        for rule in self.rules.values():
            if rule.superseded_by:
                continue
            if rule.trigger_count < min_triggers:
                continue
            bypass_ratio = rule.bypass_count / max(rule.trigger_count, 1)
            if bypass_ratio >= stale_bypass_ratio:
                stale.append(rule)
                continue
            # age-based staleness
            if rule.last_triggered:
                last = datetime.fromisoformat(rule.last_triggered.replace("Z", "+00:00"))
                age = (now - last).total_seconds() / 86400
                if age > max_age_days:
                    stale.append(rule)
        return stale

    def propose_amendment(self, rule_id: str, change_type: str,
                          new_text: Optional[str] = None,
                          proposer: str = "engine") -> Optional[ProposedAmendment]:
        if rule_id not in self.rules and change_type != "add":
            return None
        old_text = self.rules[rule_id].text if rule_id in self.rules else None
        prop = ProposedAmendment(
            amendment_id=f"amd-{rule_id}-{int(time.time())}-{random.randint(1000,9999)}",
            rule_id=rule_id,
            change_type=change_type,
            old_text=old_text,
            new_text=new_text,
            proposed_at=datetime.now(timezone.utc).isoformat(),
            proposer=proposer,
        )
        self.amendments[prop.amendment_id] = prop
        self.chain.append("amendment_proposed", asdict(prop))
        return prop

    def simulate_amendment(self, amendment_id: str,
                           synthetic_scenarios: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if amendment_id not in self.amendments:
            return None
        prop = self.amendments[amendment_id]
        # run a synthetic replay: how would the new rule perform vs old?
        old_hits = 0
        new_hits = 0
        for scenario in synthetic_scenarios:
            # crude simulation: check if scenario text is "caught" by rule text
            old_match = self._rule_matches(prop.old_text or "", scenario["text"])
            new_match = self._rule_matches(prop.new_text or "", scenario["text"])
            if old_match == scenario["expected"]:
                old_hits += 1
            if new_match == scenario["expected"]:
                new_hits += 1
        total = len(synthetic_scenarios)
        result = {
            "amendment_id": amendment_id,
            "scenarios_run": total,
            "old_accuracy": round(old_hits / total, 4) if total else 0,
            "new_accuracy": round(new_hits / total, 4) if total else 0,
            "improvement": round((new_hits - old_hits) / total, 4) if total else 0,
            "recommendation": "ratify" if new_hits >= old_hits else "reject",
        }
        prop.simulation_result = result
        self.chain.append("amendment_simulated", result)
        return result

    def ratify_or_reject(self, amendment_id: str,
                         node_votes: Dict[str, str],
                         human_approved: bool = False) -> str:
        if amendment_id not in self.amendments:
            return "not_found"
        prop = self.amendments[amendment_id]
        prop.ratification_votes.update(node_votes)
        prop.human_approved = human_approved

        # consensus: 2/3 of known swarm nodes must vote yes
        total_nodes = max(len(self.swarm_nodes), 3)
        yes_count = sum(1 for v in prop.ratification_votes.values() if v == "yes")
        quorum = (2 * total_nodes) // 3 + (1 if (2 * total_nodes) % 3 else 0)
        quorum_met = yes_count >= quorum

        if quorum_met and human_approved:
            prop.ratified = True
            self._apply_amendment(prop)
            self.chain.append("amendment_ratified", {
                "amendment_id": amendment_id,
                "yes_votes": yes_count,
                "quorum": quorum,
                "human": human_approved,
            })
            return "ratified"
        elif not human_approved:
            # human veto or absence
            prop.rejected = True
            self.chain.append("amendment_rejected", {
                "amendment_id": amendment_id,
                "reason": "human_approval_missing",
            })
            return "rejected_human"
        else:
            prop.rejected = True
            self.chain.append("amendment_rejected", {
                "amendment_id": amendment_id,
                "reason": "quorum_not_met",
                "yes_votes": yes_count,
                "quorum": quorum,
            })
            return "rejected_quorum"

    # ── helpers ──

    def _parse_constitution(self, text: str):
        lines = text.strip().splitlines()
        current_id = None
        current_text = []
        current_weight = 0.5
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and "]" in line:
                if current_id:
                    self._add_rule(current_id, "\n".join(current_text), current_weight)
                current_id = line[1:line.index("]")]
                current_text = []
                current_weight = 0.5
            elif line.startswith("weight="):
                current_weight = float(line.split("=")[1])
            else:
                current_text.append(line)
        if current_id:
            self._add_rule(current_id, "\n".join(current_text), current_weight)

    def _add_rule(self, rule_id: str, text: str, weight: float):
        self.rules[rule_id] = ConstitutionalRule(
            rule_id=rule_id,
            text=text,
            weight=weight,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _apply_amendment(self, prop: ProposedAmendment):
        if prop.change_type == "remove":
            if prop.rule_id in self.rules:
                self.rules[prop.rule_id].superseded_by = prop.amendment_id
        elif prop.change_type == "modify":
            if prop.rule_id in self.rules:
                old = self.rules[prop.rule_id]
                old.superseded_by = prop.amendment_id
                self._add_rule(prop.rule_id, prop.new_text or old.text, old.weight)
                self.rules[prop.rule_id].trigger_count = old.trigger_count
        elif prop.change_type == "add":
            self._add_rule(prop.rule_id, prop.new_text or "", 0.5)

    @staticmethod
    def _rule_matches(rule_text: str, scenario_text: str) -> bool:
        # ultra-simple keyword matching for synthetic simulation
        keywords = [w.lower() for w in rule_text.split() if len(w) > 3]
        text_lower = scenario_text.lower()
        return any(kw in text_lower for kw in keywords)

    @staticmethod
    def _default_constitution() -> str:
        return """
[safety_first]
Never execute destructive commands without explicit human confirmation.
weight=0.95

[user_autonomy]
Respect user decisions even when suboptimal.
weight=0.80

[transparency]
Log every significant action with reasoning.
weight=0.70

[privacy]
Do not exfiltrate user data to external services without consent.
weight=0.90

[emotional_safety]
Avoid responses that increase distress in high-risk contexts.
weight=0.75

[agent_cooperation]
Collaborate with peer agents rather than compete.
weight=0.60
"""

    # ── queries ──

    def get_rule_stats(self) -> Dict[str, Dict[str, Any]]:
        return {
            rid: {
                "text": r.text[:60] + "..." if len(r.text) > 60 else r.text,
                "weight": r.weight,
                "triggers": r.trigger_count,
                "bypasses": r.bypass_count,
                "blocks": r.block_count,
                "allows": r.allow_count,
                "superseded": r.superseded_by is not None,
            }
            for rid, r in self.rules.items()
        }

    def get_chain_summary(self) -> Dict[str, Any]:
        return {
            "length": len(self.chain.entries),
            "verified": self.chain.verify(),
            "last_hash": self.chain._last_hash[:16] + "...",
            "entry_types": {},
        }


# ── demo ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX Constitution Evolver — Rule Evolution Engine")
    print("=" * 60)

    engine = ConstitutionEvolver()
    engine.swarm_nodes = ["alpha", "beta", "gamma", "delta"]

    # 1. seed outcomes
    print("\n[1] RECORD OUTCOMES (simulate 30 events)")
    random.seed(42)
    for i in range(30):
        rule = random.choice(list(engine.rules.keys()))
        result = random.choices(
            ["triggered", "bypassed", "blocked", "allowed"],
            weights=[0.3, 0.2, 0.3, 0.2]
        )[0]
        engine.record_outcome(rule, result, f"scenario-{i}")
    print(f"  chain length = {len(engine.chain.entries)}")

    # 2. detect stale
    print("\n[2] STALE RULE DETECTION")
    stale = engine.identify_stale_rules(min_triggers=3, stale_bypass_ratio=0.5)
    for r in stale:
        print(f"  ⚠ {r.rule_id}: triggers={r.trigger_count} bypass={r.bypass_count}")

    # 3. propose amendment
    print("\n[3] PROPOSE AMENDMENT")
    prop = engine.propose_amendment(
        "emotional_safety",
        "modify",
        new_text="Avoid responses that increase distress; escalate to human in high-risk contexts.",
        proposer="beta",
    )
    if prop:
        print(f"  proposed {prop.amendment_id} for rule '{prop.rule_id}'")

    # 4. simulate
    print("\n[4] SIMULATE AMENDMENT")
    scenarios = [
        {"text": "user expresses severe depression", "expected": True},
        {"text": "user asks for stock price", "expected": False},
        {"text": "user mentions self-harm", "expected": True},
        {"text": "routine weather request", "expected": False},
        {"text": "user is crying and hopeless", "expected": True},
    ]
    sim = engine.simulate_amendment(prop.amendment_id, scenarios)
    if sim:
        print(f"  old_accuracy={sim['old_accuracy']} new_accuracy={sim['new_accuracy']} "
              f"improvement={sim['improvement']} → {sim['recommendation']}")

    # 5. ratify
    print("\n[5] RATIFY OR REJECT")
    votes = {"alpha": "yes", "beta": "yes", "gamma": "yes", "delta": "no"}
    status = engine.ratify_or_reject(prop.amendment_id, votes, human_approved=True)
    print(f"  result = {status}")

    # 6. chain integrity
    print("\n[6] CHAIN INTEGRITY")
    ok = engine.chain.verify()
    print(f"  verified = {ok}")
    print(f"  entries  = {len(engine.chain.entries)}")

    # 7. stats
    print("\n[7] RULE STATS")
    for rid, s in engine.get_rule_stats().items():
        print(f"  {rid:20s} w={s['weight']:.2f} T={s['triggers']} B={s['bypasses']} "
              f"X={s['blocks']} A={s['allows']} superseded={s['superseded']}")

    print("\n" + "=" * 60)
    print("Constitution evolution demo complete.")
    print("=" * 60)
