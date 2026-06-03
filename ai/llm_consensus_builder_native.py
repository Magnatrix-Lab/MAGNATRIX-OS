"""LLM Consensus Builder — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class VoteType(Enum):
    YES = auto()
    NO = auto()
    ABSTAIN = auto()

@dataclass
class Vote:
    agent_id: str
    vote_type: VoteType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ConsensusBuilder:
    def __init__(self, threshold: float = 0.66) -> None:
        self.threshold = threshold
        self._votes: Dict[str, List[Vote]] = {}

    def add_vote(self, topic_id: str, vote: Vote) -> None:
        if topic_id not in self._votes:
            self._votes[topic_id] = []
        self._votes[topic_id].append(vote)

    def tally(self, topic_id: str) -> Dict[str, Any]:
        votes = self._votes.get(topic_id, [])
        if not votes:
            return {"total": 0, "yes": 0, "no": 0, "abstain": 0, "consensus": False}
        total_weight = sum(v.weight for v in votes)
        yes_weight = sum(v.weight for v in votes if v.vote_type == VoteType.YES)
        no_weight = sum(v.weight for v in votes if v.vote_type == VoteType.NO)
        abstain_weight = sum(v.weight for v in votes if v.vote_type == VoteType.ABSTAIN)
        consensus = yes_weight / total_weight >= self.threshold if total_weight > 0 else False
        return {
            "total": len(votes),
            "yes": yes_weight,
            "no": no_weight,
            "abstain": abstain_weight,
            "consensus": consensus,
            "ratio": yes_weight / total_weight if total_weight > 0 else 0.0
        }

    def get_winning(self, topic_id: str) -> Optional[VoteType]:
        tally = self.tally(topic_id)
        if tally["yes"] > tally["no"] and tally["yes"] > tally["abstain"]:
            return VoteType.YES
        elif tally["no"] > tally["yes"] and tally["no"] > tally["abstain"]:
            return VoteType.NO
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {"topics": len(self._votes), "total_votes": sum(len(v) for v in self._votes.values())}

def run() -> None:
    print("Consensus Builder test")
    e = ConsensusBuilder(threshold=0.6)
    e.add_vote("topic1", Vote("a1", VoteType.YES, 1.0))
    e.add_vote("topic1", Vote("a2", VoteType.YES, 1.0))
    e.add_vote("topic1", Vote("a3", VoteType.NO, 1.0))
    e.add_vote("topic1", Vote("a4", VoteType.YES, 1.0))
    tally = e.tally("topic1")
    print("  Tally: " + str(tally))
    print("  Winning: " + (e.get_winning("topic1").name if e.get_winning("topic1") else "None"))
    print("  Stats: " + str(e.get_stats()))
    print("Consensus Builder test complete.")

if __name__ == "__main__":
    run()
