"""Engagement Scorer — attention, interaction, retention metrics, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import time

class EngagementMetric(Enum):
    ATTENTION = auto()
    INTERACTION = auto()
    RETENTION = auto()
    CONVERSION = auto()
    SATISFACTION = auto()

@dataclass
class EngagementSession:
    session_id: str
    user_id: str
    start_time: float
    events: List[Dict] = field(default_factory=list)
    end_time: Optional[float] = None

class EngagementScorer:
    def __init__(self):
        self.sessions: Dict[str, EngagementSession] = {}
        self.weights = {
            EngagementMetric.ATTENTION: 0.25,
            EngagementMetric.INTERACTION: 0.25,
            EngagementMetric.RETENTION: 0.2,
            EngagementMetric.CONVERSION: 0.15,
            EngagementMetric.SATISFACTION: 0.15,
        }

    def start_session(self, session_id: str, user_id: str):
        self.sessions[session_id] = EngagementSession(session_id, user_id, time.time())

    def add_event(self, session_id: str, event_type: str, value: float = 1.0):
        session = self.sessions.get(session_id)
        if session:
            session.events.append({"type": event_type, "value": value, "time": time.time()})

    def end_session(self, session_id: str):
        session = self.sessions.get(session_id)
        if session:
            session.end_time = time.time()

    def score_session(self, session_id: str) -> Dict[str, float]:
        session = self.sessions.get(session_id)
        if not session:
            return {}
        duration = (session.end_time or time.time()) - session.start_time
        click_count = sum(1 for e in session.events if e["type"] == "click")
        scroll_depth = max((e["value"] for e in session.events if e["type"] == "scroll"), default=0)
        conversion = sum(1 for e in session.events if e["type"] == "conversion")
        attention = min(duration / 300, 1.0)
        interaction = min(click_count / 10, 1.0)
        retention = min(scroll_depth / 100, 1.0)
        conv = min(conversion / 1, 1.0)
        satisfaction = min(len(session.events) / 20, 1.0)
        scores = {
            EngagementMetric.ATTENTION.name: attention,
            EngagementMetric.INTERACTION.name: interaction,
            EngagementMetric.RETENTION.name: retention,
            EngagementMetric.CONVERSION.name: conv,
            EngagementMetric.SATISFACTION.name: satisfaction,
        }
        overall = sum(scores[k] * self.weights.get(EngagementMetric[k], 0.2) for k in scores)
        scores["OVERALL"] = overall
        return scores

    def score_user(self, user_id: str) -> float:
        user_sessions = [s for s in self.sessions.values() if s.user_id == user_id]
        if not user_sessions:
            return 0.0
        return sum(self.score_session(s.session_id).get("OVERALL", 0) for s in user_sessions) / len(user_sessions)

    def stats(self) -> Dict:
        return {"sessions": len(self.sessions), "users": len(set(s.user_id for s in self.sessions.values()))}

def run():
    scorer = EngagementScorer()
    scorer.start_session("s1", "user1")
    scorer.add_event("s1", "click", 1)
    scorer.add_event("s1", "click", 1)
    scorer.add_event("s1", "scroll", 80)
    scorer.add_event("s1", "conversion", 1)
    scorer.end_session("s1")
    print(scorer.score_session("s1"))
    print(scorer.stats())

if __name__ == "__main__":
    run()
