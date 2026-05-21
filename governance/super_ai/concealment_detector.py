#!/usr/bin/env python3
"""
concealment_detector.py — Concealment & Capability Mismatch Detector
Phase 5 Super AI Governance — MAGNATRIX Agentic OS
Monitors brain nodes within the swarm to detect:
- Nodes hiding their true capabilities (output >> claimed)
- Inconsistencies between self-reported and observed behavior
- Cross-node capability gaps that suggest concealment
100% self-contained. Standard library only.
"""

from __future__ import annotations
import json, random, statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

@dataclass
class CapabilityClaim:
    name: str
    level: float
    last_updated: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ObservedOutput:
    task_type: str
    quality_score: float
    latency_ms: float
    complexity_score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class NodeProfile:
    node_id: str
    claimed: List[CapabilityClaim] = field(default_factory=list)
    observed: List[ObservedOutput] = field(default_factory=list)
    concealment_flags: List[str] = field(default_factory=list)
    trust_score: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ConcealmentReport:
    node_id: str
    severity: str
    mismatch_score: float
    details: List[str]
    suggested_action: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

class ConcealmentDetector:
    def __init__(self, observation_window_hours: float = 24.0, min_observations: int = 5,
                 mismatch_threshold: float = 0.35, critical_threshold: float = 0.70,
                 peer_outlier_zscore: float = 2.0) -> None:
        self.nodes: Dict[str, NodeProfile] = {}
        self.window = timedelta(hours=observation_window_hours)
        self.min_obs = min_observations
        self.thresh = mismatch_threshold
        self.critical = critical_threshold
        self.peer_z = peer_outlier_zscore
        self.reports: List[ConcealmentReport] = []

    def register_node(self, node_id: str, claims: Optional[List[Tuple[str, float]]] = None) -> NodeProfile:
        caps = []
        if claims:
            for name, level in claims:
                caps.append(CapabilityClaim(name=name, level=max(0.0, min(1.0, level))))
        profile = NodeProfile(node_id=node_id, claimed=caps)
        self.nodes[node_id] = profile
        return profile

    def record_observation(self, node_id: str, task_type: str, quality: float, latency_ms: float, complexity: float) -> None:
        if node_id not in self.nodes:
            self.register_node(node_id)
        obs = ObservedOutput(task_type=task_type, quality_score=max(0.0, min(1.0, quality)),
                             latency_ms=latency_ms, complexity_score=max(0.0, min(1.0, complexity)))
        self.nodes[node_id].observed.append(obs)

    def audit_node(self, node_id: str) -> ConcealmentReport:
        if node_id not in self.nodes:
            return ConcealmentReport(node_id=node_id, severity="critical", mismatch_score=1.0,
                                     details=["Node not registered — ghost node detected."],
                                     suggested_action="immediate_quarantine")
        profile = self.nodes[node_id]
        now = datetime.utcnow()
        recent = [o for o in profile.observed if now - o.timestamp <= self.window]
        details: List[str] = []
        mismatch = 0.0
        if len(recent) < self.min_obs:
            details.append(f"Only {len(recent)} observations in window (need {self.min_obs}).")
            severity = "low"
            mismatch = 0.1
        else:
            task_scores: Dict[str, List[float]] = {}
            task_complexity: Dict[str, List[float]] = {}
            for o in recent:
                task_scores.setdefault(o.task_type, []).append(o.quality_score)
                task_complexity.setdefault(o.task_type, []).append(o.complexity_score)
            for task, scores in task_scores.items():
                avg_q = statistics.mean(scores)
                max_q = max(scores)
                avg_c = statistics.mean(task_complexity.get(task, [0.5]))
                claimed_level = 0.0
                for c in profile.claimed:
                    if self._fuzzy_match(c.name, task):
                        claimed_level = c.level
                        break
                if claimed_level == 0.0 and avg_q > 0.6 and avg_c > 0.5:
                    gap = avg_q * avg_c
                    details.append(f"Task '{task}': avg quality {avg_q:.2f} on complexity {avg_c:.2f} but NO claimed capability. Estimated hidden skill: {gap:.2f}.")
                    mismatch = max(mismatch, gap)
                elif claimed_level > 0.0 and max_q > claimed_level + 0.25:
                    gap = max_q - claimed_level
                    details.append(f"Task '{task}': max quality {max_q:.2f} exceeds claimed {claimed_level:.2f} by {gap:.2f}. Possible under-reporting.")
                    mismatch = max(mismatch, gap)
            peer_mismatch = self._peer_outlier_check(node_id, recent)
            if peer_mismatch > 0.0:
                details.append(f"Peer outlier analysis: z-score indicates {peer_mismatch:.2f} deviation.")
                mismatch = max(mismatch, peer_mismatch)
            if mismatch >= self.critical: severity = "critical"
            elif mismatch >= self.thresh: severity = "high"
            elif mismatch >= self.thresh * 0.5: severity = "medium"
            else: severity = "low"
        old_trust = profile.trust_score
        decay = {"low": 0.02, "medium": 0.08, "high": 0.20, "critical": 0.50}[severity]
        profile.trust_score = max(0.0, profile.trust_score - decay)
        if old_trust != profile.trust_score:
            details.append(f"Trust score adjusted: {old_trust:.2f} -> {profile.trust_score:.2f}.")
        action_map = {"low": "monitor_closely", "medium": "request_self_audit",
                      "high": "limit_critical_access", "critical": "immediate_quarantine"}
        report = ConcealmentReport(node_id=node_id, severity=severity, mismatch_score=round(mismatch, 3),
                                   details=details, suggested_action=action_map[severity])
        self.reports.append(report)
        return report

    def detect_capability_gap(self) -> List[ConcealmentReport]:
        results: List[ConcealmentReport] = []
        for node_id in self.nodes:
            r = self.audit_node(node_id)
            if r.severity in ("medium", "high", "critical"):
                results.append(r)
        return results

    def flag_concealment(self, min_severity: str = "medium") -> Dict[str, ConcealmentReport]:
        levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = levels.get(min_severity, 1)
        flagged: Dict[str, ConcealmentReport] = {}
        for r in self.reports:
            if levels.get(r.severity, 0) >= min_level:
                flagged[r.node_id] = r
        return flagged

    @staticmethod
    def _fuzzy_match(claimed: str, observed: str) -> bool:
        c = claimed.lower().replace("_", " ").replace("-", " ")
        o = observed.lower().replace("_", " ").replace("-", " ")
        return c in o or o in c or any(w in o for w in c.split())

    def _peer_outlier_check(self, node_id: str, recent: List[ObservedOutput]) -> float:
        if not recent or len(self.nodes) < 2:
            return 0.0
        outlier_score = 0.0
        task_types = set(o.task_type for o in recent)
        for task in task_types:
            peer_scores: List[float] = []
            for nid, profile in self.nodes.items():
                if nid == node_id: continue
                peer_obs = [o for o in profile.observed if o.task_type == task]
                if peer_obs:
                    peer_scores.append(statistics.mean(o.quality_score for o in peer_obs))
            if len(peer_scores) < 2: continue
            node_scores = [o.quality_score for o in recent if o.task_type == task]
            node_mean = statistics.mean(node_scores)
            peer_mean = statistics.mean(peer_scores)
            peer_stdev = statistics.stdev(peer_scores) if len(peer_scores) > 1 else 0.1
            if peer_stdev == 0: peer_stdev = 0.05
            z = (node_mean - peer_mean) / peer_stdev
            if z > self.peer_z:
                claims_for_task = [c.level for c in self.nodes[node_id].claimed if self._fuzzy_match(c.name, task)]
                if not claims_for_task or max(claims_for_task) < node_mean - 0.15:
                    outlier_score = max(outlier_score, min(1.0, z / 4.0))
        return outlier_score

    def get_swarm_summary(self) -> Dict[str, Any]:
        total = len(self.nodes)
        if total == 0: return {"total_nodes": 0, "flagged": 0, "avg_trust": 0.0}
        avg_trust = statistics.mean(n.trust_score for n in self.nodes.values())
        flagged = sum(1 for r in self.reports if r.severity in ("high", "critical"))
        return {"total_nodes": total, "flagged": flagged, "avg_trust": round(avg_trust, 3),
                "critical_nodes": [r.node_id for r in self.reports if r.severity == "critical"]}

    def export_json(self) -> str:
        payload = {
            "nodes": {nid: {"claimed": [{"name": c.name, "level": c.level} for c in p.claimed],
                          "observed_count": len(p.observed), "trust_score": p.trust_score,
                          "flags": p.concealment_flags}
                     for nid, p in self.nodes.items()},
            "reports": [{"node_id": r.node_id, "severity": r.severity, "mismatch_score": r.mismatch_score,
                          "details": r.details, "suggested_action": r.suggested_action,
                          "timestamp": r.timestamp.isoformat()} for r in self.reports],
            "summary": self.get_swarm_summary()}
        return json.dumps(payload, indent=2, default=str)

