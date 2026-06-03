"""LLM Prompt Versioning — Native Python (stdlib only)."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class PromptVersion:
    id: str
    prompt_text: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class PromptVersioning:
    def __init__(self) -> None:
        self._versions: Dict[str, List[PromptVersion]] = {}
        self._current: Dict[str, str] = {}

    def add_version(self, prompt_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> PromptVersion:
        version = PromptVersion(
            id=prompt_id + "_v" + str(len(self._versions.get(prompt_id, [])) + 1),
            prompt_text=text,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        if prompt_id not in self._versions:
            self._versions[prompt_id] = []
        self._versions[prompt_id].append(version)
        self._current[prompt_id] = version.id
        return version

    def get_current(self, prompt_id: str) -> Optional[PromptVersion]:
        if prompt_id not in self._versions:
            return None
        current_id = self._current.get(prompt_id)
        for v in self._versions[prompt_id]:
            if v.id == current_id:
                return v
        return None

    def rollback(self, prompt_id: str, version_id: str) -> bool:
        if prompt_id not in self._versions:
            return False
        for v in self._versions[prompt_id]:
            if v.id == version_id:
                self._current[prompt_id] = version_id
                return True
        return False

    def diff(self, prompt_id: str, v1: str, v2: str) -> List[str]:
        versions = self._versions.get(prompt_id, [])
        text1 = next((v.prompt_text for v in versions if v.id == v1), "")
        text2 = next((v.prompt_text for v in versions if v.id == v2), "")
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        max_len = max(len(lines1), len(lines2))
        diff = []
        for i in range(max_len):
            l1 = lines1[i] if i < len(lines1) else ""
            l2 = lines2[i] if i < len(lines2) else ""
            if l1 != l2:
                diff.append("Line " + str(i + 1) + " changed: '" + l1 + "' -> '" + l2 + "'")
        return diff

    def get_stats(self) -> Dict[str, Any]:
        return {"prompts": len(self._versions), "total_versions": sum(len(vs) for vs in self._versions.values())}

def run() -> None:
    print("Prompt Versioning test")
    e = PromptVersioning()
    e.add_version("p1", "You are a helpful assistant.")
    e.add_version("p1", "You are a helpful and creative assistant.")
    e.add_version("p1", "You are a helpful, creative, and precise assistant.")
    print("  Current: " + e.get_current("p1").prompt_text)
    e.rollback("p1", "p1_v1")
    print("  After rollback: " + e.get_current("p1").prompt_text)
    diffs = e.diff("p1", "p1_v1", "p1_v3")
    print("  Diff count: " + str(len(diffs)))
    print("Prompt Versioning test complete.")

if __name__ == "__main__":
    run()
