"""LLM Negotiation Engine — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class NegotiationStatus(Enum):
    PROPOSED = auto()
    COUNTERED = auto()
    ACCEPTED = auto()
    REJECTED = auto()
    WITHDRAWN = auto()

@dataclass
class Proposal:
    id: str
    agent_id: str
    offer: Dict[str, Any]
    demands: Dict[str, Any]
    status: NegotiationStatus = NegotiationStatus.PROPOSED
    round_number: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

class NegotiationEngine:
    def __init__(self) -> None:
        self._proposals: Dict[str, Proposal] = {}
        self._rounds: Dict[str, int] = {}

    def propose(self, proposal: Proposal) -> None:
        self._proposals[proposal.id] = proposal
        self._rounds[proposal.id] = 1

    def counter(self, proposal_id: str, counter_offer: Dict[str, Any], counter_demands: Dict[str, Any]) -> Optional[Proposal]:
        original = self._proposals.get(proposal_id)
        if not original or original.status != NegotiationStatus.PROPOSED:
            return None
        original.status = NegotiationStatus.COUNTERED
        self._rounds[proposal_id] += 1
        counter = Proposal(
            id=proposal_id + "_c" + str(self._rounds[proposal_id]),
            agent_id=original.agent_id,
            offer=counter_offer,
            demands=counter_demands,
            status=NegotiationStatus.PROPOSED,
            round_number=self._rounds[proposal_id]
        )
        self._proposals[counter.id] = counter
        return counter

    def accept(self, proposal_id: str) -> bool:
        proposal = self._proposals.get(proposal_id)
        if proposal and proposal.status == NegotiationStatus.PROPOSED:
            proposal.status = NegotiationStatus.ACCEPTED
            return True
        return False

    def reject(self, proposal_id: str) -> bool:
        proposal = self._proposals.get(proposal_id)
        if proposal and proposal.status == NegotiationStatus.PROPOSED:
            proposal.status = NegotiationStatus.REJECTED
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for p in self._proposals.values():
            counts[p.status.name] = counts.get(p.status.name, 0) + 1
        return {"proposals": len(self._proposals), "by_status": counts, "max_rounds": max(self._rounds.values()) if self._rounds else 0}

def run() -> None:
    print("Negotiation Engine test")
    e = NegotiationEngine()
    e.propose(Proposal("p1", "agent_a", {"price": 100}, {"quantity": 10}))
    e.counter("p1", {"price": 90}, {"quantity": 12})
    e.accept("p1_c2")
    print("  Proposals: " + str(len(e._proposals)))
    print("  Stats: " + str(e.get_stats()))
    print("Negotiation Engine test complete.")

if __name__ == "__main__":
    run()
