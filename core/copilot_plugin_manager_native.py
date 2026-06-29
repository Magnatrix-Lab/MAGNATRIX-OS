
"""
copilot_plugin_manager_native.py
MAGNATRIX-OS — Copilot Plugin Manager

Inspired by awesome-copilot plugins and marketplace:
Install, manage, and discover plugins for AI agent environments.
Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Plugin:
    plugin_id: str
    name: str
    description: str
    version: str
    author: str
    source_url: str
    install_path: str
    is_installed: bool = False
    is_active: bool = False
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    installed_at: str = ""

    def __post_init__(self):
        if not self.installed_at:
            self.installed_at = datetime.now().isoformat()


class CopilotPluginManager:
    """Manage plugins for AI agent environments."""

    MARKETPLACE = {
        "aws-tools": {"name": "AWS Tools", "description": "AWS CLI and SDK integration", "version": "1.2.0", "author": "aws-community", "dependencies": ["boto3"]},
        "github-integration": {"name": "GitHub Integration", "description": "GitHub API integration for PRs, issues, actions", "version": "2.0.1", "author": "github-team", "dependencies": ["PyGithub"]},
        "docker-helper": {"name": "Docker Helper", "description": "Docker container management", "version": "1.0.5", "author": "docker-community", "dependencies": []},
        "kubernetes-navigator": {"name": "Kubernetes Navigator", "description": "K8s manifest generation", "version": "1.1.0", "author": "k8s-community", "dependencies": ["kubernetes"]},
        "security-scanner": {"name": "Security Scanner", "description": "Security vulnerability scanning", "version": "1.3.0", "author": "security-team", "dependencies": ["bandit", "safety"]},
        "test-generator": {"name": "Test Generator", "description": "Generate tests automatically", "version": "1.0.2", "author": "qa-community", "dependencies": ["pytest"]},
        "doc-generator": {"name": "Documentation Generator", "description": "Auto-generate docs from code", "version": "1.0.0", "author": "docs-team", "dependencies": ["sphinx"]},
        "code-quality": {"name": "Code Quality", "description": "Linting and formatting", "version": "2.0.0", "author": "quality-team", "dependencies": ["black", "flake8", "mypy"]},
    }

    def __init__(self, plugins_dir: str = "./copilot_plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(exist_ok=True)
        self.installed: Dict[str, Plugin] = {}
        self._load()

    def _load(self) -> None:
        file = self.plugins_dir / "installed.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pd in data.items():
                        self.installed[pid] = Plugin(**pd)
            except Exception:
                pass

    def _save(self) -> None:
        file = self.plugins_dir / "installed.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump({pid: asdict(p) for pid, p in self.installed.items()}, f, indent=2)

    def search_marketplace(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        results = []
        for pid, info in self.MARKETPLACE.items():
            if q in info["name"].lower() or q in info["description"].lower():
                results.append({"plugin_id": pid, **info})
        return results

    def install(self, plugin_id: str) -> Optional[Plugin]:
        if plugin_id not in self.MARKETPLACE:
            return None
        info = self.MARKETPLACE[plugin_id]
        install_path = str(self.plugins_dir / plugin_id)
        plugin = Plugin(
            plugin_id=plugin_id, name=info["name"], description=info["description"],
            version=info["version"], author=info["author"], source_url="",
            install_path=install_path, is_installed=True, is_active=True,
            dependencies=info.get("dependencies", []),
        )
        self.installed[plugin_id] = plugin
        self._save()
        return plugin

    def uninstall(self, plugin_id: str) -> bool:
        if plugin_id in self.installed:
            del self.installed[plugin_id]
            self._save()
            return True
        return False

    def activate(self, plugin_id: str) -> bool:
        if plugin_id in self.installed:
            self.installed[plugin_id].is_active = True
            self._save()
            return True
        return False

    def deactivate(self, plugin_id: str) -> bool:
        if plugin_id in self.installed:
            self.installed[plugin_id].is_active = False
            self._save()
            return True
        return False

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        return self.installed.get(plugin_id)

    def list_installed(self) -> List[Plugin]:
        return list(self.installed.values())

    def list_active(self) -> List[Plugin]:
        return [p for p in self.installed.values() if p.is_active]

    def check_dependencies(self, plugin_id: str) -> List[str]:
        plugin = self.installed.get(plugin_id)
        if not plugin:
            return []
        missing = []
        for dep in plugin.dependencies:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)
        return missing

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.installed)
        active = sum(1 for p in self.installed.values() if p.is_active)
        return {
            "installed": total, "active": active, "marketplace_size": len(self.MARKETPLACE),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CopilotPluginManager", "Plugin"]
