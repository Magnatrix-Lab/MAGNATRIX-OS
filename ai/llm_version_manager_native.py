"""LLM Version Manager — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class VersionStatus(Enum):
    DRAFT = auto()
    RELEASED = auto()
    DEPRECATED = auto()
    RETIRED = auto()

@dataclass
class VersionInfo:
    id: str
    version: str
    status: VersionStatus
    changelog: str = ""
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class VersionManager:
    def __init__(self) -> None:
        self._versions: Dict[str, List[VersionInfo]] = {}
        self._current: Dict[str, str] = {}

    def add(self, component_id: str, version: VersionInfo) -> None:
        if component_id not in self._versions:
            self._versions[component_id] = []
        self._versions[component_id].append(version)
        self._current[component_id] = version.version

    def get_current(self, component_id: str) -> Optional[VersionInfo]:
        versions = self._versions.get(component_id, [])
        current_ver = self._current.get(component_id)
        for v in versions:
            if v.version == current_ver:
                return v
        return None

    def get_history(self, component_id: str) -> List[VersionInfo]:
        return list(self._versions.get(component_id, []))

    def deprecate(self, component_id: str, version: str) -> bool:
        versions = self._versions.get(component_id, [])
        for v in versions:
            if v.version == version:
                v.status = VersionStatus.DEPRECATED
                return True
        return False

    def compare(self, v1: str, v2: str) -> int:
        p1 = [int(x) for x in v1.split(".")]
        p2 = [int(x) for x in v2.split(".")]
        for a, b in zip(p1, p2):
            if a < b:
                return -1
            if a > b:
                return 1
        if len(p1) < len(p2):
            return -1
        if len(p1) > len(p2):
            return 1
        return 0

    def get_stats(self) -> Dict[str, Any]:
        return {"components": len(self._versions), "total_versions": sum(len(vs) for vs in self._versions.values()), "current": len(self._current)}

def run() -> None:
    print("Version Manager test")
    e = VersionManager()
    e.add("core", VersionInfo("v1", "1.0.0", VersionStatus.RELEASED, "Initial release"))
    e.add("core", VersionInfo("v2", "1.1.0", VersionStatus.RELEASED, "Added streaming"))
    e.add("core", VersionInfo("v3", "2.0.0", VersionStatus.RELEASED, "Breaking changes"))
    print("  Current: " + e.get_current("core").version)
    e.deprecate("core", "1.0.0")
    print("  Compare 1.0.0 vs 2.0.0: " + str(e.compare("1.0.0", "2.0.0")))
    print("  Stats: " + str(e.get_stats()))
    print("Version Manager test complete.")

if __name__ == "__main__":
    run()
