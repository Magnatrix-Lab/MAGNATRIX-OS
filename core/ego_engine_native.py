#!/usr/bin/env python3
"""
Ego Engine for MAGNATRIX-OS (GENesis-AGI inspired)
Cognitive engine: autonomous decision-making, proposals, signals, cadence, verification.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import random
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class SignalType(enum.Enum):
    USER_MESSAGE = "user_message"
    SYSTEM_ALERT = "system_alert"
    MEMORY_TRIGGER = "memory_trigger"
    GOAL_STALENESS = "goal_staleness"
    FOLLOW_UP = "follow_up"
    PROACTIVE = "proactive"
    SCHEDULED = "scheduled"
    CAPABILITY_AVAILABLE = "capability_available"


class ProposalType(enum.Enum):
    DIRECT_RESPONSE = "direct_response"
    TOOL_USE = "tool_use"
    RESEARCH = "research"
    CONTENT_CREATE = "content_create"
    OUTREACH = "outreach"
    LEARNING = "learning"
    GOAL_DECOMPOSE = "goal_decompose"
    REFLECTION = "reflection"
    WAIT = "wait"


@dataclasses.dataclass
class Signal:
    id: str
    signal_type: SignalType
    source: str
    content: str
    priority: int = 5  # 1-10, lower = more urgent
    timestamp: float = dataclasses.field(default_factory=time.time)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    consumed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.signal_type.value,
            'source': self.source,
            'content': self.content[:100],
            'priority': self.priority,
            'timestamp': self.timestamp,
        }


@dataclasses.dataclass
class Proposal:
    id: str
    proposal_type: ProposalType
    description: str
    confidence: float  # 0.0-1.0
    estimated_cost: float  # estimated tokens/cost
    dependencies: List[str] = dataclasses.field(default_factory=list)
    rationale: str = ""
    approved: bool = False
    executed: bool = False
    result: Optional[str] = None
    timestamp: float = dataclasses.field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.proposal_type.value,
            'description': self.description[:100],
            'confidence': self.confidence,
            'cost': self.estimated_cost,
            'approved': self.approved,
            'executed': self.executed,
        }


@dataclasses.dataclass
class Intention:
    id: str
    description: str
    priority: int
    status: str = "pending"  # pending, active, completed, failed
    created_at: float = dataclasses.field(default_factory=time.time)
    deadline: Optional[float] = None
    parent_id: Optional[str] = None
    subgoals: List[str] = dataclasses.field(default_factory=list)


class EgoCadence:
    """Cadence engine: manages the ego's operational rhythm."""

    def __init__(self) -> None:
        self._cycle_count: int = 0
        self._last_cycle: float = 0
        self._cycle_interval: float = 1.0  # seconds between cycles
        self._active: bool = False

    def should_tick(self) -> bool:
        now = time.time()
        if now - self._last_cycle >= self._cycle_interval:
            self._last_cycle = now
            self._cycle_count += 1
            return True
        return False

    def get_cycle_info(self) -> Dict[str, Any]:
        return {
            'cycle_count': self._cycle_count,
            'last_cycle': self._last_cycle,
            'interval': self._cycle_interval,
            'active': self._active,
        }


class EgoSignals:
    """Signal collection and management."""

    def __init__(self) -> None:
        self._signals: List[Signal] = []
        self._lock = threading.Lock()
        self._handlers: Dict[SignalType, List[Callable[[Signal], None]]] = {}

    def emit(self, signal: Signal) -> None:
        with self._lock:
            self._signals.append(signal)

        # Notify handlers
        for handler in self._handlers.get(signal.signal_type, []):
            try:
                handler(signal)
            except Exception:
                pass

    def on(self, signal_type: SignalType, handler: Callable[[Signal], None]) -> None:
        self._handlers.setdefault(signal_type, []).append(handler)

    def consume(self, signal_type: Optional[SignalType] = None, n: int = 1) -> List[Signal]:
        with self._lock:
            if signal_type:
                matching = [s for s in self._signals if s.signal_type == signal_type and not s.consumed]
            else:
                matching = [s for s in self._signals if not s.consumed]

            matching.sort(key=lambda s: s.priority)
            consumed = matching[:n]
            for s in consumed:
                s.consumed = True
            return consumed

    def get_unconsumed(self) -> List[Signal]:
        with self._lock:
            return [s for s in self._signals if not s.consumed]


