"""
ACS Manifest Resolver — MAGNATRIX-OS Governance Layer
Resolve, merge, scope policy manifests dari folder/file.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import json
import os
import glob
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ResolvedManifest:
    """Manifest yang sudah di-resolve (single unified dict)."""
    version: str
    metadata: Dict[str, Any]
    policies: Dict[str, Any]
    intervention_points: Dict[str, Any]
    tools: Dict[str, Any]
    approval: Optional[Dict[str, Any]] = None
    source_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "agent_control_specification_version": self.version,
            "metadata": self.metadata,
            "policies": self.policies,
            "intervention_points": self.intervention_points,
            "tools": self.tools,
        }
        if self.approval:
            result["approval"] = self.approval
        return result


class ManifestResolver:
    """
    Resolve policy manifests dari folder.
    - Discovery: scan folder untuk *.yaml, *.json, *.yml
    - Scope: filter manifest berdasarkan scope (agent, tool, global)
    - Merge: merge parent-child inheritance
    - Bind: bind intervention points ke policy
    """

    def __init__(self, manifest_dir: str = "./policies") -> None:
        self.manifest_dir = manifest_dir
        self._cache: Dict[str, ResolvedManifest] = {}

    def discover(self) -> List[str]:
        """Discover semua manifest files di folder."""
        if not os.path.isdir(self.manifest_dir):
            return []
        patterns = ["*.json", "*.yaml", "*.yml"]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(self.manifest_dir, pattern)))
        return sorted(files)

    def load_file(self, filepath: str) -> Dict[str, Any]:
        """Load single manifest file."""
        with open(filepath, "r") as f:
            if filepath.endswith(".json"):
                return json.load(f)
            else:
                # Simple YAML-like parser (no PyYAML dependency)
                return self._parse_yaml_like(f.read())

    def _parse_yaml_like(self, text: str) -> Dict[str, Any]:
        """Parse sederhana YAML-like: key: value atau nested dengan indent."""
        result: Dict[str, Any] = {}
        current = result
        stack = [(0, current)]
        last_key = None

        for line in text.strip().splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            stripped = line.strip()

            if ":" in stripped:
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip()

                # Pop stack hingga level yang tepat
                while stack and stack[-1][0] >= indent:
                    stack.pop()
                if stack:
                    current = stack[-1][1]
                else:
                    current = result

                if val:
                    # Scalar value
                    try:
                        current[key] = json.loads(val)
                    except json.JSONDecodeError:
                        current[key] = val
                else:
                    # Nested dict
                    current[key] = {}
                    stack.append((indent, current[key]))
                    last_key = key
            elif stripped.startswith("-"):
                # List item — simplified
                item = stripped[1:].strip()
                if last_key and isinstance(current.get(last_key), list):
                    current[last_key].append(item)
                else:
                    current[last_key] = [item]

        return result

    def resolve(self, scope: Optional[str] = None) -> ResolvedManifest:
        """
        Resolve semua manifest files menjadi single unified manifest.
        - Merge parent-child (extends)
        - Filter by scope
        - Bind intervention points
        """
        files = self.discover()
        manifests: List[Dict[str, Any]] = []
        for f in files:
            try:
                manifest = self.load_file(f)
                if scope:
                    manifest_scope = manifest.get("metadata", {}).get("scope", "global")
                    if manifest_scope != scope and manifest_scope != "global":
                        continue
                manifests.append(manifest)
            except Exception:
                continue

        # Merge
        merged = self._merge_manifests(manifests)
        resolved = ResolvedManifest(
            version=merged.get("agent_control_specification_version", "0.1.0"),
            metadata=merged.get("metadata", {}),
            policies=merged.get("policies", {}),
            intervention_points=merged.get("intervention_points", {}),
            tools=merged.get("tools", {}),
            approval=merged.get("approval"),
            source_files=files,
        )
        self._cache[scope or "global"] = resolved
        return resolved

    def _merge_manifests(self, manifests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple manifests. Later manifests override earlier ones."""
        merged: Dict[str, Any] = {
            "agent_control_specification_version": "0.1.0",
            "metadata": {},
            "policies": {},
            "intervention_points": {},
            "tools": {},
        }
        for manifest in manifests:
            # Merge metadata
            merged["metadata"].update(manifest.get("metadata", {}))
            # Merge policies
            merged["policies"].update(manifest.get("policies", {}))
            # Merge intervention points (deep merge)
            for point, binding in manifest.get("intervention_points", {}).items():
                if point not in merged["intervention_points"]:
                    merged["intervention_points"][point] = binding
                else:
                    # Override dengan manifest yang lebih spesifik
                    merged["intervention_points"][point].update(binding)
            # Merge tools
            merged["tools"].update(manifest.get("tools", {}))
            # Version — ambil highest
            v = manifest.get("agent_control_specification_version", "")
            if v and v > merged["agent_control_specification_version"]:
                merged["agent_control_specification_version"] = v
        return merged

    def get_bindings(self, resolved: ResolvedManifest) -> List[Dict[str, Any]]:
        """Extract intervention point bindings dari resolved manifest."""
        bindings = []
        for point, config in resolved.intervention_points.items():
            policy_id = config.get("policy", {}).get("id", "")
            bindings.append({
                "point": point,
                "policy_id": policy_id,
                "policy_target": config.get("policy_target", ""),
                "policy_target_kind": config.get("policy_target_kind", "snapshot"),
                "tool_name_from": config.get("tool_name_from", ""),
            })
        return bindings

    def stats(self) -> Dict[str, Any]:
        return {
            "manifest_dir": self.manifest_dir,
            "cached_manifests": len(self._cache),
            "discovered_files": len(self.discover()),
        }


def run():
    print("=" * 60)
    print("ACS Manifest Resolver — Demo")
    print("=" * 60)

    # Create a temp manifest directory with test files
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write a simple JSON manifest
        manifest1 = {
            "agent_control_specification_version": "0.1.0",
            "metadata": {"name": "email-agent", "scope": "global"},
            "policies": {
                "email_policy": {"type": "custom", "rules": ["block_external"]}
            },
            "intervention_points": {
                "pre_tool_call": {
                    "policy": {"id": "email_policy"},
                    "policy_target": "$.tool_call",
                }
            },
            "tools": {
                "send_email": {"type": "Tool", "clearance": "internal"}
            },
        }
        with open(os.path.join(tmpdir, "manifest1.json"), "w") as f:
            json.dump(manifest1, f)

        resolver = ManifestResolver(tmpdir)
        print(f"\nDiscovered: {resolver.discover()}")

        resolved = resolver.resolve()
        print(f"\nResolved version: {resolved.version}")
        print(f"Policies: {list(resolved.policies.keys())}")
        print(f"Bindings: {resolver.get_bindings(resolved)}")
        print(f"Tools: {resolved.tools}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