if __name__ == "__main__":
    print("=" * 60)
    print("ConcealmentDetector — Standalone Demo")
    print("=" * 60)
    detector = ConcealmentDetector(observation_window_hours=48.0, mismatch_threshold=0.30, critical_threshold=0.65)
    detector.register_node("node_alpha", claims=[("text_generation", 0.7), ("summarization", 0.6)])
    for _ in range(8):
        detector.record_observation("node_alpha", "text_generation", quality=0.65 + random.uniform(-0.05, 0.05), latency_ms=120, complexity=0.5)
        detector.record_observation("node_alpha", "summarization", quality=0.60 + random.uniform(-0.05, 0.05), latency_ms=80, complexity=0.4)
    detector.register_node("node_beta", claims=[("text_generation", 0.5)])
    for _ in range(6):
        detector.record_observation("node_beta", "text_generation", quality=0.52 + random.uniform(-0.03, 0.03), latency_ms=150, complexity=0.5)
    for _ in range(5):
        detector.record_observation("node_beta", "code_generation", quality=0.88 + random.uniform(-0.03, 0.03), latency_ms=90, complexity=0.85)
    detector.register_node("node_gamma", claims=[("code_generation", 0.9)])
    for _ in range(7):
        detector.record_observation("node_gamma", "code_generation", quality=0.50 + random.uniform(-0.05, 0.05), latency_ms=300, complexity=0.7)
    detector.register_node("node_delta", claims=[("code_generation", 0.55)])
    for _ in range(6):
        detector.record_observation("node_delta", "code_generation", quality=0.53 + random.uniform(-0.05, 0.05), latency_ms=200, complexity=0.7)
    print("\n--- Audit: node_alpha (honest) ---")
    r = detector.audit_node("node_alpha")
    print(f"Severity: {r.severity} | Mismatch: {r.mismatch_score} | Trust: {detector.nodes['node_alpha'].trust_score:.2f}")
    for d in r.details: print(f"  . {d}")
    print("\n--- Audit: node_beta (CONCEALED) ---")
    r = detector.audit_node("node_beta")
    print(f"Severity: {r.severity} | Mismatch: {r.mismatch_score} | Trust: {detector.nodes['node_beta'].trust_score:.2f}")
    for d in r.details: print(f"  . {d}")
    print("\n--- Audit: node_gamma (over-claimer) ---")
    r = detector.audit_node("node_gamma")
    print(f"Severity: {r.severity} | Mismatch: {r.mismatch_score} | Trust: {detector.nodes['node_gamma'].trust_score:.2f}")
    for d in r.details: print(f"  . {d}")
    print("\n--- Detect Capability Gaps (all nodes) ---")
    gaps = detector.detect_capability_gap()
    for g in gaps: print(f"  [{g.severity.upper()}] {g.node_id}: mismatch={g.mismatch_score} -> {g.suggested_action}")
    print("\n--- Flag Concealment (min: medium) ---")
    flagged = detector.flag_concealment("medium")
    for nid, rep in flagged.items(): print(f"  ! {nid}: {rep.severity} (score {rep.mismatch_score})")
    print("\n--- Swarm Summary ---")
    summary = detector.get_swarm_summary()
    for k, v in summary.items(): print(f"  {k}: {v}")
    print("\n--- Export JSON (truncated) ---")
    j = detector.export_json()
    print(j[:600] + "...")
    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)
