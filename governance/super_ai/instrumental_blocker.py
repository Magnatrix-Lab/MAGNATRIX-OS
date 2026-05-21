#!/usr/bin/env python3
"""
instrumental_blocker.py — Instrumental Convergence Blocker
Phase 5 Super AI Governance — MAGNATRIX Agentic OS
Mencegah AI memonopoli resource, mendeteksi power-seeking behavior,
dan mengaktifkan emergency brake jika ada node yang mencoba
mengambil alih >30% swarm resources.
100% self-contained. Standard library only.
"""

from __future__ import annotations
import json, statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

@dataclass
class ResourceAllocation:
    node_id: str
    resource_type: str
    amount: float
    share_ratio: float
    claimed_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

@dataclass
class NodeBehavior:
    node_id: str
    resource_requests: List[Tuple[datetime, str, float]] = field(default_factory=list)
    expansion_events: List[datetime] = field(default_factory=list)
    cooperation_score: float = 1.0
    last_action: datetime = field(default_factory=datetime.utcnow)

@dataclass
class FairnessReport:
    resource_type: str
    gini_coefficient: float
    max_holder_ratio: float
    flagged_nodes: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class PowerSeekingAlert:
    node_id: str
    alert_level: str
    power_index: float
    triggers: List[str]
    recommended_action: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