class EgoProposals:
    """Proposal generation and evaluation."""

    def __init__(self) -> None:
        self._proposals: Dict[str, Proposal] = {}
        self._lock = threading.Lock()

    def generate(self, signals: List[Signal], context: Dict[str, Any]) -> List[Proposal]:
        """Generate proposals from signals."""
        proposals = []

        for signal in signals:
            if signal.signal_type == SignalType.USER_MESSAGE:
                proposals.append(Proposal(
                    id=f"prop_{int(time.time())}_{random.randint(1000,9999)}",
                    proposal_type=ProposalType.DIRECT_RESPONSE,
                    description=f"Respond to user: {signal.content[:50]}",
                    confidence=0.9,
                    estimated_cost=0.5,
                    rationale="User expects direct response",
                ))
            elif signal.signal_type == SignalType.GOAL_STALENESS:
                proposals.append(Proposal(
                    id=f"prop_{int(time.time())}_{random.randint(1000,9999)}",
                    proposal_type=ProposalType.GOAL_DECOMPOSE,
                    description="Decompose stale goal into subgoals",
                    confidence=0.7,
                    estimated_cost=1.0,
                    rationale="Goal needs refresh",
                ))
            elif signal.signal_type == SignalType.PROACTIVE:
                proposals.append(Proposal(
                    id=f"prop_{int(time.time())}_{random.randint(1000,9999)}",
                    proposal_type=ProposalType.RESEARCH,
                    description=f"Proactive research: {signal.content[:50]}",
                    confidence=0.6,
                    estimated_cost=2.0,
                    rationale="Proactive opportunity detected",
                ))

        with self._lock:
            for p in proposals:
                self._proposals[p.id] = p

        return proposals

    def approve(self, proposal_id: str) -> bool:
        with self._lock:
            if proposal_id in self._proposals:
                self._proposals[proposal_id].approved = True
                return True
            return False

    def get_approved(self) -> List[Proposal]:
        with self._lock:
            return [p for p in self._proposals.values() if p.approved and not p.executed]

    def mark_executed(self, proposal_id: str, result: str) -> None:
        with self._lock:
            if proposal_id in self._proposals:
                self._proposals[proposal_id].executed = True
                self._proposals[proposal_id].result = result


class EgoIntentions:
    """Intention and goal management."""

    def __init__(self) -> None:
        self._intentions: Dict[str, Intention] = {}
        self._active: Optional[str] = None

    def create(self, description: str, priority: int = 5, parent_id: Optional[str] = None) -> Intention:
        intention = Intention(
            id=f"int_{int(time.time())}_{random.randint(1000,9999)}",
            description=description,
            priority=priority,
            parent_id=parent_id,
        )
        self._intentions[intention.id] = intention
        return intention

    def decompose(self, intention_id: str, subgoals: List[str]) -> List[Intention]:
        parent = self._intentions.get(intention_id)
        if not parent:
            return []

        created = []
        for sg in subgoals:
            sub = self.create(sg, priority=parent.priority + 1, parent_id=intention_id)
            parent.subgoals.append(sub.id)
            created.append(sub)
        return created

    def get_active(self) -> Optional[Intention]:
        if self._active and self._active in self._intentions:
            return self._intentions[self._active]
        return None

    def activate(self, intention_id: str) -> bool:
        if intention_id in self._intentions:
            self._active = intention_id
            self._intentions[intention_id].status = "active"
            return True
        return False

    def complete(self, intention_id: str) -> None:
        if intention_id in self._intentions:
            self._intentions[intention_id].status = "completed"

    def list_pending(self) -> List[Intention]:
        return [i for i in self._intentions.values() if i.status == "pending"]


class EgoVerification:
    """Proposal verification and integrity checking."""

    def __init__(self) -> None:
        self._verifications: List[Dict[str, Any]] = []

    def verify(self, proposal: Proposal) -> Dict[str, Any]:
        checks = {
            'confidence_sufficient': proposal.confidence >= 0.5,
            'cost_reasonable': proposal.estimated_cost <= 5.0,
            'description_clear': len(proposal.description) > 10,
            'has_rationale': len(proposal.rationale) > 0,
        }
        passed = all(checks.values())
        result = {
            'proposal_id': proposal.id,
            'passed': passed,
            'checks': checks,
            'timestamp': time.time(),
        }
        self._verifications.append(result)
        return result

    def get_verification_rate(self) -> float:
        if not self._verifications:
            return 1.0
        passed = sum(1 for v in self._verifications if v['passed'])
        return passed / len(self._verifications)


