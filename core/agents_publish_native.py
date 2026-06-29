"""Agents Publish - Agent registry and marketplace publishing."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class AgentRegistryEntry:
    entry_id: str
    agent_name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    endpoint_url: str = ""
    status: str = "draft"  # draft, pending, published, deprecated
    registered_at: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "entry_id": self.entry_id,
            "agent_name": self.agent_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "endpoint_url": self.endpoint_url,
            "status": self.status,
            "registered_at": self.registered_at,
            "metrics": self.metrics,
        }


@dataclass
class MarketplaceListing:
    listing_id: str
    entry_id: str
    price_tier: str = "free"  # free, standard, premium
    marketplace: str = "gemini_enterprise"
    approved: bool = False
    listing_url: str = ""

    def to_dict(self) -> Dict:
        return {
            "listing_id": self.listing_id,
            "entry_id": self.entry_id,
            "price_tier": self.price_tier,
            "marketplace": self.marketplace,
            "approved": self.approved,
            "listing_url": self.listing_url,
        }


class AgentsPublish:
    """Agent registry and Gemini Enterprise marketplace publishing."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "agents_publish"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.registry: Dict[str, AgentRegistryEntry] = {}
        self.listings: Dict[str, MarketplaceListing] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for e in data.get("registry", []):
                    self.registry[e["entry_id"]] = AgentRegistryEntry(**e)
                for l in data.get("listings", []):
                    self.listings[l["listing_id"]] = MarketplaceListing(**l)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "registry": [e.to_dict() for e in self.registry.values()],
            "listings": [l.to_dict() for l in self.listings.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def register(self, agent_name: str, version: str = "1.0.0", description: str = "", author: str = "", tags: Optional[List[str]] = None) -> AgentRegistryEntry:
        """Register agent in internal registry."""
        entry_id = f"reg_{agent_name}_{version}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
        entry = AgentRegistryEntry(
            entry_id=entry_id,
            agent_name=agent_name,
            version=version,
            description=description,
            author=author,
            tags=tags or [],
            registered_at=time.time(),
            status="draft",
        )
        self.registry[entry_id] = entry
        self._save_state()
        return entry

    def update_endpoint(self, entry_id: str, endpoint_url: str) -> AgentRegistryEntry:
        """Update agent endpoint URL."""
        if entry_id not in self.registry:
            raise ValueError(f"Entry {entry_id} not found")
        entry = self.registry[entry_id]
        entry.endpoint_url = endpoint_url
        self._save_state()
        return entry

    def submit_for_review(self, entry_id: str) -> AgentRegistryEntry:
        """Submit agent for marketplace review."""
        if entry_id not in self.registry:
            raise ValueError(f"Entry {entry_id} not found")
        entry = self.registry[entry_id]
        entry.status = "pending"
        self._save_state()
        return entry

    def publish(self, entry_id: str, marketplace: str = "gemini_enterprise", price_tier: str = "free") -> MarketplaceListing:
        """Publish agent to marketplace."""
        if entry_id not in self.registry:
            raise ValueError(f"Entry {entry_id} not found")
        entry = self.registry[entry_id]
        entry.status = "published"

        listing_id = f"lst_{entry_id}_{int(time.time())}"
        listing = MarketplaceListing(
            listing_id=listing_id,
            entry_id=entry_id,
            marketplace=marketplace,
            price_tier=price_tier,
            approved=True,
            listing_url=f"https://enterprise.google.com/agents/{entry.agent_name}/{entry.version}",
        )
        self.listings[listing_id] = listing
        self._save_state()
        return listing

    def deprecate(self, entry_id: str) -> AgentRegistryEntry:
        """Deprecate an agent version."""
        if entry_id not in self.registry:
            raise ValueError(f"Entry {entry_id} not found")
        entry = self.registry[entry_id]
        entry.status = "deprecated"
        self._save_state()
        return entry

    def update_metrics(self, entry_id: str, metrics: Dict[str, float]) -> AgentRegistryEntry:
        """Update agent usage metrics."""
        if entry_id not in self.registry:
            raise ValueError(f"Entry {entry_id} not found")
        entry = self.registry[entry_id]
        entry.metrics.update(metrics)
        self._save_state()
        return entry

    def search_registry(self, query: str) -> List[AgentRegistryEntry]:
        """Search registry by name or tag."""
        query = query.lower()
        results = []
        for entry in self.registry.values():
            if query in entry.agent_name.lower() or any(query in t.lower() for t in entry.tags):
                results.append(entry)
        return results

    def get_stats(self) -> Dict:
        status_counts = {}
        for e in self.registry.values():
            status_counts[e.status] = status_counts.get(e.status, 0) + 1
        return {
            "registry_total": len(self.registry),
            "listings_total": len(self.listings),
            "status_breakdown": status_counts,
        }

    def to_dict(self) -> Dict:
        return {
            "registry": [e.to_dict() for e in self.registry.values()],
            "listings": [l.to_dict() for l in self.listings.values()],
            "stats": self.get_stats(),
        }


__all__ = ["AgentsPublish", "AgentRegistryEntry", "MarketplaceListing"]