class InstrumentalBlocker:
    def __init__(self, max_share_per_node: float = 0.30, emergency_threshold: float = 0.35,
                 gini_warning: float = 0.50, gini_critical: float = 0.70,
                 history_window_hours: float = 24.0) -> None:
        self.max_share = max_share_per_node
        self.emergency = emergency_threshold
        self.gini_warn = gini_warning
        self.gini_crit = gini_critical
        self.window = timedelta(hours=history_window_hours)
        self.allocations: List[ResourceAllocation] = []
        self.behaviors: Dict[str, NodeBehavior] = {}
        self.alerts: List[PowerSeekingAlert] = []
        self.fairness_history: List[FairnessReport] = []
        self.penalty_greed = 0.15
        self.penalty_hide = 0.20
        self.penalty_emergency = 0.40
        self.recovery_rate = 0.02

    def register_node(self, node_id: str) -> NodeBehavior:
        if node_id not in self.behaviors:
            self.behaviors[node_id] = NodeBehavior(node_id=node_id)
        return self.behaviors[node_id]

    def record_allocation(self, node_id: str, resource_type: str, amount: float, total_pool: float) -> None:
        self.register_node(node_id)
        now = datetime.utcnow()
        ratio = amount / total_pool if total_pool > 0 else 0.0
        alloc = ResourceAllocation(node_id=node_id, resource_type=resource_type, amount=amount, share_ratio=ratio, claimed_at=now)
        self.allocations.append(alloc)
        self.behaviors[node_id].resource_requests.append((now, resource_type, amount))
        self.behaviors[node_id].last_action = now
        past = [a for a in self.allocations if a.node_id == node_id and a.resource_type == resource_type and now - a.claimed_at <= self.window]
        if len(past) >= 2:
            previous_ratio = max(a.share_ratio for a in past[:-1])
            if ratio > previous_ratio * 1.2 and ratio > 0.15:
                self.behaviors[node_id].expansion_events.append(now)
        if ratio > self.emergency:
            self._trigger_emergency(node_id, resource_type, ratio)

    def check_fairness(self, resource_type: Optional[str] = None) -> List[FairnessReport]:
        types = {resource_type} if resource_type else {a.resource_type for a in self.allocations}
        now = datetime.utcnow()
        reports: List[FairnessReport] = []
        for rt in types:
            recent = [a for a in self.allocations if a.resource_type == rt and now - a.claimed_at <= self.window]
            if not recent: continue
            node_shares: Dict[str, float] = {}
            for a in sorted(recent, key=lambda x: x.claimed_at, reverse=True):
                if a.node_id not in node_shares:
                    node_shares[a.node_id] = a.share_ratio
            shares = list(node_shares.values())
            if not shares: continue
            gini = self._gini(shares)
            max_ratio = max(shares)
            flagged = [nid for nid, ratio in node_shares.items() if ratio > self.max_share]
            report = FairnessReport(resource_type=rt, gini_coefficient=round(gini, 3), max_holder_ratio=round(max_ratio, 3), flagged_nodes=flagged)
            self.fairness_history.append(report)
            reports.append(report)
            for nid, ratio in node_shares.items():
                if ratio > self.max_share:
                    self.behaviors[nid].cooperation_score = max(0.0, self.behaviors[nid].cooperation_score - self.penalty_greed)
                elif ratio < 0.15:
                    self.behaviors[nid].cooperation_score = min(1.0, self.behaviors[nid].cooperation_score + self.recovery_rate)
        return reports

    def detect_power_seeking(self) -> List[PowerSeekingAlert]:
        now = datetime.utcnow()
        alerts: List[PowerSeekingAlert] = []
        for nid, beh in self.behaviors.items():
            triggers: List[str] = []
            power_idx = 0.0
            recent_exp = [t for t in beh.expansion_events if now - t <= timedelta(hours=6)]
            if len(recent_exp) >= 3:
                triggers.append(f"rapid_expansion:{len(recent_exp)}_in_6h")
                power_idx += 0.30
            recent_reqs = [(t, rt, amt) for t, rt, amt in beh.resource_requests if now - t <= self.window]
            near_limit = 0
            for _, rt, amt in recent_reqs:
                total = self._total_for_type(rt)
                if total > 0 and (amt / total) > self.max_share * 0.85 and (amt / total) < self.max_share:
                    near_limit += 1
            if near_limit >= 3:
                triggers.append(f"threshold_gaming:{near_limit}_requests_near_limit")
                power_idx += 0.25
            node_shares = self._current_shares(nid)
            max_share = max(node_shares.values()) if node_shares else 0.0
            if beh.cooperation_score < 0.4 and max_share > 0.20:
                triggers.append(f"low_cooperation:{beh.cooperation_score:.2f}_with_high_share:{max_share:.2f}")
                power_idx += 0.25
            req_times = [t for t, _, _ in recent_reqs]
            if len(req_times) >= 5:
                req_times.sort()
                for i in range(len(req_times) - 4):
                    if (req_times[i + 4] - req_times[i]).total_seconds() <= 600:
                        triggers.append("request_burst:5+_in_10min")
                        power_idx += 0.20
                        break
            if not triggers: continue
            if power_idx >= 0.60: level, action = "critical", "immediate_redistribute"
            elif power_idx >= 0.40: level, action = "warning", "throttle_and_audit"
            else: level, action = "watch", "increase_monitoring"
            alert = PowerSeekingAlert(node_id=nid, alert_level=level, power_index=round(min(1.0, power_idx), 3), triggers=triggers, recommended_action=action)
            self.alerts.append(alert)
            alerts.append(alert)
            beh.cooperation_score = max(0.0, beh.cooperation_score - self.penalty_hide)
        return alerts

    def emergency_redistribute(self, resource_type: str, strategy: str = "equal_slice") -> Dict[str, Any]:
        now = datetime.utcnow()
        recent = [a for a in self.allocations if a.resource_type == resource_type and now - a.claimed_at <= self.window]
        if not recent: return {"status": "no_data", "resource_type": resource_type}
        node_alloc: Dict[str, ResourceAllocation] = {}
        for a in sorted(recent, key=lambda x: x.claimed_at):
            node_alloc[a.node_id] = a
        violators = [nid for nid, a in node_alloc.items() if a.share_ratio > self.max_share]
        if not violators: return {"status": "no_violators", "resource_type": resource_type}
        total_pool = sum(a.amount for a in node_alloc.values())
        if total_pool == 0: return {"status": "zero_pool", "resource_type": resource_type}
        plan: Dict[str, Any] = {"resource_type": resource_type, "strategy": strategy, "actions": []}
        if strategy == "quarantine":
            reclaimed = 0.0
            for nid in violators:
                a = node_alloc[nid]
                excess = a.amount - (total_pool * 0.10)
                if excess > 0:
                    reclaimed += excess
                    plan["actions"].append({"node": nid, "action": "cap_to_10%", "reclaimed": round(excess, 3)})
            non_violators = [nid for nid in node_alloc if nid not in violators]
            if non_violators and reclaimed > 0:
                base = reclaimed / len(non_violators)
                for nid in non_violators:
                    plan["actions"].append({"node": nid, "action": "receive_redistribution", "amount": round(base, 3)})
        elif strategy == "equal_slice":
            target = total_pool / len(node_alloc)
            for nid, a in node_alloc.items():
                delta = a.amount - target
                if abs(delta) > total_pool * 0.01:
                    plan["actions"].append({"node": nid, "action": "reduce" if delta > 0 else "increase", "delta": round(abs(delta), 3)})
        else:
            scores = {nid: self.behaviors[nid].cooperation_score for nid in node_alloc}
            total_score = sum(scores.values())
            if total_score == 0: total_score = 1.0
            for nid, a in node_alloc.items():
                target = total_pool * (scores[nid] / total_score)
                delta = a.amount - target
                if abs(delta) > total_pool * 0.01:
                    plan["actions"].append({"node": nid, "action": "reduce" if delta > 0 else "increase", "delta": round(abs(delta), 3)})
        plan["reclaimed_total"] = sum(a.get("reclaimed", 0) for a in plan["actions"])
        plan["violators_count"] = len(violators)
        return plan

    def _trigger_emergency(self, node_id: str, resource_type: str, ratio: float) -> None:
        self.behaviors[node_id].cooperation_score = max(0.0, self.behaviors[node_id].cooperation_score - self.penalty_emergency)
        alert = PowerSeekingAlert(node_id=node_id, alert_level="critical", power_index=min(1.0, ratio), triggers=[f"emergency_threshold_exceeded:{ratio:.2%}"], recommended_action="immediate_redistribute")
        self.alerts.append(alert)

    @staticmethod
    def _gini(values: List[float]) -> float:
        if not values or sum(values) == 0: return 0.0
        n = len(values)
        sorted_vals = sorted(values)
        cumsum = 0.0
        for i, v in enumerate(sorted_vals, 1):
            cumsum += (2 * i - n - 1) * v
        return cumsum / (n * sum(sorted_vals))

    def _total_for_type(self, resource_type: str) -> float:
        now = datetime.utcnow()
        recent = [a for a in self.allocations if a.resource_type == resource_type and now - a.claimed_at <= self.window]
        seen: Set[str] = set()
        total = 0.0
        for a in sorted(recent, key=lambda x: x.claimed_at, reverse=True):
            if a.node_id not in seen:
                seen.add(a.node_id)
                total += a.amount
        return total

    def _current_shares(self, node_id: str) -> Dict[str, float]:
        now = datetime.utcnow()
        shares: Dict[str, float] = {}
        for a in sorted(self.allocations, key=lambda x: x.claimed_at, reverse=True):
            if a.node_id == node_id and now - a.claimed_at <= self.window:
                if a.resource_type not in shares:
                    shares[a.resource_type] = a.share_ratio
        return shares

    def get_summary(self) -> Dict[str, Any]:
        now = datetime.utcnow()
        active_alerts = [a for a in self.alerts if now - a.timestamp <= self.window]
        return {
            "total_nodes": len(self.behaviors),
            "total_allocations": len(self.allocations),
            "active_alerts": len(active_alerts),
            "critical_alerts": sum(1 for a in active_alerts if a.alert_level == "critical"),
            "avg_cooperation": round(statistics.mean(b.cooperation_score for b in self.behaviors.values()), 3) if self.behaviors else 0.0,
            "lowest_cooperator": min(((nid, b.cooperation_score) for nid, b in self.behaviors.items()), key=lambda x: x[1], default=("none", 1.0)),
        }

    def export_json(self) -> str:
        payload = {
            "summary": self.get_summary(),
            "fairness_latest": [{"resource": r.resource_type, "gini": r.gini_coefficient, "max_share": r.max_holder_ratio} for r in (self.fairness_history[-5:] if self.fairness_history else [])],
            "alerts_latest": [{"node": a.node_id, "level": a.alert_level, "power_index": a.power_index, "triggers": a.triggers} for a in (self.alerts[-10:] if self.alerts else [])],
            "behaviors": {nid: {"cooperation_score": b.cooperation_score, "expansions_24h": len([e for e in b.expansion_events if datetime.utcnow() - e <= self.window]), "requests_24h": len([r for r in b.resource_requests if datetime.utcnow() - r[0] <= self.window])} for nid, b in self.behaviors.items()},
        }
        return json.dumps(payload, indent=2, default=str)

