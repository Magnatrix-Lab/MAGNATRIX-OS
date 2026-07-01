#!/usr/bin/env python3
"""skill_marketplace_native.py — MAGNATRIX-OS Skill Registry & Marketplace

Signed skill registry, verification pipeline, trust scoring, ratings,
revenue sharing, vertical packs. Pure stdlib.
"""
from __future__ import annotations
import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SkillAuthor:
    id: str
    name: str
    pubkey: str  # public key for verification
    trust_score: float = 0.0  # 0-1
    skills_published: int = 0
    total_downloads: int = 0
    avg_rating: float = 0.0
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillSignature:
    author_id: str
    signature: str  # hex signature of skill hash
    timestamp: float
    verification_status: str = "pending"  # pending, verified, failed


@dataclass
class SkillPackage:
    id: str
    name: str
    version: str
    description: str
    category: str  # dev, finance, legal, medical, creative, etc.
    author_id: str
    content_hash: str  # SHA-256 of skill content
    signature: Optional[SkillSignature] = None
    rating: float = 0.0  # 1-5
    rating_count: int = 0
    downloads: int = 0
    price: float = 0.0  # 0 = free, otherwise in platform credits
    dependencies: List[str] = field(default_factory=list)
    compatible_versions: List[str] = field(default_factory=list)  # Magnatrix OS versions
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class Review:
    id: str
    skill_id: str
    user_id: str
    rating: float  # 1-5
    review_text: str
    verified_purchase: bool = False
    timestamp: float = field(default_factory=time.time)
    helpful_count: int = 0


