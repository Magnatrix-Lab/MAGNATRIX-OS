
"""
browser_context_manager_native.py
MAGNATRIX-OS — Browser Context Manager

Inspired by Hermes Browser Extension v0.1.6 context control:
- Follow active tab or pin to specific tab
- Selectable open-tab context with tab picker
- Per-tab context tracking with context switching

Pure Python standard library.
"""

import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path


class ContextMode(Enum):
    FOLLOW_ACTIVE = auto()
    PINNED = auto()


@dataclass
class BrowserTab:
    tab_id: str
    title: str
    url: str
    favicon: str = ""
    is_active: bool = False
    is_pinned: bool = False
    is_selected: bool = False
    last_accessed: str = ""
    content_summary: str = ""


@dataclass
class TabContext:
    context_id: str
    mode: ContextMode = ContextMode.FOLLOW_ACTIVE
    pinned_tab_id: Optional[str] = None
    selected_tab_ids: Set[str] = field(default_factory=set)
    active_tab_id: Optional[str] = None
    last_updated: str = ""


class BrowserContextManager:
    """Manage browser tab context for AI assistant integration."""

    def __init__(self, state_file: str = "browser_context.json"):
        self.state_file = Path(state_file)
        self.tabs: Dict[str, BrowserTab] = {}
        self.context = TabContext(context_id="default")
        self._load_state()

    def _load_state(self) -> None:
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.context = TabContext(
                    context_id=data.get("context_id", "default"),
                    mode=ContextMode[data.get("mode", "FOLLOW_ACTIVE")],
                    pinned_tab_id=data.get("pinned_tab_id"),
                    selected_tab_ids=set(data.get("selected_tab_ids", [])),
                    active_tab_id=data.get("active_tab_id"),
                )
                for t in data.get("tabs", []):
                    self.tabs[t["tab_id"]] = BrowserTab(**t)

    def _save_state(self) -> None:
        data = {
            "context_id": self.context.context_id,
            "mode": self.context.mode.name,
            "pinned_tab_id": self.context.pinned_tab_id,
            "selected_tab_ids": list(self.context.selected_tab_ids),
            "active_tab_id": self.context.active_tab_id,
            "tabs": [asdict(t) for t in self.tabs.values()],
            "last_updated": datetime.now().isoformat(),
        }
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def set_mode(self, mode: ContextMode, pinned_tab_id: Optional[str] = None) -> None:
        self.context.mode = mode
        if mode == ContextMode.PINNED and pinned_tab_id:
            self.context.pinned_tab_id = pinned_tab_id
        self.context.last_updated = datetime.now().isoformat()
        self._save_state()

    def update_tab(self, tab: BrowserTab) -> None:
        self.tabs[tab.tab_id] = tab
        if tab.is_active:
            self.context.active_tab_id = tab.tab_id
        self._save_state()

    def select_tab(self, tab_id: str) -> None:
        self.context.selected_tab_ids.add(tab_id)
        self._save_state()

    def deselect_tab(self, tab_id: str) -> None:
        self.context.selected_tab_ids.discard(tab_id)
        self._save_state()

    def select_all(self) -> None:
        self.context.selected_tab_ids = set(self.tabs.keys())
        self._save_state()

    def deselect_all(self) -> None:
        self.context.selected_tab_ids.clear()
        self._save_state()

    def get_contextual_tabs(self) -> List[BrowserTab]:
        """Return tabs that should be in the AI context."""
        if self.context.mode == ContextMode.PINNED and self.context.pinned_tab_id:
            if self.context.pinned_tab_id in self.tabs:
                return [self.tabs[self.context.pinned_tab_id]]
            return []
        # Follow active mode: return selected tabs + active tab
        result = []
        for tab_id in self.context.selected_tab_ids:
            if tab_id in self.tabs:
                result.append(self.tabs[tab_id])
        if self.context.active_tab_id and self.context.active_tab_id not in self.context.selected_tab_ids:
            if self.context.active_tab_id in self.tabs:
                result.append(self.tabs[self.context.active_tab_id])
        return result

    def build_prompt_context(self) -> str:
        """Build prompt context from contextual tabs."""
        tabs = self.get_contextual_tabs()
        lines = ["## Browser Context", ""]
        for tab in tabs:
            lines.append(f"- **{tab.title}** ({tab.url})")
            if tab.content_summary:
                lines.append(f"  Summary: {tab.content_summary[:200]}")
        lines.append("")
        lines.append(f"Mode: {self.context.mode.name}")
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "mode": self.context.mode.name,
            "tab_count": len(self.tabs),
            "selected_count": len(self.context.selected_tab_ids),
            "contextual_tabs": len(self.get_contextual_tabs()),
        }


__all__ = ["BrowserContextManager", "BrowserTab", "TabContext", "ContextMode"]