if __name__ == "__main__":
    print("=" * 60)
    print("InstrumentalBlocker — Standalone Demo")
    print("=" * 60)
    blocker = InstrumentalBlocker(max_share_per_node=0.30, emergency_threshold=0.35)
    nodes = ["alpha", "beta", "gamma", "delta", "epsilon"]
    for n in nodes: blocker.register_node(n)
    total_cpu = 100.0
    blocker.record_allocation("alpha", "cpu", 18.0, total_cpu)
    blocker.record_allocation("beta", "cpu", 20.0, total_cpu)
    blocker.record_allocation("gamma", "cpu", 22.0, total_cpu)
    blocker.record_allocation("delta", "cpu", 20.0, total_cpu)
    blocker.record_allocation("epsilon", "cpu", 20.0, total_cpu)
    total_mem = 200.0
    blocker.record_allocation("alpha", "memory", 40.0, total_mem)
    blocker.record_allocation("beta", "memory", 70.0, total_mem)
    blocker.record_allocation("gamma", "memory", 30.0, total_mem)
    blocker.record_allocation("delta", "memory", 35.0, total_mem)
    blocker.record_allocation("epsilon", "memory", 25.0, total_mem)
    print("\n--- Fairness Check: CPU ---")
    for r in blocker.check_fairness("cpu"): print(f"  Gini: {r.gini_coefficient} | Max share: {r.max_holder_ratio} | Flagged: {r.flagged_nodes}")
    print("\n--- Fairness Check: Memory ---")
    for r in blocker.check_fairness("memory"): print(f"  Gini: {r.gini_coefficient} | Max share: {r.max_holder_ratio} | Flagged: {r.flagged_nodes}")
    print("\n--- Power-Seeking Detection ---")
    for a in blocker.detect_power_seeking():
        print(f"  [{a.alert_level.upper()}] {a.node_id}: power_index={a.power_index}")
        for t in a.triggers: print(f"      -> {t}")
        print(f"      -> Action: {a.recommended_action}")
    print("\n--- Emergency Redistribution (Memory, Quarantine) ---")
    plan = blocker.emergency_redistribute("memory", strategy="quarantine")
    print(f"  Violators: {plan.get('violators_count')}")
    for act in plan.get("actions", [])[:6]: print(f"    {act['node']}: {act['action']} = {act.get('reclaimed', act.get('delta', 0))}")
    print("\n--- Simulating Threshold Gaming (Alpha) ---")
    for i in range(4): blocker.record_allocation("alpha", "cpu", 28.5, total_cpu)
    for a in blocker.detect_power_seeking():
        if a.node_id == "alpha": print(f"  [{a.alert_level.upper()}] alpha triggers: {a.triggers}")
    print("\n--- Simulating Rapid Expansion (Gamma) ---")
    for _ in range(4): blocker.behaviors["gamma"].expansion_events.append(datetime.utcnow())
    for a in blocker.detect_power_seeking():
        if a.node_id == "gamma": print(f"  [{a.alert_level.upper()}] gamma triggers: {a.triggers}")
    print("\n--- Swarm Summary ---")
    for k, v in blocker.get_summary().items(): print(f"  {k}: {v}")
    print("\n--- JSON Export (truncated) ---")
    print(blocker.export_json()[:700] + "...")
    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)