class SkillMarketplaceNative:
    """Native skill marketplace with signed registry and verification."""

    def __init__(self, workspace: str = "./skill_marketplace") -> None:
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._skills: Dict[str, SkillPackage] = {}
        self._authors: Dict[str, SkillAuthor] = {}
        self._reviews: Dict[str, List[Review]] = {}
        self._transactions: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._skills_path = self.workspace / "skills.json"
        self._authors_path = self.workspace / "authors.json"
        self._reviews_path = self.workspace / "reviews.json"
        self._transactions_path = self.workspace / "transactions.json"
        self._load()

    def _load(self) -> None:
        if self._skills_path.exists():
            try:
                with open(self._skills_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for sid, sd in data.items(): self._skills[sid] = SkillPackage(**sd)
            except Exception: pass
        if self._authors_path.exists():
            try:
                with open(self._authors_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for aid, ad in data.items(): self._authors[aid] = SkillAuthor(**ad)
            except Exception: pass
        if self._reviews_path.exists():
            try:
                with open(self._reviews_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for sid, rlist in data.items(): self._reviews[sid] = [Review(**r) for r in rlist]
            except Exception: pass
        if self._transactions_path.exists():
            try:
                with open(self._transactions_path, "r", encoding="utf-8") as f:
                    self._transactions = json.load(f)
            except Exception: pass

    def _save(self) -> None:
        with open(self._skills_path, "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self._skills.items()}, f, indent=2, default=str)
        with open(self._authors_path, "w", encoding="utf-8") as f:
            json.dump({aid: asdict(a) for aid, a in self._authors.items()}, f, indent=2, default=str)
        with open(self._reviews_path, "w", encoding="utf-8") as f:
            json.dump({sid: [asdict(r) for r in rlist] for sid, rlist in self._reviews.items()}, f, indent=2, default=str)
        with open(self._transactions_path, "w", encoding="utf-8") as f:
            json.dump(self._transactions[-10000:], f, indent=2, default=str)

    def register_author(self, name: str, pubkey: str, verified: bool = False) -> str:
        with self._lock:
            author_id = f"author_{int(time.time())}_{str(uuid.uuid4())[:6]}"
            self._authors[author_id] = SkillAuthor(
                id=author_id, name=name, pubkey=pubkey, verified=verified
            )
            self._save()
            return author_id

    def publish_skill(self, author_id: str, name: str, version: str, description: str, category: str, content: str, price: float = 0.0, dependencies: Optional[List[str]] = None, compatible_versions: Optional[List[str]] = None, tags: Optional[List[str]] = None) -> str:
        """Publish a skill. Returns skill ID. Content hash auto-computed."""
        with self._lock:
            if author_id not in self._authors: raise ValueError("Author not found")
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            skill_id = f"skill_{int(time.time())}_{str(uuid.uuid4())[:6]}"
            skill = SkillPackage(
                id=skill_id, name=name, version=version, description=description,
                category=category, author_id=author_id, content_hash=content_hash,
                price=price, dependencies=dependencies or [],
                compatible_versions=compatible_versions or [], tags=tags or []
            )
            self._skills[skill_id] = skill
            # Update author stats
            author = self._authors[author_id]
            author.skills_published += 1
            self._save()
            return skill_id

    def sign_skill(self, skill_id: str, author_id: str, signature: str) -> bool:
        """Add cryptographic signature to a skill. (Placeholder for crypto verification)."""
        with self._lock:
            if skill_id not in self._skills: return False
            if author_id not in self._authors: return False
            skill = self._skills[skill_id]
            if skill.author_id != author_id: return False
            sig = SkillSignature(
                author_id=author_id, signature=signature, timestamp=time.time(),
                verification_status="verified"  # In production: verify with pubkey
            )
            skill.signature = sig
            self._save()
            return True

    def verify_skill(self, skill_id: str, content: str) -> Tuple[bool, str]:
        """Verify skill integrity against stored hash."""
        with self._lock:
            if skill_id not in self._skills: return False, "Skill not found"
            skill = self._skills[skill_id]
            computed_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if computed_hash == skill.content_hash:
                return True, "Hash verified"
            return False, f"Hash mismatch: expected {skill.content_hash[:16]}..., got {computed_hash[:16]}..."

    def review_skill(self, skill_id: str, user_id: str, rating: float, review_text: str, verified_purchase: bool = False) -> str:
        with self._lock:
            if skill_id not in self._skills: raise ValueError("Skill not found")
            review_id = f"review_{int(time.time())}_{str(uuid.uuid4())[:6]}"
            review = Review(
                id=review_id, skill_id=skill_id, user_id=user_id, rating=rating,
                review_text=review_text, verified_purchase=verified_purchase
            )
            if skill_id not in self._reviews: self._reviews[skill_id] = []
            self._reviews[skill_id].append(review)
            # Update skill rating
            skill = self._skills[skill_id]
            all_ratings = [r.rating for r in self._reviews[skill_id]]
            skill.rating = sum(all_ratings) / len(all_ratings)
            skill.rating_count = len(all_ratings)
            self._save()
            return review_id

    def purchase_skill(self, skill_id: str, user_id: str, payment_tx: str = "") -> bool:
        with self._lock:
            if skill_id not in self._skills: return False
            skill = self._skills[skill_id]
            tx = {
                "timestamp": time.time(),
                "skill_id": skill_id,
                "user_id": user_id,
                "price": skill.price,
                "payment_tx": payment_tx,
                "tx_id": str(uuid.uuid4())[:12],
            }
            self._transactions.append(tx)
            skill.downloads += 1
            # Update author stats
            author = self._authors.get(skill.author_id)
            if author: author.total_downloads += 1
            self._save()
            return True

    def download_skill(self, skill_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Download a skill (free or purchased)."""
        with self._lock:
            if skill_id not in self._skills: return None
            skill = self._skills[skill_id]
            if skill.price > 0:
                # Check if purchased
                purchased = any(t["skill_id"] == skill_id and t["user_id"] == user_id for t in self._transactions)
                if not purchased: return None
            return {
                "id": skill.id,
                "name": skill.name,
                "version": skill.version,
                "content_hash": skill.content_hash,
                "author_id": skill.author_id,
                "dependencies": skill.dependencies,
                "compatible_versions": skill.compatible_versions,
                "tags": skill.tags,
            }

    def search_skills(self, query: str = "", category: Optional[str] = None, tags: Optional[List[str]] = None, min_rating: float = 0.0, max_price: Optional[float] = None, sort_by: str = "rating") -> List[SkillPackage]:
        with self._lock:
            results = list(self._skills.values())
            if query:
                q = query.lower()
                results = [s for s in results if q in s.name.lower() or q in s.description.lower()]
            if category: results = [s for s in results if s.category == category]
            if tags: results = [s for s in results if any(t in s.tags for t in tags)]
            if min_rating: results = [s for s in results if s.rating >= min_rating]
            if max_price is not None: results = [s for s in results if s.price <= max_price]
            if sort_by == "rating": results.sort(key=lambda s: s.rating, reverse=True)
            elif sort_by == "downloads": results.sort(key=lambda s: s.downloads, reverse=True)
            elif sort_by == "price": results.sort(key=lambda s: s.price)
            elif sort_by == "newest": results.sort(key=lambda s: s.created_at, reverse=True)
            return results

    def get_author_stats(self, author_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if author_id not in self._authors: return None
            author = self._authors[author_id]
            skills = [s for s in self._skills.values() if s.author_id == author_id]
            total_revenue = sum(s.price * s.downloads for s in skills)
            return {
                "author_id": author_id,
                "name": author.name,
                "trust_score": author.trust_score,
                "verified": author.verified,
                "skills_published": author.skills_published,
                "total_downloads": author.total_downloads,
                "avg_rating": author.avg_rating,
                "total_revenue": total_revenue,
                "skills": [s.id for s in skills],
            }

    def get_market_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_skills = len(self._skills)
            total_authors = len(self._authors)
            total_transactions = len(self._transactions)
            total_revenue = sum(t.get("price", 0) for t in self._transactions)
            categories = {}
            for s in self._skills.values(): categories[s.category] = categories.get(s.category, 0) + 1
            return {
                "total_skills": total_skills,
                "total_authors": total_authors,
                "total_transactions": total_transactions,
                "total_revenue": total_revenue,
                "categories": categories,
                "avg_rating": sum(s.rating for s in self._skills.values()) / total_skills if total_skills else 0,
            }

    def print_summary(self) -> str:
        stats = self.get_market_stats()
        lines = [
            "=== Skill Marketplace Summary ===",
            f"Total Skills: {stats['total_skills']}",
            f"Total Authors: {stats['total_authors']}",
            f"Total Transactions: {stats['total_transactions']}",
            f"Total Revenue: {stats['total_revenue']:.2f}",
            f"Avg Rating: {stats['avg_rating']:.2f}",
            "
--- Categories ---",
        ]
        for cat, count in stats['categories'].items(): lines.append(f"  {cat}: {count}")
        return "
".join(lines)

if __name__ == "__main__":
    market = SkillMarketplaceNative()
    aid = market.register_author("DevOps Master", "pubkey_abc123", verified=True)
    sid = market.publish_skill(aid, "Kubernetes Orchestrator", "1.0.0", "Auto-deploy K8s manifests", "dev", "skill_content_here", price=10.0, tags=["k8s", "devops", "deployment"])
    market.sign_skill(sid, aid, "signature_placeholder")
    market.review_skill(sid, "user_001", 5.0, "Excellent skill, very reliable!")
    market.purchase_skill(sid, "user_002")
    print(market.print_summary())
