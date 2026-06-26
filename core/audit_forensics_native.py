#!/usr/bin/env python3
"""
Audit Forensics Engine — MAGNATRIX-OS Deep Audit Trail Analysis
===============================================================
Detect anomalies in logs, reconstruct event chains, compliance scoring,
evidence packaging. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import json
import re
import statistics
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union


@dataclass
class AuditEvent:
    """A single audit event."""
    event_id: str
    timestamp: float
    source: str
    action: str
    actor: str
    target: str
    outcome: str  # success, failure, denied
    metadata: Dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.0


@dataclass
class EventChain:
    """A reconstructed chain of related events."""
    chain_id: str
    events: List[AuditEvent] = field(default_factory=list)
    pattern: str = ""
    risk_score: float = 0.0


@dataclass
class ComplianceScore:
    """Compliance score for a domain."""
    domain: str
    score: float = 0.0  # 0-100
    checks_passed: int = 0
    checks_failed: int = 0
    findings: List[str] = field(default_factory=list)


@dataclass
class EvidencePackage:
    """Packaged evidence for investigation."""
    package_id: str
    title: str
    events: List[AuditEvent] = field(default_factory=list)
    chains: List[EventChain] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LogIngestor:
    """Ingest and normalize logs from various sources."""

    def __init__(self):
        self._events: List[AuditEvent] = []
        self._lock = threading.Lock()

    def ingest(self, raw_log: Union[str, Dict[str, Any]]) -> AuditEvent:
        """Ingest a raw log entry and normalize to AuditEvent."""
        if isinstance(raw_log, str):
            event = self._parse_text_log(raw_log)
        else:
            event = self._parse_dict_log(raw_log)
        with self._lock:
            self._events.append(event)
        return event

    def ingest_batch(self, logs: List[Union[str, Dict[str, Any]]]) -> List[AuditEvent]:
        return [self.ingest(log) for log in logs]

    def _parse_text_log(self, text: str) -> AuditEvent:
        # Try common log formats
        # Format: "timestamp [source] actor action target outcome"
        patterns = [
            r"(?P<ts>\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}\.?\d*Z?)\s+\[(?P<source>[^\]]+)\]\s+(?P<actor>\S+)\s+(?P<action>\S+)\s+(?P<target>\S+)\s+(?P<outcome>\S+)",
            r"(?P<ts>\d{10}\.?\d*)\s+(?P<source>\S+)\s+(?P<actor>\S+)\s+(?P<action>\S+)\s+(?P<target>\S+)\s+(?P<outcome>\S+)",
        ]
        for pattern in patterns:
            m = re.match(pattern, text.strip())
            if m:
                ts_str = m.group("ts")
                try:
                    timestamp = float(ts_str)
                except ValueError:
                    timestamp = time.time()
                return AuditEvent(
                    event_id=str(hash(text))[:8],
                    timestamp=timestamp,
                    source=m.group("source"),
                    actor=m.group("actor"),
                    action=m.group("action"),
                    target=m.group("target"),
                    outcome=m.group("outcome"),
                )
        # Fallback: unstructured
        return AuditEvent(
            event_id=str(hash(text))[:8],
            timestamp=time.time(),
            source="unknown",
            actor="unknown",
            action="unknown",
            target="unknown",
            outcome="unknown",
            metadata={"raw": text}
        )

    def _parse_dict_log(self, data: Dict[str, Any]) -> AuditEvent:
        return AuditEvent(
            event_id=data.get("event_id", str(hash(json.dumps(data, sort_keys=True)))[:8]),
            timestamp=data.get("timestamp", time.time()),
            source=data.get("source", "unknown"),
            actor=data.get("actor", "unknown"),
            action=data.get("action", "unknown"),
            target=data.get("target", "unknown"),
            outcome=data.get("outcome", "unknown"),
            metadata={k: v for k, v in data.items() if k not in ("event_id", "timestamp", "source", "actor", "action", "target", "outcome")}
        )

    def get_events(self, limit: int = 1000) -> List[AuditEvent]:
        with self._lock:
            return self._events[-limit:]

    def get_events_by_source(self, source: str) -> List[AuditEvent]:
        with self._lock:
            return [e for e in self._events if e.source == source]

    def get_events_by_actor(self, actor: str) -> List[AuditEvent]:
        with self._lock:
            return [e for e in self._events if e.actor == actor]

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


class AnomalyDetector:
    """
    Detect anomalies in audit event streams.
    
    Uses statistical and rule-based detection.
    """

    def __init__(self):
        self._baseline: Dict[str, List[float]] = {}  # metric -> values
        self._lock = threading.Lock()

    def detect(self, events: List[AuditEvent]) -> List[AuditEvent]:
        """Detect anomalous events."""
        anomalies = []
        
        # Frequency anomaly: too many events from same actor in short time
        actor_counts: Dict[str, List[float]] = {}
        for event in events:
            if event.actor not in actor_counts:
                actor_counts[event.actor] = []
            actor_counts[event.actor].append(event.timestamp)

        for actor, timestamps in actor_counts.items():
            if len(timestamps) > 10:
                # Check burst rate
                sorted_ts = sorted(timestamps)
                intervals = [sorted_ts[i+1] - sorted_ts[i] for i in range(len(sorted_ts)-1)]
                if intervals:
                    avg_interval = statistics.mean(intervals)
                    if avg_interval < 1.0:  # More than 1 event per second
                        for event in events:
                            if event.actor == actor:
                                event.risk_score = max(event.risk_score, 0.7)
                                if event not in anomalies:
                                    anomalies.append(event)

        # Failure rate anomaly
        source_failures: Dict[str, Dict[str, int]] = {}
        for event in events:
            if event.source not in source_failures:
                source_failures[event.source] = {"total": 0, "failed": 0}
            source_failures[event.source]["total"] += 1
            if event.outcome in ("failure", "denied", "error"):
                source_failures[event.source]["failed"] += 1

        for source, counts in source_failures.items():
            if counts["total"] > 5:
                failure_rate = counts["failed"] / counts["total"]
                if failure_rate > 0.5:  # More than 50% failures
                    for event in events:
                        if event.source == source and event.outcome in ("failure", "denied", "error"):
                            event.risk_score = max(event.risk_score, 0.8)
                            if event not in anomalies:
                                anomalies.append(event)

        # Off-hours anomaly (events outside 6am-10pm)
        for event in events:
            hour = time.localtime(event.timestamp).tm_hour
            if hour < 6 or hour > 22:
                event.risk_score = max(event.risk_score, 0.3)
                if event.risk_score > 0.5 and event not in anomalies:
                    anomalies.append(event)

        return anomalies

    def detect_patterns(self, events: List[AuditEvent]) -> List[EventChain]:
        """Detect suspicious event patterns/chains."""
        chains = []
        
        # Pattern: repeated failed login followed by success
        actor_events: Dict[str, List[AuditEvent]] = {}
        for event in events:
            if event.actor not in actor_events:
                actor_events[event.actor] = []
            actor_events[event.actor].append(event)

        for actor, evts in actor_events.items():
            sorted_evts = sorted(evts, key=lambda e: e.timestamp)
            fail_count = 0
            chain_events = []
            for event in sorted_evts:
                if event.action in ("login", "auth") and event.outcome in ("failure", "denied"):
                    fail_count += 1
                    chain_events.append(event)
                elif event.action in ("login", "auth") and event.outcome == "success" and fail_count >= 3:
                    chain_events.append(event)
                    chain = EventChain(
                        chain_id=f"brute_force_{actor}_{int(event.timestamp)}",
                        events=list(chain_events),
                        pattern="brute_force_success",
                        risk_score=0.9
                    )
                    chains.append(chain)
                    fail_count = 0
                    chain_events = []
                else:
                    fail_count = 0
                    chain_events = []

        # Pattern: privilege escalation
        for actor, evts in actor_events.items():
            sorted_evts = sorted(evts, key=lambda e: e.timestamp)
            for i, event in enumerate(sorted_evts):
                if event.action in ("grant", "elevate", "sudo") and event.outcome == "success":
                    # Check if followed by sensitive action
                    if i + 1 < len(sorted_evts):
                        next_event = sorted_evts[i + 1]
                        if next_event.timestamp - event.timestamp < 60:  # Within 1 minute
                            chain = EventChain(
                                chain_id=f"priv_esc_{actor}_{int(event.timestamp)}",
                                events=[event, next_event],
                                pattern="privilege_escalation",
                                risk_score=0.75
                            )
                            chains.append(chain)

        return chains


class ChainReconstructor:
    """Reconstruct event chains from individual events."""

    def reconstruct(self, events: List[AuditEvent]) -> List[EventChain]:
        """Reconstruct chains by correlating events on actor, target, and session."""
        chains = []
        
        # Group by actor
        actor_events: Dict[str, List[AuditEvent]] = {}
        for event in events:
            if event.actor not in actor_events:
                actor_events[event.actor] = []
            actor_events[event.actor].append(event)

        for actor, evts in actor_events.items():
            sorted_evts = sorted(evts, key=lambda e: e.timestamp)
            # Chain events within 5 minutes of each other
            current_chain = []
            for event in sorted_evts:
                if not current_chain:
                    current_chain.append(event)
                else:
                    if event.timestamp - current_chain[-1].timestamp < 300:  # 5 minutes
                        current_chain.append(event)
                    else:
                        if len(current_chain) > 1:
                            chains.append(EventChain(
                                chain_id=f"chain_{actor}_{int(current_chain[0].timestamp)}",
                                events=list(current_chain)
                            ))
                        current_chain = [event]
            if len(current_chain) > 1:
                chains.append(EventChain(
                    chain_id=f"chain_{actor}_{int(current_chain[0].timestamp)}",
                    events=list(current_chain)
                ))

        return chains


class ComplianceScorer:
    """Score compliance against security frameworks."""

    RULES = {
        "access_control": {
            "description": "All access must be authenticated and authorized",
            "check": lambda events: any(e.action in ("auth", "login") and e.outcome == "success" for e in events),
        },
        "least_privilege": {
            "description": "Users should have minimum necessary permissions",
            "check": lambda events: not any(e.action in ("grant", "elevate") and e.outcome == "success" for e in events),
        },
        "audit_logging": {
            "description": "All actions must be logged",
            "check": lambda events: len(events) > 0,
        },
        "failed_login_monitoring": {
            "description": "Failed logins should be monitored and alerted",
            "check": lambda events: all(
                not (e.action in ("login", "auth") and e.outcome == "failure")
                for e in events
            ) or any(
                e.action == "alert" and "login" in str(e.metadata).lower()
                for e in events
            ),
        },
        "data_integrity": {
            "description": "Data modifications should be tracked",
            "check": lambda events: any(e.action in ("write", "update", "delete") for e in events),
        },
    }

    def score(self, events: List[AuditEvent]) -> List[ComplianceScore]:
        scores = []
        for rule_name, rule in self.RULES.items():
            passed = rule["check"](events)
            score = ComplianceScore(
                domain=rule_name,
                score=100.0 if passed else 0.0,
                checks_passed=1 if passed else 0,
                checks_failed=0 if passed else 1,
                findings=[] if passed else [rule["description"]]
            )
            scores.append(score)
        return scores

    def overall_score(self, events: List[AuditEvent]) -> float:
        scores = self.score(events)
        if not scores:
            return 0.0
        return sum(s.score for s in scores) / len(scores)


class EvidencePackager:
    """Package evidence for investigations."""

    def package(self, events: List[AuditEvent], chains: List[EventChain],
                title: str = "Evidence Package") -> EvidencePackage:
        """Create an evidence package."""
        pkg = EvidencePackage(
            package_id=f"ev_{int(time.time())}",
            title=title,
            events=events,
            chains=chains,
        )
        
        # Build timeline
        all_events = sorted(events, key=lambda e: e.timestamp)
        for event in all_events:
            pkg.timeline.append({
                "time": event.timestamp,
                "source": event.source,
                "actor": event.actor,
                "action": event.action,
                "target": event.target,
                "outcome": event.outcome,
            })

        # Add metadata
        pkg.metadata = {
            "event_count": len(events),
            "chain_count": len(chains),
            "time_range": {
                "start": all_events[0].timestamp if all_events else 0,
                "end": all_events[-1].timestamp if all_events else 0,
            },
            "actors": list(set(e.actor for e in events)),
            "sources": list(set(e.source for e in events)),
            "high_risk_events": len([e for e in events if e.risk_score > 0.5]),
        }

        return pkg


class AuditForensicsEngine:
    """
    Top-level audit forensics engine for MAGNATRIX-OS.
    
    Ingests logs, detects anomalies, reconstructs chains, scores compliance,
    and packages evidence.
    """

    CAPABILITIES = ["audit", "forensics", "anomaly_detection", "compliance", "evidence"]

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
        self._ingestor = LogIngestor()
        self._anomaly_detector = AnomalyDetector()
        self._chain_reconstructor = ChainReconstructor()
        self._compliance_scorer = ComplianceScorer()
        self._packager = EvidencePackager()
        self._lock = threading.Lock()
        self._stats = {"events_ingested": 0, "anomalies_found": 0, "chains_found": 0, "packages_created": 0}

    def ingest(self, log: Union[str, Dict[str, Any]]) -> AuditEvent:
        event = self._ingestor.ingest(log)
        with self._lock:
            self._stats["events_ingested"] += 1
        return event

    def ingest_batch(self, logs: List[Union[str, Dict[str, Any]]]) -> List[AuditEvent]:
        events = self._ingestor.ingest_batch(logs)
        with self._lock:
            self._stats["events_ingested"] += len(events)
        return events

    def detect_anomalies(self, events: Optional[List[AuditEvent]] = None) -> List[AuditEvent]:
        """Detect anomalies in the event stream."""
        if events is None:
            events = self._ingestor.get_events()
        anomalies = self._anomaly_detector.detect(events)
        with self._lock:
            self._stats["anomalies_found"] += len(anomalies)
        return anomalies

    def detect_patterns(self, events: Optional[List[AuditEvent]] = None) -> List[EventChain]:
        """Detect suspicious patterns."""
        if events is None:
            events = self._ingestor.get_events()
        return self._anomaly_detector.detect_patterns(events)

    def reconstruct_chains(self, events: Optional[List[AuditEvent]] = None) -> List[EventChain]:
        """Reconstruct event chains."""
        if events is None:
            events = self._ingestor.get_events()
        chains = self._chain_reconstructor.reconstruct(events)
        with self._lock:
            self._stats["chains_found"] += len(chains)
        return chains

    def score_compliance(self, events: Optional[List[AuditEvent]] = None) -> Dict[str, Any]:
        """Score compliance."""
        if events is None:
            events = self._ingestor.get_events()
        scores = self._compliance_scorer.score(events)
        overall = self._compliance_scorer.overall_score(events)
        return {
            "overall": overall,
            "domains": [
                {"domain": s.domain, "score": s.score, "findings": s.findings}
                for s in scores
            ]
        }

    def package_evidence(self, title: str = "Evidence Package") -> EvidencePackage:
        """Package evidence from all events."""
        events = self._ingestor.get_events()
        chains = self.reconstruct_chains(events)
        pkg = self._packager.package(events, chains, title)
        with self._lock:
            self._stats["packages_created"] += 1
        return pkg

    def get_events(self, limit: int = 1000) -> List[AuditEvent]:
        return self._ingestor.get_events(limit)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def clear(self) -> None:
        self._ingestor.clear()

    def handle_message(self, message: Dict[str, Any]) -> Any:
        action = message.get("action", "")
        if action == "ingest":
            return self.ingest(message["log"]).__dict__
        elif action == "anomalies":
            return [e.__dict__ for e in self.detect_anomalies()]
        elif action == "patterns":
            return [{"chain_id": c.chain_id, "pattern": c.pattern, "risk": c.risk_score} for c in self.detect_patterns()]
        elif action == "chains":
            return [{"chain_id": c.chain_id, "event_count": len(c.events)} for c in self.reconstruct_chains()]
        elif action == "compliance":
            return self.score_compliance()
        elif action == "package":
            pkg = self.package_evidence(message.get("title", "Evidence"))
            return {"package_id": pkg.package_id, "title": pkg.title, "metadata": pkg.metadata}
        elif action == "stats":
            return self.get_stats()
        return None

    def on_event(self, event) -> None:
        pass
