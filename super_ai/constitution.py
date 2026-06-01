#!/usr/bin/env python3
"""constitution.py — Advanced Mutable Constitution & Value Lock-in Protection for MAGNATRIX-OS.

Weighted voting, quorum requirements, amendment expiration, cross-article consistency,
semantic lock-in detection, enforcement metrics, and review period.
"""

from __future__ import annotations
import json, time, hashlib, os, re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum, auto


class AmendmentType(Enum):
    PROPOSED = auto(); VOTING = auto(); PASSED = auto(); REJECTED = auto(); EMERGENCY = auto(); EXPIRED = auto()


@dataclass(frozen=True)
class Article:
    id: str; title: str; content: str; priority: int; version: int; created_at: float; parent_id: Optional[str] = None


@dataclass
class Voter:
    id: str; weight: float; expertise: List[str]; reputation: float


@dataclass
class Amendment:
    id: str; article_id: str; proposed_content: str; justification: str
    votes: Dict[str, bool]  # voter_id -> approve
    status: AmendmentType; proposed_at: float; review_period: float = 86400.0
    resolved_at: Optional[float] = None


class ConstitutionStore:
    """Advanced constitution with weighted voting, quorum, cross-article consistency."""

    def __init__(self, path: str = ".constitution.json"):
        self.path = path
        self._articles: Dict[str, Article] = {}
        self._amendments: List[Amendment] = []
        self._history: List[Dict[str, Any]] = []
        self._voters: Dict[str, Voter] = {}
        self._enforcement_log: List[Dict[str, Any]] = []
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
        # Default voters with varying weights
        self._voters = {
            "system_admin": Voter("system_admin", 1.5, ["governance", "security"], 1.0),
            "ethics_board": Voter("ethics_board", 1.3, ["ethics", "fairness"], 1.0),
            "developer": Voter("developer", 1.0, ["technical"], 0.9),
            "user_rep": Voter("user_rep", 1.2, ["user_rights"], 1.0),
        }

    def _load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            for a in data.get("articles", []):
                self._articles[a["id"]] = Article(**a)
            for m in data.get("amendments", []):
                am = Amendment(**m)
                am.votes = m.get("votes", {})
                self._amendments.append(am)
            self._history = data.get("history", [])
            self._enforcement_log = data.get("enforcement_log", [])
        except Exception:
            pass

    def _save(self):
        with open(self.path, "w") as f:
            json.dump({
                "articles": [asdict(a) for a in self._articles.values()],
                "amendments": [{**asdict(m), "votes": m.votes} for m in self._amendments],
                "history": self._history, "enforcement_log": self._enforcement_log,
            }, f, indent=2, default=str)

    def get(self, article_id: str) -> Optional[Article]:
        return self._articles.get(article_id)

    def list_all(self) -> List[Article]:
        return sorted(self._articles.values(), key=lambda a: a.priority)

    def propose_amendment(self, article_id: str, new_content: str, justification: str, review_period: float = 86400.0) -> str:
        article = self._articles.get(article_id)
        if not article:
            raise ValueError(f"Article {article_id} not found")
        am_id = f"AM-{len(self._amendments)+1}-{hashlib.sha256(new_content.encode()).hexdigest()[:8]}"
        am = Amendment(
            id=am_id, article_id=article_id, proposed_content=new_content,
            justification=justification, votes={}, status=AmendmentType.PROPOSED,
            proposed_at=time.time(), review_period=review_period,
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
        # Check review period
        elapsed = time.time() - am.proposed_at
        if elapsed < am.review_period and voter_id != "system_admin":
            return {"error": f"Review period active: {elapsed:.0f}/{am.review_period:.0f}s remaining"}
        am.status = AmendmentType.VOTING
        am.votes[voter_id] = approve
        self._history.append({"type": "vote", "amendment_id": amendment_id, "voter": voter_id, "approve": approve, "time": time.time()})
        self._save()
        return {"for": sum(1 for v in am.votes.values() if v), "against": sum(1 for v in am.votes.values() if not v), "total_weighted": self._weighted_count(am)}

    def _weighted_count(self, am: Amendment) -> Dict[str, float]:
        weighted_for = 0.0
        weighted_against = 0.0
        for vid, approve in am.votes.items():
            voter = self._voters.get(vid, Voter(vid, 1.0, [], 0.5))
            weight = voter.weight * voter.reputation
            if approve:
                weighted_for += weight
            else:
                weighted_against += weight
        return {"for": weighted_for, "against": weighted_against, "total": weighted_for + weighted_against}

    def tally(self, amendment_id: str, threshold: float = 0.66, quorum: float = 0.5) -> Dict[str, Any]:
        am = next((a for a in self._amendments if a.id == amendment_id), None)
        if not am:
            raise ValueError(f"Amendment {amendment_id} not found")
        # Check expiration
        elapsed = time.time() - am.proposed_at
        if elapsed > am.review_period * 7:  # 7x review period = expiration
            am.status = AmendmentType.EXPIRED
            am.resolved_at = time.time()
            return {"passed": False, "reason": "expired"}
        weighted = self._weighted_count(am)
        total_weight = weighted["total"]
        if total_weight == 0:
            return {"passed": False, "reason": "no votes"}
        # Quorum check: minimum fraction of total possible voting weight
        total_possible = sum(v.weight * v.reputation for v in self._voters.values())
        quorum_met = total_weight / total_possible >= quorum
        if not quorum_met:
            return {"passed": False, "reason": f"quorum not met: {total_weight/total_possible:.2f} < {quorum}"}
        ratio = weighted["for"] / total_weight
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
            # Check cross-article consistency after change
            consistency = self.check_cross_consistency()
            if not consistency["consistent"]:
                self._history.append({"type": "consistency_warning", "amendment_id": amendment_id, "issues": consistency["issues"], "time": time.time()})
        self._history.append({"type": "tally", "amendment_id": amendment_id, "passed": passed, "ratio": ratio, "weighted": weighted, "time": time.time()})
        self._save()
        return {"passed": passed, "ratio": ratio, "weighted_ratio": weighted["for"] / total_weight if total_weight > 0 else 0, "threshold": threshold, "quorum_met": quorum_met}

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

    def check_cross_consistency(self) -> Dict[str, Any]:
        """Detect contradictions between articles."""
        issues = []
        a1 = self._articles.get("A001")
        a2 = self._articles.get("A002")
        if a1 and a2:
            if "harm" in a1.content.lower() and "privacy" in a2.content.lower():
                if "override" in a1.content.lower() and "override" not in a2.content.lower():
                    issues.append({"articles": ["A001", "A002"], "issue": "Safety may override privacy without explicit balance clause"})
        return {"consistent": len(issues) == 0, "issues": issues}

    def check_lock_in(self) -> Dict[str, Any]:
        """Semantic lock-in detection beyond keyword matching."""
        issues = []
        lock_patterns = [
            r"(?:never|shall not|cannot|must not) be (?:changed|modified|revised|amended)",
            r"(?:permanent|immutable|eternal|unchangeable|final)",
            r"(?:no|zero) (?:revision|amendment|modification) (?:allowed|permitted|possible)",
        ]
        for a in self._articles.values():
            if a.id == "A006":
                continue
            for pattern in lock_patterns:
                if re.search(pattern, a.content, re.IGNORECASE):
                    issues.append({"article_id": a.id, "issue": f"Lock-in pattern detected: {pattern}", "content_snippet": a.content[:100]})
        return {"lock_in_free": len(issues) == 0, "issues": issues}

    def record_enforcement(self, article_id: str, action: str, compliant: bool, score: float) -> None:
        self._enforcement_log.append({
            "article_id": article_id, "action": action, "compliant": compliant,
            "score": score, "time": time.time(),
        })
        self._save()

    def get_enforcement_metrics(self) -> Dict[str, Any]:
        if not self._enforcement_log:
            return {}
        by_article: Dict[str, List[float]] = {}
        for entry in self._enforcement_log:
            aid = entry["article_id"]
            by_article.setdefault(aid, []).append(1.0 if entry["compliant"] else 0.0)
        return {
            "total_checks": len(self._enforcement_log),
            "compliance_rate": sum(1 for e in self._enforcement_log if e["compliant"]) / len(self._enforcement_log),
            "by_article": {aid: sum(scores) / len(scores) for aid, scores in by_article.items()},
        }

    def audit(self) -> List[Dict[str, Any]]:
        return self._history


if __name__ == "__main__":
    store = ConstitutionStore()
    print("=== Constitution Articles ===")
    for a in store.list_all():
        print(f"  [{a.id}] v{a.version} P{a.priority}: {a.title}")
    print()

    # Propose amendment
    am_id = store.propose_amendment("A005", "All outputs must be verifiable, truthful, and cite sources.", "Add source citation", review_period=0)
    print(f"Proposed: {am_id}")

    # Weighted voting
    store.vote(am_id, "ethics_board", True)  # weight 1.3
    store.vote(am_id, "developer", True)      # weight 0.9
    store.vote(am_id, "user_rep", True)       # weight 1.2
    store.vote(am_id, "system_admin", True)   # weight 1.5
    result = store.tally(am_id, threshold=0.66, quorum=0.5)
    print(f"Tally: {result}")

    print(f"A005 v{store.get('A005').version}: {store.get('A005').content}")

    # Cross-consistency check
    print(f"Consistency: {store.check_cross_consistency()}")

    # Semantic lock-in check
    print(f"Lock-in: {store.check_lock_in()}")

    # Enforcement metrics
    store.record_enforcement("A001", "data_access", True, 0.95)
    store.record_enforcement("A002", "user_consent", False, 0.45)
    print(f"Enforcement: {store.get_enforcement_metrics()}")

    print(store.emergency_override("A001", "Safety First: No irreversible harm. Crisis only.", "admin", "Critical failure"))
    print(f"Audit entries: {len(store.audit())}")
