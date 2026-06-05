"""Support Ticket Analyzer — sentiment, urgency, routing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import re
import time

class TicketPriority(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

class SupportTicketAnalyzer:
    def __init__(self):
        self.keywords = {
            "CRITICAL": ["outage", "down", "crash", "broken", "unable", "urgent", "emergency"],
            "HIGH": ["error", "fail", "slow", "bug", "issue"],
            "MEDIUM": ["question", "how", "help", "request"],
            "LOW": ["feedback", "suggestion", "improvement"],
        }
        self.tickets: List[Dict] = []

    def analyze(self, ticket_id: str, text: str, customer_tier: str = "standard") -> Dict:
        text_lower = text.lower()
        scores = {k: 0 for k in self.keywords}
        for level, words in self.keywords.items():
            for w in words:
                if w in text_lower:
                    scores[level] += 1
        if scores["CRITICAL"] > 0:
            priority = TicketPriority.CRITICAL
        elif scores["HIGH"] > 0:
            priority = TicketPriority.HIGH
        elif scores["MEDIUM"] > 0:
            priority = TicketPriority.MEDIUM
        else:
            priority = TicketPriority.LOW
        if customer_tier == "enterprise":
            priority = TicketPriority(min(priority.value - 1, 1)) if priority.value > 1 else priority
        result = {"ticket_id": ticket_id, "priority": priority.name, "scores": scores}
        self.tickets.append(result)
        return result

    def route(self, analysis: Dict) -> str:
        priority = analysis.get("priority", "LOW")
        routes = {"CRITICAL": "escalation_team", "HIGH": "senior_support", "MEDIUM": "support_team", "LOW": "community"}
        return routes.get(priority, "support_team")

    def stats(self) -> Dict:
        counts = {}
        for t in self.tickets:
            p = t["priority"]
            counts[p] = counts.get(p, 0) + 1
        return {"tickets": len(self.tickets), "by_priority": counts}

def run():
    sta = SupportTicketAnalyzer()
    print(sta.analyze("T1", "The system is completely down and broken!", "enterprise"))
    print(sta.analyze("T2", "How do I change my password?"))
    print(sta.stats())

if __name__ == "__main__":
    run()
