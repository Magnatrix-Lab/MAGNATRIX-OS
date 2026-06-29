"""
agent_hook_manager_native.py
MAGNATRIX-OS — Agent Hook Manager

Inspired by telagod/code-abyss cross-platform hooks:
Manage agent hooks for Claude Code, Codex CLI, Gemini CLI, OpenClaw. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class AgentHook:
    hook_id: str
    target_platform: str  # claude, codex, gemini, openclaw
    hook_type: str  # pre_edit, post_edit, pre_command, post_command
    script_content: str
    is_active: bool = True
    priority: int = 50


class AgentHookManager:
    """Manage cross-platform agent hooks for AI coding agents."""

    SUPPORTED_PLATFORMS = ["claude", "codex", "gemini", "openclaw", "pi", "hermes"]
    HOOK_TYPES = ["pre_edit", "post_edit", "pre_command", "post_command", "pre_write", "post_write"]

    def __init__(self, hooks_dir: str = "./agent_hooks"):
        self.hooks_dir = Path(hooks_dir)
        self.hooks_dir.mkdir(exist_ok=True)
        self.hooks: Dict[str, AgentHook] = {}
        self._load()

    def _load(self) -> None:
        file = self.hooks_dir / "hooks.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for hid, hd in data.items():
                        self.hooks[hid] = AgentHook(**hd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.hooks_dir / "hooks.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.hooks.items()}, f, indent=2)

    def register_hook(self, hook_id: str, target_platform: str, hook_type: str,
                      script_content: str, priority: int = 50) -> Optional[AgentHook]:
        if target_platform not in self.SUPPORTED_PLATFORMS or hook_type not in self.HOOK_TYPES:
            return None
        hook = AgentHook(
            hook_id=hook_id, target_platform=target_platform, hook_type=hook_type,
            script_content=script_content, priority=priority, is_active=True,
        )
        self.hooks[hook_id] = hook
        self._save()
        return hook

    def unregister_hook(self, hook_id: str) -> bool:
        if hook_id in self.hooks:
            del self.hooks[hook_id]
            self._save()
            return True
        return False

    def activate(self, hook_id: str) -> bool:
        hook = self.hooks.get(hook_id)
        if hook:
            hook.is_active = True
            self._save()
            return True
        return False

    def deactivate(self, hook_id: str) -> bool:
        hook = self.hooks.get(hook_id)
        if hook:
            hook.is_active = False
            self._save()
            return True
        return False

    def get_hooks_for_platform(self, platform: str, hook_type: Optional[str] = None) -> List[AgentHook]:
        result = [h for h in self.hooks.values() if h.target_platform == platform and h.is_active]
        if hook_type:
            result = [h for h in result if h.hook_type == hook_type]
        return sorted(result, key=lambda h: h.priority)

    def get_hooks_for_file(self, file_path: str) -> List[AgentHook]:
        """Get hooks that should trigger for a given file path."""
        return [h for h in self.hooks.values() if h.is_active and file_path in h.script_content]

    def generate_install_script(self, platform: str) -> str:
        """Generate installation script for a platform."""
        hooks = self.get_hooks_for_platform(platform)
        lines = [f"#!/bin/bash", f"# Install hooks for {platform}", ""]
        for hook in hooks:
            lines.append(f"# Hook: {hook.hook_id} ({hook.hook_type})")
            lines.append(hook.script_content)
            lines.append("")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        by_platform = {}
        for h in self.hooks.values():
            by_platform[h.target_platform] = by_platform.get(h.target_platform, 0) + 1
        active = sum(1 for h in self.hooks.values() if h.is_active)
        return {"total_hooks": len(self.hooks), "active": active, "by_platform": by_platform}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgentHookManager", "AgentHook"]