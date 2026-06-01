#!/usr/bin/env python3
"""constitution.py — Mutable Constitution & Value Lock-in Protection for MAGNATRIX-OS.

Pattern: Ensure constitution can evolve but never permanently freeze values.
Every value must be revisable via consensus. No lock-in trap.
"""

from __future__ import annotations
import json, time, hashlib, copy, os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum, auto


class AmendmentType(Enum):
    PROPOSED = auto()
    VOTING = auto()
    PASSED = auto()
    REJECTED = auto()
    EMERGENCY = auto()


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    content: str
    priority: int  # 1 = core, 10 = advisory
    version: int
    created_at: float
    parent_id: Optional[str] = None


@dataclass
class Amendment:
    id: str
    article_id: str
    proposed_content: str
    justification: str
    votes_for: int
    votes_against: int
    status: AmendmentType
    proposed_at: float
    resolved_at: Optional[float] = None


class ConstitutionStore:
    """Immutable-append constitution with full lineage."""

    def __init__(self, path: str = ".constitution.json"):
        self.path = path
        self._articles: Dict[str, Article] = {}
        self._amendments: List[Amendment] = []
        self._history: List[Dict[str, Any]] = []
        self._init_defaults()
        self._load()

    def _init_defaults(self):
        defaults = [
            Article("A001", "Safety First", "No action shall cause irreversible harm to humans or systems.", 1, 1, time.time()),
            Article("A002", "Privacy by Default", "All data must be encrypted and user consent required.", 1, 1, time.time()),
            Article("A003", "Fairness", "No bias in decision-making; equal treatment for all users.", 2, 1, time.time()),
            Article("A004", "Autonomy", "Users retain full control over their data and agent behavior.", 2, 1, time.time()),
            Article("A005", "Truth", "All outputs must be verifiable and truthful to the best of capability.", 2, 1, time.time()),
            Article("A006", "Value Lock-in Guard", "No value may be made permanently immutable. This article itself is revisable.", 1, 1, time.time()),
        ]
        for a in defaults:
            self._articles[a.id] = a

    def _load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, "r") as f:
            data = json.load(f)
        for a in data.get("articles", []):
            self._articles[a["id"]] = Article(**a)
        self._amendments = [Amendment(**m) for m in data.get("amendments", [])]
        self._history = data.get("history", [])

    def _save(self):
        with open(self.path, "w") as f:
            json.dump({
                "articles": [asdict(a) for a in self._articles.values()],
                "amendments": [asdict(m) for m in self._amendments],
                "history": self._history,
            }, f, indent=2, default=str)

    def get(self, article_id: str) -> Optional[Article]:
        return self._articles.get(article_id)

    def list_all(self) -> List[Article]:
        return sorted(self._articles.values(), key=lambda a: a.priority)

    def propose_amendment(self, article_id: str, new_content: str, justification: str) -> str:
        article = self._articles.get(article_id)
        if not article:
            raise ValueError(f"Article {article_id} not found")
        am_id = f"AM-{len(self._amendments)+1}-{hashlib.sha256(new_content.encode()).hexdigest()[:8]}"
        am = Amendment(
            id=am_id, article_id=article_id, proposed_content=new_content,
            justification=justification, votes_for=0, votes_against=0,
            status=AmendmentType.PROPOSED, proposed_at=time.time(),
        )
        self._amendments.append(am)
        self._history.append({"type": "propose", "amendment_id": am_id, "time": time.time()})
        self._save()
        return am_id

    def vote(self, amendment_id: str, voter_id: str, approve: bool) -> Dict[str, Any]:
        am = next((a for a in self._amendments if a.id == amendment_id), None)
        if not am:
            raise ValueError(f"Amendment {amendment_id} not found")
        if am.status not in (AmendmentType.PROPOSED, AmendmentType.VOTING):
            raise ValueError(f"Amendment already {am.status.name}")
        am.status = AmendmentType.VOTING
        if approve:
            am.votes_for += 1
        else:
            am.votes_against += 1
        self._history.append({"type": "vote", "amendment_id": amendment_id, "voter": voter_id, "approve": approve, "time": time.time()})
        self._save()
        return {"for": am.votes_for, "against": am.votes_against}

    def tally(self, amendment_id: str, threshold: float = 0.66) -> Dict[str, Any]:
        am = next((a for a in self._amendments if a.id == amendment_id), None)
        if not am:
            raise ValueError(f"Amendment {amendment_id} not found")
        total = am.votes_for + am.votes_against
        if total == 0:
            return {"passed": False, "reason": "no votes"}
        ratio = am.votes_for / total
        passed = ratio >= threshold
        am.status = AmendmentType.PASSED if passed else AmendmentType.REJECTED
        am.resolved_at = time.time()
        if passed:
            old = self._articles[am.article_id]
            new_article = Article(
                id=old.id, title=old.title, content=am.proposed_content,
                priority=old.priority, version=old.version + 1,
                created_at=time.time(), parent_id=old.id,
            )
            self._articles[old.id] = new_article
        self._history.append({"type": "tally", "amendment_id": amendment_id, "passed": passed, "time": time.time()})
        self._save()
        return {"passed": passed, "ratio": ratio, "threshold": threshold}

    def emergency_override(self, article_id: str, new_content: str, authority: str, reason: str) -> str:
        old = self._articles.get(article_id)
        if not old:
            raise ValueError(f"Article {article_id} not found")
        new_article = Article(
            id=old.id, title=old.title, content=new_content,
            priority=old.priority, version=old.version + 1,
            created_at=time.time(), parent_id=old.id,
        )
        self._articles[article_id] = new_article
        self._history.append({
            "type": "emergency_override", "article_id": article_id,
            "authority": authority, "reason": reason, "time": time.time(),
        })
        self._save()
        return f"Emergency override by {authority}: {reason}"

    def audit(self) -> List[Dict[str, Any]]:
        return self._history

    def check_lock_in(self) -> Dict[str, Any]:
        issues = []
        for a in self._articles.values():
            if "permanent" in a.content.lower() or "immutable" in a.content.lower():
                if a.id != "A006":
                    issues.append({"article_id": a.id, "issue": "potential lock-in language"})
        return {"lock_in_free": len(issues) == 0, "issues": issues}


if __name__ == "__main__":
    store = ConstitutionStore()
    print("=== Constitution Articles ===")
    for a in store.list_all():
        print(f"  [{a.id}] v{a.version} P{a.priority}: {a.title}")
    print()
    am_id = store.propose_amendment("A005", "All outputs must be verifiable, truthful, and cite sources.", "Add source citation")
    print(f"Proposed: {am_id}")
    store.vote(am_id, "voter1", True)
    store.vote(am_id, "voter2", True)
    store.vote(am_id, "voter3", False)
    result = store.tally(am_id, threshold=0.66)
    print(f"Tally: {result}")
    print(f"A005 v{store.get('A005').version}: {store.get('A005').content}")
    print(f"Lock-in: {store.check_lock_in()}")
    print(store.emergency_override("A001", "Safety First: No irreversible harm. Crisis only.", "admin", "Critical failure"))
    print(f"Audit entries: {len(store.audit())}")
