#!/usr/bin/env python3
"""
Agent Plugin Marketplace for MAGNATRIX-OS
Plugin discovery, install, rating, dependency resolution.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class PluginStatus(enum.Enum):
    AVAILABLE = "available"
    INSTALLED = "installed"
    UPDATING = "updating"
    DISABLED = "disabled"
    BROKEN = "broken"


@dataclasses.dataclass
class Plugin:
    id: str
    name: str
    version: str
    author: str
    description: str
    capabilities: List[str] = dataclasses.field(default_factory=list)
    dependencies: List[str] = dataclasses.field(default_factory=list)
    permissions: List[str] = dataclasses.field(default_factory=list)
    tags: List[str] = dataclasses.field(default_factory=list)
    category: str = "utility"
    download_url: str = ""
    hash_sha256: str = ""
    size_kb: int = 0
    status: PluginStatus = PluginStatus.AVAILABLE
    rating: float = 0.0
    rating_count: int = 0
    downloads: int = 0
    installed_at: Optional[float] = None
    updated_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "permissions": self.permissions,
            "tags": self.tags,
            "category": self.category,
            "download_url": self.download_url,
            "hash_sha256": self.hash_sha256,
            "size_kb": self.size_kb,
            "status": self.status.value,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "downloads": self.downloads,
        }


@dataclasses.dataclass
class Rating:
    plugin_id: str
    user_id: str
    score: int  # 1-5
    review: str = ""
    helpful: int = 0
    timestamp: float = dataclasses.field(default_factory=time.time)


class DependencyResolver:
    """Resolve plugin dependencies with topological ordering."""

    def resolve(self, plugin_id: str, registry: PluginRegistry) -> Tuple[bool, List[str]]:
        """Resolve dependencies. Returns (success, ordered_install_list)."""
        visited: Set[str] = set()
        temp_mark: Set[str] = set()
        order: List[str] = []

        def visit(pid: str) -> bool:
            if pid in temp_mark:
                return False  # Cycle detected
            if pid in visited:
                return True

            temp_mark.add(pid)
            plugin = registry.get(pid)
            if plugin:
                for dep in plugin.dependencies:
                    if not visit(dep):
                        return False
            order.append(pid)
            temp_mark.remove(pid)
            visited.add(pid)
            return True

        success = visit(plugin_id)
        return success, order


class PluginRegistry:
    """Central plugin registry."""

    def __init__(self) -> None:
        self._plugins: Dict[str, Plugin] = {}
        self._ratings: Dict[str, List[Rating]] = {}
        self._resolver = DependencyResolver()

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.id] = plugin

    def get(self, plugin_id: str) -> Optional[Plugin]:
        return self._plugins.get(plugin_id)

    def list_all(self) -> List[Plugin]:
        return list(self._plugins.values())

    def search(self, query: str) -> List[Plugin]:
        query_lower = query.lower()
        results = []
        for p in self._plugins.values():
            if query_lower in p.name.lower() or query_lower in p.description.lower():
                results.append(p)
            elif any(query_lower in tag.lower() for tag in p.tags):
                results.append(p)
            elif any(query_lower in cap.lower() for cap in p.capabilities):
                results.append(p)
        return results

    def by_category(self, category: str) -> List[Plugin]:
        return [p for p in self._plugins.values() if p.category == category]

    def by_capability(self, capability: str) -> List[Plugin]:
        return [p for p in self._plugins.values() if capability in p.capabilities]

    def trending(self, n: int = 10) -> List[Plugin]:
        sorted_plugins = sorted(self._plugins.values(), key=lambda p: p.downloads + p.rating_count * 10, reverse=True)
        return sorted_plugins[:n]

    def add_rating(self, rating: Rating) -> None:
        if rating.plugin_id not in self._ratings:
            self._ratings[rating.plugin_id] = []
        self._ratings[rating.plugin_id].append(rating)

        # Update weighted average (newer ratings weighted more)
        ratings = self._ratings[rating.plugin_id]
        weights = [1.0 + i * 0.1 for i in range(len(ratings))]  # Progressive weighting
        total_weight = sum(weights)
        weighted_sum = sum(r.score * w for r, w in zip(ratings, weights))

        plugin = self._plugins.get(rating.plugin_id)
        if plugin:
            plugin.rating = weighted_sum / total_weight if total_weight > 0 else 0
            plugin.rating_count = len(ratings)


class PluginInstaller:
    """Install and manage plugins."""

    def __init__(self, registry: PluginRegistry, install_dir: str = "./plugins") -> None:
        self._registry = registry
        self._install_dir = install_dir
        self._installed: Dict[str, Plugin] = {}
        os.makedirs(install_dir, exist_ok=True)

    def install(self, plugin_id: str) -> Tuple[bool, str]:
        plugin = self._registry.get(plugin_id)
        if not plugin:
            return False, "Plugin not found"

        if plugin_id in self._installed:
            return False, "Already installed"

        # Resolve dependencies
        success, dep_order = self._resolver.resolve(plugin_id, self._registry)
        if not success:
            return False, "Circular dependency detected"

        # Install dependencies first
        for dep_id in dep_order:
            if dep_id != plugin_id and dep_id not in self._installed:
                dep_plugin = self._registry.get(dep_id)
                if dep_plugin:
                    self._install_single(dep_plugin)

        # Install the plugin
        self._install_single(plugin)
        return True, "Installed successfully"

    def _install_single(self, plugin: Plugin) -> None:
        plugin.status = PluginStatus.INSTALLED
        plugin.installed_at = time.time()
        self._installed[plugin.id] = plugin

        # Create plugin directory
        plugin_dir = os.path.join(self._install_dir, plugin.id)
        os.makedirs(plugin_dir, exist_ok=True)

        # Save metadata
        with open(os.path.join(plugin_dir, "plugin.json"), "w") as f:
            json.dump(plugin.to_dict(), f, indent=2)

    def uninstall(self, plugin_id: str) -> bool:
        if plugin_id not in self._installed:
            return False

        # Check for dependents
        for p in self._installed.values():
            if plugin_id in p.dependencies:
                return False

        plugin = self._installed.pop(plugin_id)
        plugin.status = PluginStatus.AVAILABLE

        # Remove directory
        plugin_dir = os.path.join(self._install_dir, plugin_id)
        if os.path.exists(plugin_dir):
            import shutil
            shutil.rmtree(plugin_dir)

        return True

    def update(self, plugin_id: str) -> Tuple[bool, str]:
        if plugin_id not in self._installed:
            return False, "Not installed"

        plugin = self._registry.get(plugin_id)
        if not plugin:
            return False, "Plugin not in registry"

        installed = self._installed[plugin_id]
        if plugin.version == installed.version:
            return False, "Already up to date"

        # Update
        self._installed[plugin_id] = plugin
        plugin.status = PluginStatus.INSTALLED
        plugin.updated_at = time.time()
        return True, f"Updated to {plugin.version}"

    def list_installed(self) -> List[Plugin]:
        return list(self._installed.values())

    def check_updates(self) -> List[str]:
        updates = []
        for pid, installed in self._installed.items():
            latest = self._registry.get(pid)
            if latest and latest.version != installed.version:
                updates.append(pid)
        return updates


class PluginMarketplace:
    """Main marketplace orchestrator."""

    def __init__(self, install_dir: str = "./plugins") -> None:
        self.registry = PluginRegistry()
        self.installer = PluginInstaller(self.registry, install_dir)

    def publish(self, plugin: Plugin) -> None:
        self.registry.register(plugin)

    def search(self, query: str) -> List[Plugin]:
        return self.registry.search(query)

    def install(self, plugin_id: str) -> Tuple[bool, str]:
        return self.installer.install(plugin_id)

    def uninstall(self, plugin_id: str) -> bool:
        return self.installer.uninstall(plugin_id)

    def rate(self, plugin_id: str, user_id: str, score: int, review: str = "") -> None:
        rating = Rating(plugin_id=plugin_id, user_id=user_id, score=score, review=review)
        self.registry.add_rating(rating)

    def get_recommendations(self, user_id: str) -> List[Plugin]:
        # Simple recommendation: highest rated + trending
        trending = self.registry.trending(5)
        return trending

    def stats(self) -> Dict[str, Any]:
        return {
            "total_plugins": len(self.registry.list_all()),
            "installed": len(self.installer.list_installed()),
            "categories": len(set(p.category for p in self.registry.list_all())),
            "total_ratings": sum(len(r) for r in self.registry._ratings.values()),
        }


def _demo() -> None:
    print("=== Agent Plugin Marketplace Demo ===\n")

    marketplace = PluginMarketplace()

    # Register plugins
    print("--- Publishing Plugins ---")
    plugins = [
        Plugin(id="pdf_parser", name="PDF Parser", version="1.0.0", author="Alice", description="Parse PDF documents", category="parsing", capabilities=["parse_pdf", "extract_text"], tags=["pdf", "document"], dependencies=[]),
        Plugin(id="web_scraper", name="Web Scraper", version="1.0.0", author="Bob", description="Scrape web pages", category="data", capabilities=["scrape", "http"], tags=["web", "scraping"], dependencies=["http_client"]),
        Plugin(id="http_client", name="HTTP Client", version="1.0.0", author="Charlie", description="HTTP requests", category="network", capabilities=["http"], tags=["http", "network"], dependencies=[]),
        Plugin(id="rag_enhancer", name="RAG Enhancer", version="1.0.0", author="Dave", description="Enhance RAG results", category="ai", capabilities=["rerank", "compress"], tags=["rag", "ai"], dependencies=["pdf_parser"]),
    ]
    for p in plugins:
        marketplace.publish(p)
    print(f"  Published {len(plugins)} plugins\n")

    # Search
    print("--- Search ---")
    results = marketplace.search("pdf")
    print(f"  Search 'pdf': {len(results)} results")
    for r in results:
        print(f"    {r.name} ({r.id})")
    print()

    # Install with dependency resolution
    print("--- Install with Dependencies ---")
    success, msg = marketplace.install("rag_enhancer")
    print(f"  rag_enhancer: {success} - {msg}")
    success, msg = marketplace.install("web_scraper")
    print(f"  web_scraper: {success} - {msg}")
    print()

    # Ratings
    print("--- Ratings ---")
    marketplace.rate("pdf_parser", "user_1", 5, "Excellent PDF parser")
    marketplace.rate("pdf_parser", "user_2", 4, "Good but slow")
    marketplace.rate("pdf_parser", "user_3", 5, "Best parser ever")
    p = marketplace.registry.get("pdf_parser")
    if p:
        print(f"  pdf_parser rating: {p.rating:.2f} ({p.rating_count} reviews)")
    print()

    # Trending
    print("--- Trending ---")
    trending = marketplace.registry.trending(3)
    for p in trending:
        print(f"  {p.name}: {p.downloads} downloads, {p.rating:.2f} rating")
    print()

    # Stats
    print("--- Stats ---")
    stats = marketplace.stats()
    print(f"  Total: {stats['total_plugins']}, Installed: {stats['installed']}, Categories: {stats['categories']}")
    print()

    # Update check
    print("--- Update Check ---")
    updates = marketplace.installer.check_updates()
    print(f"  Updates available: {len(updates)}")
    print()

    print("=== Marketplace Demo Complete ===")


if __name__ == "__main__":
    _demo()
