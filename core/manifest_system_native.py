#!/usr/bin/env python3
"""manifest_system_native.py -- MAGNATRIX-OS Module Manifest System (Claw Bundle)

MODULE_SPEC_v0.1 real implementation: module.json + handler.py registration,
metadata, version, dependencies, lifecycle hooks. Pure stdlib.
"""
from __future__ import annotations
import ast
import json
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

@dataclass
class ModuleManifest:
    id: str; name: str; version: str; description: str; domain: str
    entry_point: str; class_name: str
    dependencies: List[str] = field(default_factory=list)
    required_env: List[str] = field(default_factory=list)
    lifecycle_hooks: Dict[str, str] = field(default_factory=dict)
    api_surface: List[str] = field(default_factory=list)
    author: str = ""; license: str = "MIT"; tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: str = "registered"

@dataclass
class DependencyGraph:
    modules: List[str] = field(default_factory=list)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    cycles: List[List[str]] = field(default_factory=list)
    load_order: List[str] = field(default_factory=list)

class ManifestSystemNative:
    def __init__(self, workspace: str = "./manifests", module_dir: str = "./core") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self.module_dir = Path(module_dir); self._manifests: Dict[str, ModuleManifest] = {}
        self._lock = threading.RLock(); self._manifests_path = self.workspace / "manifests.json"
        self._load()

    def _load(self) -> None:
        if self._manifests_path.exists():
            try:
                with open(self._manifests_path, "r", encoding="utf-8") as f: data = json.load(f)
                for mid, md in data.items(): self._manifests[mid] = ModuleManifest(**md)
            except Exception: pass

    def _save(self) -> None:
        with open(self._manifests_path, "w", encoding="utf-8") as f:
            json.dump({mid: asdict(m) for mid, m in self._manifests.items()}, f, indent=2, default=str)

    def register(self, name: str, version: str, description: str, domain: str, entry_point: str, class_name: str, dependencies: Optional[List[str]] = None, required_env: Optional[List[str]] = None, lifecycle_hooks: Optional[Dict[str, str]] = None, api_surface: Optional[List[str]] = None, author: str = "", license: str = "MIT", tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        with self._lock:
            mid = f"manifest_{name}_{version}"
            if mid in self._manifests: return mid
            manifest = ModuleManifest(id=mid, name=name, version=version, description=description, domain=domain, entry_point=entry_point, class_name=class_name, dependencies=dependencies or [], required_env=required_env or [], lifecycle_hooks=lifecycle_hooks or {}, api_surface=api_surface or [], author=author, license=license, tags=tags or [], metadata=metadata or {})
            self._manifests[mid] = manifest; self._save(); return mid

    def auto_register(self, module_path: Path) -> Optional[str]:
        with self._lock:
            name = module_path.stem.replace("_native", ""); domain_map = {"vector_memory": "language", "knowledge_graph": "language", "identity": "language", "checkpoint": "language", "task_scheduler": "formal", "agent_messaging": "formal", "rbac": "formal", "security_scanner": "formal", "metrics_collector": "formal", "modularity_analyzer": "formal", "network_topology": "formal", "domain_isolation_test": "formal", "llm_gateway": "physical", "answer_fusion": "physical", "auto_recovery": "physical", "boot_optimizer": "physical", "deliberation_engine": "social", "human_in_loop": "social", "chat_interface": "social"}
            domain = "unknown"
            for key, d in domain_map.items():
                if key in name: domain = d; break
            try:
                with open(module_path, "r", encoding="utf-8") as f: tree = ast.parse(f.read())
                classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and ("Native" in node.name or "Engine" in node.name or "Manager" in node.name)]
                class_name = classes[0] if classes else "Unknown"
            except Exception: class_name = "Unknown"
            return self.register(name, "1.0.0", f"Auto-registered {name}", domain, str(module_path), class_name, tags=["auto"])

    def scan_and_register(self) -> int:
        count = 0
        if not self.module_dir.exists(): return 0
        for py_file in self.module_dir.rglob("*.py"):
            if py_file.name.startswith("_") or "_native" not in py_file.stem: continue
            result = self.auto_register(py_file)
            if result: count += 1
        return count

    def get_manifest(self, mid: str) -> Optional[ModuleManifest]:
        with self._lock: return self._manifests.get(mid)

    def get_by_name(self, name: str) -> Optional[ModuleManifest]:
        with self._lock:
            for m in self._manifests.values():
                if m.name == name: return m
            return None

    def list_manifests(self, domain: Optional[str] = None, status: Optional[str] = None) -> List[ModuleManifest]:
        with self._lock:
            result = list(self._manifests.values())
            if domain: result = [m for m in result if m.domain == domain]
            if status: result = [m for m in result if m.status == status]
            return result

    def update_status(self, mid: str, status: str) -> bool:
        with self._lock:
            if mid not in self._manifests: return False
            self._manifests[mid].status = status; self._manifests[mid].updated_at = time.time(); self._save(); return True

    def build_dependency_graph(self) -> DependencyGraph:
        with self._lock:
            modules = [m.name for m in self._manifests.values()]; edges = []
            for m in self._manifests.values():
                for dep in m.dependencies:
                    if dep in modules: edges.append((dep, m.name))
            adj = {m: [] for m in modules}
            for dep, mod in edges: adj[dep].append(mod)
            visited = set(); rec_stack = set(); cycles = []
            def dfs(node, path):
                visited.add(node); rec_stack.add(node); path.append(node)
                for neighbor in adj.get(node, []):
                    if neighbor not in visited: dfs(neighbor, path)
                    elif neighbor in rec_stack:
                        cycle_start = path.index(neighbor)
                        cycles.append(path[cycle_start:] + [neighbor])
                path.pop(); rec_stack.discard(node)
            for m in modules:
                if m not in visited: dfs(m, [])
            in_degree = {m: 0 for m in modules}
            for dep, mod in edges: in_degree[mod] += 1
            queue = [m for m in modules if in_degree[m] == 0]; load_order = []
            while queue:
                node = queue.pop(0); load_order.append(node)
                for neighbor in adj.get(node, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0: queue.append(neighbor)
            for m in modules:
                if m not in load_order: load_order.append(m)
            return DependencyGraph(modules=modules, edges=edges, cycles=cycles, load_order=load_order)

    def get_load_order(self) -> List[str]: return self.build_dependency_graph().load_order
    def get_cycles(self) -> List[List[str]]: return self.build_dependency_graph().cycles

    def validate(self) -> List[str]:
        issues = []; graph = self.build_dependency_graph()
        if graph.cycles: issues.append(f"Circular dependencies detected: {graph.cycles}")
        for m in self._manifests.values():
            ep = Path(m.entry_point)
            if not ep.exists(): issues.append(f"[{m.name}] Entry point missing: {m.entry_point}")
            for dep in m.dependencies:
                if not self.get_by_name(dep): issues.append(f"[{m.name}] Missing dependency: {dep}")
            for env in m.required_env:
                if not __import__("os").environ.get(env): issues.append(f"[{m.name}] Missing env var: {env}")
        return issues

    def print_summary(self) -> str:
        graph = self.build_dependency_graph()
        lines = ["=== Module Manifest Summary ===", f"Total Modules: {len(self._manifests)}", f"Domains: {', '.join(set(m.domain for m in self._manifests.values()))}", f"Cycles: {len(graph.cycles)}", f"Load Order: {graph.load_order[:10]}{'...' if len(graph.load_order) > 10 else ''}", "
--- Validation Issues ---"]
        issues = self.validate()
        if issues: lines.extend([f"  ! {i}" for i in issues[:10]])
        else: lines.append("  o All manifests valid")
        lines.append("
--- Modules by Domain ---")
        domains = {}
        for m in self._manifests.values(): domains.setdefault(m.domain, []).append(m.name)
        for d, mods in domains.items(): lines.append(f"  {d}: {', '.join(mods[:5])}{'...' if len(mods) > 5 else ''}")
        return "
".join(lines)

    def export_bundle(self, mid: str, output_dir: Optional[str] = None) -> str:
        with self._lock:
            if mid not in self._manifests: return ""
            m = self._manifests[mid]
            out = Path(output_dir) if output_dir else self.workspace / "bundles" / m.name
            out.mkdir(parents=True, exist_ok=True)
            manifest_path = out / "module.json"
            with open(manifest_path, "w", encoding="utf-8") as f: json.dump(asdict(m), f, indent=2, default=str)
            handler_src = Path(m.entry_point); handler_dst = out / "handler.py"
            if handler_src.exists(): shutil.copy2(handler_src, handler_dst)
            return str(out)

    def import_bundle(self, bundle_dir: str) -> Optional[str]:
        manifest_path = Path(bundle_dir) / "module.json"
        if not manifest_path.exists(): return None
        with open(manifest_path, "r", encoding="utf-8") as f: data = json.load(f)
        return self.register(**{k: v for k, v in data.items() if k not in ["id", "status", "created_at", "updated_at"]})

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            domains = {}; statuses = {}
            for m in self._manifests.values(): domains[m.domain] = domains.get(m.domain, 0) + 1; statuses[m.status] = statuses.get(m.status, 0) + 1
            return {"total": len(self._manifests), "domains": domains, "statuses": statuses, "cycles": len(self.get_cycles())}

if __name__ == "__main__":
    ms = ManifestSystemNative(module_dir=".")
    ms.scan_and_register()
    print(ms.print_summary())