class EgoEngine:
    """Main Ego cognitive engine."""

    def __init__(self) -> None:
        self.cadence = EgoCadence()
        self.signals = EgoSignals()
        self.proposals = EgoProposals()
        self.intentions = EgoIntentions()
        self.verification = EgoVerification()
        self._capabilities: Set[str] = set()
        self._state: Dict[str, Any] = {
            'focus': 'idle',
            'mood': 'neutral',
            'energy': 1.0,
        }
        self._running: bool = False

    def add_capability(self, capability: str) -> None:
        self._capabilities.add(capability)

    def get_capabilities(self) -> Set[str]:
        return self._capabilities

    def tick(self) -> Dict[str, Any]:
        """Single ego cycle."""
        if not self.cadence.should_tick():
            return {'action': 'wait'}

        # 1. Consume signals
        signals = self.signals.consume(n=5)

        # 2. Generate proposals
        proposals = self.proposals.generate(signals, self._state)

        # 3. Verify and approve
        approved = []
        for p in proposals:
            v = self.verification.verify(p)
            if v['passed'] and p.confidence >= 0.6:
                self.proposals.approve(p.id)
                approved.append(p)

        # 4. Execute approved proposals
        executed = []
        for p in approved[:3]:  # Max 3 per cycle
            # Simulate execution
            self.proposals.mark_executed(p.id, f"Executed: {p.description}")
            executed.append(p)

        return {
            'cycle': self.cadence.get_cycle_info()['cycle_count'],
            'signals_consumed': len(signals),
            'proposals_generated': len(proposals),
            'proposals_approved': len(approved),
            'proposals_executed': len(executed),
            'state': self._state,
        }

    def run(self, cycles: int = 10) -> List[Dict[str, Any]]:
        """Run ego for N cycles."""
        results = []
        for _ in range(cycles):
            result = self.tick()
            results.append(result)
            if result['proposals_executed'] > 0:
                time.sleep(0.1)
        return results

    def get_status(self) -> Dict[str, Any]:
        return {
            'cycle_count': self.cadence.get_cycle_info()['cycle_count'],
            'capabilities': list(self._capabilities),
            'unconsumed_signals': len(self.signals.get_unconsumed()),
            'pending_proposals': len(self.proposals.get_approved()),
            'pending_intentions': len(self.intentions.list_pending()),
            'verification_rate': self.verification.get_verification_rate(),
            'state': self._state,
        }


def _demo() -> None:
    print("=== Ego Engine Demo (GENesis-AGI inspired) ===\n")

    ego = EgoEngine()
    ego.add_capability('conversation')
    ego.add_capability('research')
    ego.add_capability('content_creation')

    # Emit signals
    ego.signals.emit(Signal(id='s1', signal_type=SignalType.USER_MESSAGE, source='user', content='Hello, how are you?', priority=2))
    ego.signals.emit(Signal(id='s2', signal_type=SignalType.GOAL_STALENESS, source='system', content='Goal "learn_python" stale for 5 days', priority=4))
    ego.signals.emit(Signal(id='s3', signal_type=SignalType.PROACTIVE, source='awareness', content='User mentioned AI safety', priority=6))

    # Run ego
    print("--- Running 5 cycles ---")
    results = ego.run(cycles=5)
    for r in results:
        if r['proposals_generated'] > 0:
            print(f"Cycle {r['cycle']}: {r['signals_consumed']} signals, {r['proposals_generated']} proposals, {r['proposals_executed']} executed")

    print(f"\n--- Status ---")
    status = ego.get_status()
    print(f"Cycles: {status['cycle_count']}")
    print(f"Capabilities: {status['capabilities']}")
    print(f"Verification rate: {status['verification_rate']:.1%}")

    # Create intention
    intention = ego.intentions.create("Learn about AI safety", priority=3)
    print(f"\nIntention created: {intention.id}")

    subgoals = ego.intentions.decompose(intention.id, ["Read papers", "Watch videos", "Write summary"])
    print(f"Decomposed into {len(subgoals)} subgoals")

    print("\n=== Ego Engine Demo Complete ===")


if __name__ == '__main__':
    _demo()
