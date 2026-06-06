#!/usr/bin/env python3
"""
Prompt Version Control for MAGNATRIX-OS
Prompt versioning, A/B testing, rollback, metrics per version.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional


class PromptVersion:
    """Single prompt version."""

    def __init__(self, version_id: str, prompt_text: str, metadata: Dict[str, Any] = None) -> None:
        self.version_id = version_id
        self.prompt_text = prompt_text
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.hash = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]
        self.use_count = 0
        self.metrics = {'avg_latency': 0.0, 'success_rate': 1.0, 'user_rating': 0.0}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version_id': self.version_id,
            'hash': self.hash,
            'created_at': self.created_at,
            'use_count': self.use_count,
            'metrics': self.metrics,
        }


class PromptVersionControl:
    """Prompt version control system."""

    def __init__(self, storage_path: str = './prompts.json') -> None:
        self._storage_path = storage_path
        self._prompts: Dict[str, Dict[str, PromptVersion]] = {}  # prompt_name -> {version_id -> PromptVersion}
        self._active: Dict[str, str] = {}  # prompt_name -> active_version_id

    def create(self, prompt_name: str, prompt_text: str, metadata: Dict[str, Any] = None) -> str:
        version_id = f"v{len(self._prompts.get(prompt_name, {})) + 1}"
        version = PromptVersion(version_id, prompt_text, metadata)

        if prompt_name not in self._prompts:
            self._prompts[prompt_name] = {}

        self._prompts[prompt_name][version_id] = version
        self._active[prompt_name] = version_id
        self._save()
        return version_id

    def get(self, prompt_name: str, version_id: Optional[str] = None) -> Optional[str]:
        versions = self._prompts.get(prompt_name, {})
        if not versions:
            return None

        vid = version_id or self._active.get(prompt_name)
        if not vid or vid not in versions:
            return None

        versions[vid].use_count += 1
        return versions[vid].prompt_text

    def rollback(self, prompt_name: str, version_id: str) -> bool:
        if prompt_name in self._prompts and version_id in self._prompts[prompt_name]:
            self._active[prompt_name] = version_id
            self._save()
            return True
        return False

    def record_metrics(self, prompt_name: str, version_id: str, latency: float, success: bool, rating: float = 0.0) -> None:
        versions = self._prompts.get(prompt_name, {})
        if version_id not in versions:
            return

        v = versions[version_id]
        v.metrics['avg_latency'] = (v.metrics['avg_latency'] * v.use_count + latency) / (v.use_count + 1)
        v.metrics['success_rate'] = (v.metrics['success_rate'] * v.use_count + (1.0 if success else 0.0)) / (v.use_count + 1)
        if rating > 0:
            v.metrics['user_rating'] = (v.metrics['user_rating'] * v.use_count + rating) / (v.use_count + 1)

        self._save()

    def compare_versions(self, prompt_name: str) -> List[Dict[str, Any]]:
        versions = self._prompts.get(prompt_name, {})
        return [v.to_dict() for v in versions.values()]

    def list_prompts(self) -> List[str]:
        return list(self._prompts.keys())

    def _save(self) -> None:
        data = {
            name: {vid: v.to_dict() for vid, v in versions.items()}
            for name, versions in self._prompts.items()
        }
        data['_active'] = self._active
        with open(self._storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        import os
        if not os.path.exists(self._storage_path):
            return
        with open(self._storage_path, 'r') as f:
            data = json.load(f)
        self._active = data.pop('_active', {})


def _demo() -> None:
    print("=== Prompt Version Control Demo ===\n")

    pvc = PromptVersionControl('/tmp/prompt_vcs.json')

    # Create versions
    v1 = pvc.create('summarize', 'Summarize the following text in 3 sentences:')
    v2 = pvc.create('summarize', 'Provide a concise summary (max 3 sentences) of the following:')
    v3 = pvc.create('summarize', 'TL;DR: Summarize in 3 sentences:')

    print(f"Created versions: {v1}, {v2}, {v3}")
    print(f"Active: {pvc._active.get('summarize')}")

    # Use prompt
    prompt = pvc.get('summarize')
    print(f"Current prompt: {prompt}")

    # Record metrics
    pvc.record_metrics('summarize', v1, 1.2, True, 4.5)
    pvc.record_metrics('summarize', v2, 0.8, True, 4.8)
    pvc.record_metrics('summarize', v3, 2.1, False, 2.0)

    # Compare
    print("\nVersion comparison:")
    for v in pvc.compare_versions('summarize'):
        print(f"  {v['version_id']}: uses={v['use_count']}, latency={v['metrics']['avg_latency']:.2f}, success={v['metrics']['success_rate']:.2f}, rating={v['metrics']['user_rating']:.2f}")

    # Rollback
    pvc.rollback('summarize', v1)
    print(f"\nRolled back to {v1}")
    print(f"Active: {pvc._active.get('summarize')}")

    print("\n=== Prompt Version Control Demo Complete ===")


if __name__ == '__main__':
    _demo()
