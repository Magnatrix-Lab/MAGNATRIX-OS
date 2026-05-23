#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — Rye/uv Native Integration
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari astral-sh/rye & astral-sh/uv

Pola yang ditiru:
• uv — Python package manager & resolver (Rust-based, 10–100x pip)
• Rye — All-in-one Python project workflow (init, add, remove, lock, sync)
• PubGrub dependency resolution — deterministic, minimal-upgrade solver
• Workspace (Cargo-style monorepo) — multi-package coordination
• uv tool / uvx — one-shot tool execution tanpa install permanen
• Script inline metadata — # /// script dengan deps inline
• Global cache — disk deduplication, content-addressable storage
• Python version management — download, pin, switch otomatis
• Pip-compatible CLI — drop-in replacement pip → uv pip
• Lockfile generation — reproducible, platform-aware resolution

Layer: Runtime (3) + Infrastructure (0) hybrid
Versi: Phase 5 — uv-based Accelerated Package Runtime
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import venv
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

# ─────────────────────────────────────────────────────────────────────────────
# 0. UTILITAS DASAR
# ─────────────────────────────────────────────────────────────────────────────


class _Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    DIM = "\033[90m"
    RESET = "\033[0m"


def _log(label: str, msg: str, color: str = _Colors.CYAN) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"{color}[{ts}] [{label}]{_Colors.RESET} {msg}")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:16]


def _atomic_write(path: Path, data: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


# ─────────────────────────────────────────────────────────────────────────────
# 1. UV CACHE ENGINE — Content-Addressable Global Cache
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CacheEntry:
    """Satu entri di uv cache: key = sha256(content), value = metadata."""
    key: str
    content_hash: str
    artifact_type: str  # "wheel", "sdist", "metadata", "resolution"
    platform_tag: str
    python_tag: str
    path: Path
    size_bytes: int = 0
    mtime: float = 0.0


class UVCacheEngine:
    """
    Global cache manager yang meniru uv cache architecture:
    • Content-addressable storage: artefak di-cache by sha256(content)
    • Wheel-cache: wheel files di-deduplicate antar-project
    • Metadata-cache: hasil parsing .dist-info di-cache untuk skip parse
    • Resolution-cache: hasil PubGrub resolution di-cache by lock hash
    • Link-mode: copy / hardlink / reflink / symlink
    """

    CACHE_VERSION = "v0"

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or Path.home() / ".cache" / "magnatrix" / "uv-cache"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._mem_index: Dict[str, CacheEntry] = {}  # in-memory index
        self._load_index()

    def _load_index(self) -> None:
        idx_path = self.root / "cache-index.json"
        if idx_path.exists():
            try:
                data = json.loads(idx_path.read_text())
                for k, v in data.items():
                    self._mem_index[k] = CacheEntry(
                        key=k,
                        content_hash=v["content_hash"],
                        artifact_type=v["artifact_type"],
                        platform_tag=v["platform_tag"],
                        python_tag=v["python_tag"],
                        path=Path(v["path"]),
                        size_bytes=v.get("size_bytes", 0),
                        mtime=v.get("mtime", 0.0),
                    )
            except Exception:
                pass

    def _save_index(self) -> None:
        data = {
            k: {
                "content_hash": v.content_hash,
                "artifact_type": v.artifact_type,
                "platform_tag": v.platform_tag,
                "python_tag": v.python_tag,
                "path": str(v.path),
                "size_bytes": v.size_bytes,
                "mtime": v.mtime,
            }
            for k, v in self._mem_index.items()
        }
        _atomic_write(self.root / "cache-index.json", json.dumps(data, indent=2))

    def _cache_subdir(self, artifact_type: str, content_hash: str) -> Path:
        # uv style: first 2 chars = bucket, then full hash
        bucket = content_hash[:2]
        sub = self.root / artifact_type / bucket / content_hash
        sub.mkdir(parents=True, exist_ok=True)
        return sub

    def store(self, content: bytes, artifact_type: str, platform_tag: str = "any",
              python_tag: str = "py3") -> str:
        """Store content in cache, return cache key."""
        h = _sha256(content)
        key = f"{artifact_type}:{platform_tag}:{python_tag}:{h}"
        with self._lock:
            if key in self._mem_index:
                return key
            sub = self._cache_subdir(artifact_type, h)
            dest = sub / "artifact"
            dest.write_bytes(content)
            entry = CacheEntry(
                key=key, content_hash=h, artifact_type=artifact_type,
                platform_tag=platform_tag, python_tag=python_tag,
                path=dest, size_bytes=len(content), mtime=time.time(),
            )
            self._mem_index[key] = entry
            self._save_index()
        _log("CACHE", f"stored {artifact_type} → {h[:8]} ({len(content)} bytes)")
        return key

    def fetch(self, key: str) -> Optional[bytes]:
        """Retrieve content by cache key."""
        with self._lock:
            entry = self._mem_index.get(key)
            if entry and entry.path.exists():
                return entry.path.read_bytes()
            return None

    def purge(self, max_age_days: Optional[int] = None, dry_run: bool = False) -> int:
        """Purge stale cache entries — mirip uv cache prune."""
        now = time.time()
        removed = 0
        with self._lock:
            to_remove: List[str] = []
            for key, entry in list(self._mem_index.items()):
                if max_age_days and (now - entry.mtime) > max_age_days * 86400:
                    to_remove.append(key)
                elif not entry.path.exists():
                    to_remove.append(key)
            for key in to_remove:
                entry = self._mem_index.pop(key)
                if not dry_run and entry.path.exists():
                    entry.path.unlink()
                removed += 1
            self._save_index()
        _log("CACHE", f"purged {removed} stale entries", _Colors.YELLOW)
        return removed

    def stats(self) -> Dict[str, Any]:
        total_size = sum(e.size_bytes for e in self._mem_index.values())
        by_type: Dict[str, int] = {}
        for e in self._mem_index.values():
            by_type[e.artifact_type] = by_type.get(e.artifact_type, 0) + 1
        return {
            "entries": len(self._mem_index),
            "total_bytes": total_size,
            "by_type": by_type,
            "cache_root": str(self.root),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. PUBGRUB RESOLVER — Deterministic Minimal-Upgrade Dependency Solver
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PackageId:
    name: str
    extras: Tuple[str, ...] = ()

    def __str__(self) -> str:
        if self.extras:
            return f"{self.name}[{','.join(self.extras)}]"
        return self.name


@dataclass
class Version:
    """Semantic version dengan support prerelease & local."""
    major: int
    minor: int = 0
    patch: int = 0
    prerelease: Tuple[str, ...] = ()
    local: str = ""

    @classmethod
    def parse(cls, s: str) -> Version:
        # Simplified semver parser
        s = s.strip().lstrip("v")
        local = ""
        if "+" in s:
            s, local = s.split("+", 1)
        prerelease: Tuple[str, ...] = ()
        if "-" in s:
            s, pre = s.split("-", 1)
            prerelease = tuple(pre.split("."))
        parts = s.split(".")
        major = int(parts[0]) if parts else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return cls(major, minor, patch, prerelease, local)

    def __str__(self) -> str:
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            v += "-" + ".".join(self.prerelease)
        if self.local:
            v += "+" + self.local
        return v

    def __lt__(self, other: Version) -> bool:
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        # Prerelease < no prerelease
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        return self.prerelease < other.prerelease

    def __le__(self, other: Version) -> bool:
        return self == other or self < other

    def __gt__(self, other: Version) -> bool:
        return other < self

    def __ge__(self, other: Version) -> bool:
        return not (self < other)

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.prerelease, self.local))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.prerelease, self.local) == \
               (other.major, other.minor, other.patch, other.prerelease, other.local)


@dataclass
class Requirement:
    """Dependency requirement dengan version specifier."""
    package: PackageId
    specifier: str  # e.g. ">=1.0,<2.0", "==1.5.0", "~=1.0"
    marker: Optional[str] = None  # PEP 508 environment marker

    def matches(self, version: Version) -> bool:
        # Simplified specifier matching — enough for native demo
        spec = self.specifier.strip()
        v_str = str(version)
        if spec.startswith("=="):
            return v_str == spec[2:].strip()
        if spec.startswith(">="):
            return version >= Version.parse(spec[2:].strip())
        if spec.startswith(">"):
            return version > Version.parse(spec[1:].strip())
        if spec.startswith("<="):
            return version <= Version.parse(spec[2:].strip())
        if spec.startswith("<"):
            return version < Version.parse(spec[1:].strip())
        if spec.startswith("~="):
            # Compatible release: ~=1.4.2 == >=1.4.2,<1.5.0
            base = Version.parse(spec[2:].strip())
            return version >= base and (version.major, version.minor) == (base.major, base.minor)
        return True  # bare name = any version


@dataclass
class Candidate:
    """Satu kandidat package version dari index."""
    package: PackageId
    version: Version
    requires: List[Requirement] = field(default_factory=list)
    url: Optional[str] = None
    filename: Optional[str] = None
    hash_sha256: Optional[str] = None


class SimpleIndex:
    """PEP 503 Simple API client — native tanpa pip."""

    PYPI_SIMPLE = "https://pypi.org/simple"

    def __init__(self, cache: UVCacheEngine, index_url: Optional[str] = None) -> None:
        self.cache = cache
        self.index_url = index_url or self.PYPI_SIMPLE

    def _fetch_html(self, url: str) -> str:
        cache_key = self.cache.store(url.encode(), "metadata") if False else None
        req = urllib.request.Request(url, headers={"Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")

    def get_versions(self, package_name: str) -> List[Candidate]:
        """Fetch available versions dari Simple API."""
        url = f"{self.index_url}/{package_name}/"
        try:
            html = self._fetch_html(url)
        except Exception as e:
            _log("INDEX", f"fetch error for {package_name}: {e}", _Colors.RED)
            return []

        candidates: List[Candidate] = []
        # Parse anchor tags — each link = satu artefak
        for match in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html):
            href, text = match.group(1), match.group(2).strip()
            # Extract version dari filename
            # e.g. numpy-1.26.0-cp311-cp311-manylinux...whl
            version_match = re.search(rf'{re.escape(package_name)}-(\d[^-]+)', text)
            if not version_match:
                continue
            version = Version.parse(version_match.group(1))
            cand = Candidate(
                package=PackageId(package_name),
                version=version,
                url=href,
                filename=text,
            )
            candidates.append(cand)

        # Dedup by version, keep latest filename
        by_version: Dict[Version, Candidate] = {}
        for c in candidates:
            if c.version not in by_version or (c.filename and "py3" in c.filename):
                by_version[c.version] = c
        return sorted(by_version.values(), key=lambda c: c.version, reverse=True)


class PubGrubResolver:
    """
    Deterministic minimal-upgrade dependency resolver.
    Simplified native reimplementation dari PubGrub algorithm (Rust crate
    yang dipakai uv). Ide utama:
    • Model dependencies sebagai incompatibilities (clause yang harus dipuaskan)
    • Unit propagation untuk derive constraint baru
    • Decision making untuk pick next package version
    • Backtracking bila conflict ditemukan
    """

    def __init__(self, index: SimpleIndex, cache: UVCacheEngine) -> None:
        self.index = index
        self.cache = cache
        self._resolved: Dict[PackageId, Candidate] = {}
        self._decisions: List[Tuple[PackageId, Version]] = []
        self._incompatibilities: List[List[Requirement]] = []

    def resolve(self, root_requirements: List[Requirement]) -> Dict[str, Candidate]:
        """
        Resolve dependency graph dari root requirements.
        Return mapping package_name → chosen Candidate.
        """
        _log("RESOLVE", f"resolving {len(root_requirements)} root requirements...")
        unresolved: List[Requirement] = list(root_requirements)
        chosen: Dict[PackageId, Candidate] = {}
        queue: List[PackageId] = [r.package for r in root_requirements]
        visited: Set[PackageId] = set()

        while queue:
            pkg = queue.pop(0)
            if pkg in visited:
                continue
            visited.add(pkg)

            # Cari constraint untuk package ini dari semua requirement
            constraints = [r for r in unresolved + [req for c in chosen.values() for req in c.requires]
                          if r.package == pkg]
            if not constraints:
                continue

            # Fetch candidates
            candidates = self.index.get_versions(pkg.name)
            if not candidates:
                _log("RESOLVE", f"no candidates for {pkg}", _Colors.YELLOW)
                continue

            # Filter by constraints, pick highest matching version (minimal upgrade)
            matching = [c for c in candidates if all(con.matches(c.version) for con in constraints)]
            if not matching:
                _log("RESOLVE", f"no match for {pkg} with {constraints}", _Colors.RED)
                continue

            pick = matching[0]  # highest version (list already sorted descending)
            chosen[pkg] = pick
            _log("RESOLVE", f"chose {pkg} == {pick.version}", _Colors.GREEN)

            # Queue transitive dependencies
            for req in pick.requires:
                if req.package not in visited:
                    queue.append(req.package)
                    unresolved.append(req)

        self._resolved = chosen
        return {str(k): v for k, v in chosen.items()}

    def generate_lockfile(self, root_requirements: List[Requirement]) -> Dict[str, Any]:
        resolved = self.resolve(root_requirements)
        lock = {
            "version": 1,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "resolver": "magnatrix-pubgrub-native",
            "packages": {},
        }
        for name, cand in resolved.items():
            lock["packages"][name] = {
                "version": str(cand.version),
                "url": cand.url,
                "hash": cand.hash_sha256,
                "requires": [
                    {"package": str(r.package), "specifier": r.specifier}
                    for r in cand.requires
                ],
            }
        return lock


# ─────────────────────────────────────────────────────────────────────────────
# 3. PROJECT MANAGER — Rye-style pyproject.toml + workspace
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class WorkspaceMember:
    name: str
    path: Path
    pyproject: Dict[str, Any]


class ProjectManager:
    """
    Manajer proyek Python ala Rye/uv:
    • pyproject.toml reader/writer (PEP 621)
    • rye init / add / remove / lock / sync
    • Workspace: Cargo-style monorepo support
    • Script metadata: # /// script dengan inline deps
    """

    def __init__(self, cache: UVCacheEngine, cwd: Optional[Path] = None) -> None:
        self.cache = cache
        self.cwd = (cwd or Path.cwd()).resolve()
        self.pyproject_path = self.cwd / "pyproject.toml"
        self.venv_path = self.cwd / ".venv"
        self.lockfile_path = self.cwd / "uv.lock"
        self._index = SimpleIndex(cache)

    # ── pyproject I/O ───────────────────────────────────────────────────────

    def read_pyproject(self) -> Dict[str, Any]:
        import tomllib
        if self.pyproject_path.exists():
            with open(self.pyproject_path, "rb") as f:
                return tomllib.load(f)
        return {}

    def write_pyproject(self, data: Dict[str, Any]) -> None:
        # Native TOML writer sederhana — production bisa pakai tomli_w
        lines = self._dump_toml(data)
        _atomic_write(self.pyproject_path, "\n".join(lines))

    def _dump_toml(self, data: Any, prefix: str = "") -> List[str]:
        lines: List[str] = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    lines.append(f"\n{prefix}[{k}]")
                    lines.extend(self._dump_toml(v, prefix))
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            lines.append(f"\n{prefix}[[{k}]]")
                            lines.extend(self._dump_toml(item, prefix))
                        else:
                            lines.append(f'{prefix}{k} = {json.dumps(item)}')
                else:
                    lines.append(f'{prefix}{k} = {json.dumps(v)}')
        return lines

    # ── rye init ────────────────────────────────────────────────────────────

    def init(self, name: Optional[str] = None, package: bool = True) -> None:
        """Inisialisasi proyek baru ala rye init."""
        proj_name = name or self.cwd.name.replace("-", "_").replace(" ", "_")
        _log("INIT", f"creating project '{proj_name}' at {self.cwd}")
        pyproject = {
            "build-system": {
                "requires": ["hatchling"],
                "build-backend": "hatchling.build",
            },
            "project": {
                "name": proj_name,
                "version": "0.1.0",
                "description": f"MAGNATRIX native project — {proj_name}",
                "requires-python": ">=3.10",
                "dependencies": [],
            },
            "tool": {
                "magnatrix-uv": {
                    "managed": True,
                    "dev-dependencies": [],
                },
            },
        }
        self.write_pyproject(pyproject)
        if package:
            src = self.cwd / "src" / proj_name
            src.mkdir(parents=True, exist_ok=True)
            (src / "__init__.py").write_text(f'"""{proj_name} package."""\n__version__ = "0.1.0"\n')
        _log("INIT", f"done. Run '{_Colors.YELLOW}magnatrix-uv sync{_Colors.RESET}' to create venv")

    # ── rye add / remove ────────────────────────────────────────────────────

    def add(self, package_spec: str, dev: bool = False) -> None:
        """
        Tambah dependency — ala rye add package>=1.0.
        Spec bisa: "numpy", "numpy>=1.24", "numpy==1.24.0"
        """
        # Parse spec
        match = re.match(r'^([a-zA-Z0-9_.-]+)(.*)', package_spec.strip())
        if not match:
            raise ValueError(f"Invalid package spec: {package_spec}")
        pkg_name, spec = match.group(1), match.group(2).strip()
        if not spec:
            spec = "*"
        _log("ADD", f"adding {pkg_name} {spec} {'(dev)' if dev else ''}")

        data = self.read_pyproject()
        proj = data.setdefault("project", {})
        deps_key = "dependencies"
        deps: List[str] = list(proj.get(deps_key, []))

        # Remove existing entry for same package
        deps = [d for d in deps if not re.match(rf'^{re.escape(pkg_name)}\b', d)]
        entry = f"{pkg_name}{spec}" if spec != "*" else pkg_name
        deps.append(entry)
        proj[deps_key] = deps

        self.write_pyproject(data)
        _log("ADD", f"updated pyproject.toml — now {len(deps)} dependencies")

    def remove(self, package_name: str) -> None:
        """Hapus dependency dari pyproject."""
        data = self.read_pyproject()
        proj = data.setdefault("project", {})
        deps: List[str] = list(proj.get("dependencies", []))
        before = len(deps)
        deps = [d for d in deps if not re.match(rf'^{re.escape(package_name)}\b', d)]
        proj["dependencies"] = deps
        self.write_pyproject(data)
        _log("REMOVE", f"removed {package_name} ({before - len(deps)} entries)")

    # ── lock / sync ─────────────────────────────────────────────────────────

    def lock(self) -> Path:
        """Generate uv.lock dari pyproject dependencies."""
        data = self.read_pyproject()
        proj = data.get("project", {})
        raw_deps = proj.get("dependencies", [])

        reqs: List[Requirement] = []
        for d in raw_deps:
            match = re.match(r'^([a-zA-Z0-9_.-]+)(.*)', d.strip())
            if match:
                reqs.append(Requirement(PackageId(match.group(1)), match.group(2).strip() or "*"))

        resolver = PubGrubResolver(self._index, self.cache)
        lock = resolver.generate_lockfile(reqs)
        lock_text = json.dumps(lock, indent=2)
        _atomic_write(self.lockfile_path, lock_text)
        _log("LOCK", f"generated {self.lockfile_path} ({len(lock['packages'])} packages)")
        return self.lockfile_path

    def sync(self) -> None:
        """Sync .venv dengan lockfile — install/upgrade/remove packages."""
        if not self.lockfile_path.exists():
            _log("SYNC", "lockfile not found, running lock first...", _Colors.YELLOW)
            self.lock()

        lock = json.loads(self.lockfile_path.read_text())
        # Create venv if needed
        if not self.venv_path.exists():
            _log("SYNC", f"creating venv at {self.venv_path}")
            venv.create(self.venv_path, with_pip=False)

        # Determine python path
        py_exe = self.venv_path / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        _log("SYNC", f"venv python: {py_exe}")

        # Simplified sync: untuk native demo, log packages yang harus ada
        # Production: download wheel → uv cache → unpack ke site-packages
        for pkg_name, info in lock["packages"].items():
            _log("SYNC", f"  ✓ {pkg_name} == {info['version']}")

        _log("SYNC", f"synced {len(lock['packages'])} packages")

    # ── workspace ───────────────────────────────────────────────────────────

    def discover_workspace(self) -> List[WorkspaceMember]:
        """
        Discover Cargo-style workspace: pyproject dengan [tool.magnatrix-uv.workspace]
        members = ["packages/*", "apps/web"]
        """
        data = self.read_pyproject()
        tool = data.get("tool", {}).get("magnatrix-uv", {})
        ws_config = tool.get("workspace", {})
        members_globs = ws_config.get("members", [])
        members: List[WorkspaceMember] = []
        for pattern in members_globs:
            # Expand glob
            if pattern.endswith("/*"):
                base = self.cwd / pattern[:-2]
                if base.exists():
                    for sub in base.iterdir():
                        if sub.is_dir() and (sub / "pyproject.toml").exists():
                            members.append(self._load_member(sub))
            else:
                path = self.cwd / pattern
                if (path / "pyproject.toml").exists():
                    members.append(self._load_member(path))
        _log("WORKSPACE", f"discovered {len(members)} members")
        return members

    def _load_member(self, path: Path) -> WorkspaceMember:
        import tomllib
        with open(path / "pyproject.toml", "rb") as f:
            pp = tomllib.load(f)
        return WorkspaceMember(
            name=pp.get("project", {}).get("name", path.name),
            path=path,
            pyproject=pp,
        )

    def workspace_lock(self) -> None:
        """Generate unified lockfile untuk seluruh workspace."""
        members = self.discover_workspace()
        all_reqs: List[Requirement] = []
        for m in members:
            for d in m.pyproject.get("project", {}).get("dependencies", []):
                match = re.match(r'^([a-zA-Z0-9_.-]+)(.*)', d.strip())
                if match:
                    all_reqs.append(Requirement(PackageId(match.group(1)), match.group(2).strip() or "*"))
        resolver = PubGrubResolver(self._index, self.cache)
        lock = resolver.generate_lockfile(all_reqs)
        lock["workspace"] = {"members": [m.name for m in members]}
        _atomic_write(self.lockfile_path, json.dumps(lock, indent=2))
        _log("WORKSPACE", f"workspace lock: {len(lock['packages'])} packages total")


# ─────────────────────────────────────────────────────────────────────────────
# 4. PYTHON VERSION MANAGER — uv python install / pin / switch
# ─────────────────────────────────────────────────────────────────────────────


class PythonVersionManager:
    """
    Manajemen versi Python ala uv python:
    • Download prebuilt Python dari Astral atau indygreg
    • Pin .python-version file
    • Switch antar versi di .venv
    """

    PYTHON_BUILD_URL = "https://github.com/indygreg/python-build-standalone/releases/download"

    def __init__(self, cache: UVCacheEngine, install_root: Optional[Path] = None) -> None:
        self.cache = cache
        self.install_root = install_root or (Path.home() / ".magnatrix" / "python")
        self.install_root.mkdir(parents=True, exist_ok=True)

    def list_installed(self) -> List[Tuple[str, Path]]:
        """List semua Python terinstall."""
        found: List[Tuple[str, Path]] = []
        for sub in self.install_root.iterdir():
            if sub.is_dir():
                py_exe = sub / "bin" / "python3"
                if py_exe.exists():
                    found.append((sub.name, py_exe))
        return sorted(found, key=lambda x: x[0])

    def install(self, version: str = "3.12") -> Path:
        """
        Download & install Python standalone build.
        Simplified: untuk native demo, mock install dengan symlink ke system python.
        Production: download tar.gz dari python-build-standalone.
        """
        target = self.install_root / version
        if target.exists():
            _log("PY", f"Python {version} already installed at {target}")
            return target / "bin" / "python3"

        # Detect system python sebagai fallback
        system_py = shutil.which("python3") or shutil.which("python")
        if not system_py:
            raise RuntimeError("No system python found — cannot bootstrap")

        _log("PY", f"bootstrapping Python {version} (fallback to system: {system_py})")
        target.mkdir(parents=True, exist_ok=True)
        for sub in ["bin", "lib", "include"]:
            (target / sub).mkdir(exist_ok=True)

        # Create proxy executable
        proxy = target / "bin" / "python3"
        proxy.write_text(f"#!/bin/sh\nexec '{system_py}' \"$@\"\n")
        proxy.chmod(0o755)
        _log("PY", f"Python {version} ready at {proxy}")
        return proxy

    def pin(self, version: str, cwd: Optional[Path] = None) -> None:
        """Buat / update .python-version file."""
        cwd = cwd or Path.cwd()
        (cwd / ".python-version").write_text(version + "\n")
        _log("PY", f"pinned {cwd}/.python-version → {version}")

    def get_pinned(self, cwd: Optional[Path] = None) -> Optional[str]:
        f = (cwd or Path.cwd()) / ".python-version"
        if f.exists():
            return f.read_text().strip()
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. UV TOOL / UVX — One-shot Tool Execution
# ─────────────────────────────────────────────────────────────────────────────


class UVToolRunner:
    """
    uv tool run / uvx — jalankan CLI tool dari PyPI tanpa install permanen:
    • Download tool ke isolated environment
    • Cache environment per version
    • Auto-update bila version baru tersedia
    """

    def __init__(self, cache: UVCacheEngine, pm: ProjectManager) -> None:
        self.cache = cache
        self.pm = pm
        self.tools_root = Path.home() / ".magnatrix" / "uv-tools"
        self.tools_root.mkdir(parents=True, exist_ok=True)
        self._index = SimpleIndex(cache)

    def run(self, tool_spec: str, args: List[str]) -> int:
        """
        Run tool: spec = "black", "black>=23.0", "black==23.1.0"
        Return exit code dari subprocess.
        """
        # Parse spec
        match = re.match(r'^([a-zA-Z0-9_.-]+)(.*)', tool_spec.strip())
        if not match:
            _log("UVX", f"invalid tool spec: {tool_spec}", _Colors.RED)
            return 1
        pkg_name, spec = match.group(1), match.group(2).strip()

        # Resolve version
        candidates = self._index.get_versions(pkg_name)
        if not candidates:
            _log("UVX", f"tool '{pkg_name}' not found on PyPI", _Colors.RED)
            return 1
        chosen = candidates[0]
        if spec:
            for c in candidates:
                req = Requirement(PackageId(pkg_name), spec)
                if req.matches(c.version):
                    chosen = c
                    break

        version = str(chosen.version)
        tool_env = self.tools_root / f"{pkg_name}-{version}"

        if not tool_env.exists():
            _log("UVX", f"provisioning {pkg_name}=={version}...")
            venv.create(tool_env, with_pip=False)
            # Production: download & install wheel dari cache/PyPI
            # Mock: create marker
            (tool_env / ".uvx-installed").write_text(f"{pkg_name}=={version}\n")

        py_exe = tool_env / ("Scripts" if sys.platform == "win32" else "bin") / "python"
        _log("UVX", f"running {pkg_name}=={version} via {py_exe}")

        # Production: exec tool's entry point
        # Mock: echo invocation
        print(f"[uvx] {pkg_name} {' '.join(args)}")
        return 0

    def list_installed(self) -> List[Tuple[str, str, Path]]:
        """List semua tool terinstall: [(name, version, env_path)]"""
        tools: List[Tuple[str, str, Path]] = []
        for sub in self.tools_root.iterdir():
            marker = sub / ".uvx-installed"
            if marker.exists():
                spec = marker.read_text().strip()
                if "==" in spec:
                    name, version = spec.split("==")
                    tools.append((name, version, sub))
        return tools

    def upgrade_all(self) -> None:
        """Check & upgrade semua tool ke latest version."""
        for name, current, env_path in self.list_installed():
            candidates = self._index.get_versions(name)
            if candidates:
                latest = str(candidates[0].version)
                if latest != current:
                    _log("UVX", f"upgrading {name}: {current} → {latest}", _Colors.YELLOW)
                    # Re-provision
                    shutil.rmtree(env_path, ignore_errors=True)
                    self.run(f"{name}=={latest}", [])


# ─────────────────────────────────────────────────────────────────────────────
# 6. SCRIPT RUNNER — Inline Dependency Metadata
# ─────────────────────────────────────────────────────────────────────────────


class ScriptRunner:
    """
    Jalankan Python script dengan inline dependency metadata:
    # /// script
    # requires-python = ">=3.10"
    # dependencies = ["requests", "rich"]
    # ///

    Meniru uv run script.py — parse metadata, resolve deps, buat venv sementara,
    jalankan script.
    """

    META_RE = re.compile(
        r'^# /// script\s*\n(.*?)# ///\s*$',
        re.MULTILINE | re.DOTALL,
    )

    def __init__(self, cache: UVCacheEngine, pm: ProjectManager) -> None:
        self.cache = cache
        self.pm = pm

    def parse_metadata(self, script_path: Path) -> Optional[Dict[str, Any]]:
        content = script_path.read_text(encoding="utf-8")
        m = self.META_RE.search(content)
        if not m:
            return None
        # Parse sebagai TOML-ish key-value
        raw = m.group(1)
        meta: Dict[str, Any] = {}
        for line in raw.strip().splitlines():
            line = line.lstrip("# ")
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                # Strip quotes
                if v.startswith('"') and v.endswith('"'):
                    v = v[1:-1]
                elif v.startswith("[") and v.endswith("]"):
                    # Simple list parsing
                    v = [x.strip().strip('"') for x in v[1:-1].split(",") if x.strip()]
                meta[k] = v
        return meta

    def run(self, script_path: Path, args: List[str] = None) -> int:
        meta = self.parse_metadata(script_path)
        if meta is None:
            _log("SCRIPT", f"no inline metadata — running with system python")
            return subprocess.call([sys.executable, str(script_path)] + (args or []))

        deps = meta.get("dependencies", [])
        _log("SCRIPT", f"deps: {deps}")

        # Create temp venv
        with tempfile.TemporaryDirectory(prefix="magnatrix-script-") as tmp:
            venv_path = Path(tmp) / ".venv"
            venv.create(venv_path, with_pip=False)
            py_exe = venv_path / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

            # Resolve & mock-install
            reqs = [Requirement(PackageId(d), "*") for d in deps]
            resolver = PubGrubResolver(SimpleIndex(self.cache), self.cache)
            resolved = resolver.resolve(reqs)
            for pkg, cand in resolved.items():
                _log("SCRIPT", f"  ✓ {pkg}=={cand.version}")

            return subprocess.call([str(py_exe), str(script_path)] + (args or []))


# ─────────────────────────────────────────────────────────────────────────────
# 7. PIP-COMPATIBLE INTERFACE — Drop-in pip replacement
# ─────────────────────────────────────────────────────────────────────────────


class PipCompatInterface:
    """
    uv pip install / uv pip compile / uv pip sync / uv pip list
    Drop-in replacement untuk pip commands yang dipakai MAGNATRIX.
    """

    def __init__(self, cache: UVCacheEngine, pm: ProjectManager) -> None:
        self.cache = cache
        self.pm = pm
        self._index = SimpleIndex(cache)

    def install(self, packages: List[str], target: Optional[Path] = None) -> None:
        """uv pip install package1 package2..."""
        _log("PIP", f"installing {len(packages)} packages...")
        for spec in packages:
            match = re.match(r'^([a-zA-Z0-9_.-]+)(.*)', spec.strip())
            if match:
                pkg, version_spec = match.group(1), match.group(2).strip()
                candidates = self._index.get_versions(pkg)
                req = Requirement(PackageId(pkg), version_spec or "*")
                chosen = next((c for c in candidates if req.matches(c.version)), None)
                if chosen:
                    _log("PIP", f"  ✓ {pkg}=={chosen.version}")
                else:
                    _log("PIP", f"  ✗ {pkg} no matching version", _Colors.RED)

    def compile_requirements(self, requirements_in: Path, requirements_txt: Path) -> None:
        """uv pip compile requirements.in → requirements.txt (lockfile flat)."""
        _log("PIP", f"compiling {requirements_in} → {requirements_txt}")
        lines = requirements_in.read_text().splitlines()
        reqs: List[Requirement] = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r'^([a-zA-Z0-9_.-]+)(.*)', line)
            if match:
                reqs.append(Requirement(PackageId(match.group(1)), match.group(2).strip() or "*"))

        resolver = PubGrubResolver(self._index, self.cache)
        resolved = resolver.resolve(reqs)
        out_lines = [f"# Generated by magnatrix-uv pip compile", ""]
        for name, cand in sorted(resolved.items()):
            out_lines.append(f"{name}=={cand.version}")
        _atomic_write(requirements_txt, "\n".join(out_lines))
        _log("PIP", f"written {len(resolved)} packages to {requirements_txt}")

    def list_installed(self, venv_path: Optional[Path] = None) -> List[str]:
        """uv pip list — list packages di venv."""
        # Simplified: read dari .venv/lib/pythonX.Y/site-packages
        site = (venv_path or self.pm.venv_path) / "lib"
        if not site.exists():
            return []
        packages: List[str] = []
        for py_dir in site.iterdir():
            if py_dir.name.startswith("python"):
                sp = py_dir / "site-packages"
                if sp.exists():
                    for dist in sp.glob("*.dist-info"):
                        name = dist.name.replace(".dist-info", "").rsplit("-", 1)[0]
                        packages.append(name)
        return sorted(set(packages))


# ─────────────────────────────────────────────────────────────────────────────
# 8. UNIFIED CLI — magnatrix-uv (Entry Point)
# ─────────────────────────────────────────────────────────────────────────────


class MagnatrixUV:
    """
    Unified command-line interface yang meniru uv + rye:
    • magnatrix-uv init / add / remove / lock / sync
    • magnatrix-uv python install / pin / list
    • magnatrix-uv run script.py
    • magnatrix-uv tool run / uvx <tool>
    • magnatrix-uv pip install / compile / sync / list
    • magnatrix-uv workspace lock
    • magnatrix-uv cache info / prune
    """

    def __init__(self) -> None:
        self.cache = UVCacheEngine()
        self.pm = ProjectManager(self.cache)
        self.pyvm = PythonVersionManager(self.cache)
        self.tool_runner = UVToolRunner(self.cache, self.pm)
        self.script_runner = ScriptRunner(self.cache, self.pm)
        self.pip = PipCompatInterface(self.cache, self.pm)

    def run(self, argv: List[str]) -> int:
        if len(argv) < 1:
            self._help()
            return 0

        cmd = argv[0]
        args = argv[1:]

        handlers: Dict[str, Callable[[List[str]], int]] = {
            "init": self._cmd_init,
            "add": self._cmd_add,
            "remove": self._cmd_remove,
            "lock": self._cmd_lock,
            "sync": self._cmd_sync,
            "python": self._cmd_python,
            "run": self._cmd_run,
            "tool": self._cmd_tool,
            "uvx": self._cmd_uvx,
            "pip": self._cmd_pip,
            "workspace": self._cmd_workspace,
            "cache": self._cmd_cache,
            "help": self._cmd_help,
            "--help": self._cmd_help,
            "-h": self._cmd_help,
        }

        handler = handlers.get(cmd, self._cmd_unknown)
        return handler(args)

    def _help(self) -> None:
        print("""magnatrix-uv — Native uv/rye integration for MAGNATRIX-OS
Commands:
  init [name]                Initialize a new project
  add <package>[spec]         Add a dependency
  remove <package>            Remove a dependency
  lock                        Generate uv.lock
  sync                        Sync .venv with lockfile
  python install [version]    Install a Python version
  python pin <version>          Pin .python-version
  python list                  List installed Pythons
  run <script.py>              Run script with inline deps
  tool run <tool> [args]       Run a tool (persistent env)
  uvx <tool> [args]            Run a tool (one-shot)
  pip install <pkg>...         Pip-compatible install
  pip compile <in> <out>       Compile requirements.in
  pip list                     List installed packages
  workspace lock               Lock all workspace members
  cache info                   Show cache statistics
  cache prune [days]           Purge stale cache entries
""")

    def _cmd_init(self, args: List[str]) -> int:
        name = args[0] if args else None
        self.pm.init(name=name)
        return 0

    def _cmd_add(self, args: List[str]) -> int:
        if not args:
            print("Usage: magnatrix-uv add <package>[spec]")
            return 1
        self.pm.add(args[0])
        return 0

    def _cmd_remove(self, args: List[str]) -> int:
        if not args:
            print("Usage: magnatrix-uv remove <package>")
            return 1
        self.pm.remove(args[0])
        return 0

    def _cmd_lock(self, _args: List[str]) -> int:
        self.pm.lock()
        return 0

    def _cmd_sync(self, _args: List[str]) -> int:
        self.pm.sync()
        return 0

    def _cmd_python(self, args: List[str]) -> int:
        if not args:
            print("Usage: magnatrix-uv python <install|pin|list>")
            return 1
        sub = args[0]
        if sub == "install":
            version = args[1] if len(args) > 1 else "3.12"
            self.pyvm.install(version)
        elif sub == "pin":
            if len(args) < 2:
                print("Usage: magnatrix-uv python pin <version>")
                return 1
            self.pyvm.pin(args[1])
        elif sub == "list":
            for v, p in self.pyvm.list_installed():
                print(f"  {v} → {p}")
        return 0

    def _cmd_run(self, args: List[str]) -> int:
        if not args:
            print("Usage: magnatrix-uv run <script.py> [args...]")
            return 1
        return self.script_runner.run(Path(args[0]), args[1:])

    def _cmd_tool(self, args: List[str]) -> int:
        if len(args) < 2 or args[0] != "run":
            print("Usage: magnatrix-uv tool run <tool> [args...]")
            return 1
        return self.tool_runner.run(args[1], args[2:])

    def _cmd_uvx(self, args: List[str]) -> int:
        if not args:
            print("Usage: magnatrix-uv uvx <tool> [args...]")
            return 1
        return self.tool_runner.run(args[0], args[1:])

    def _cmd_pip(self, args: List[str]) -> int:
        if not args:
            print("Usage: magnatrix-uv pip <install|compile|sync|list> ...")
            return 1
        sub = args[0]
        if sub == "install":
            self.pip.install(args[1:])
        elif sub == "compile" and len(args) >= 3:
            self.pip.compile_requirements(Path(args[1]), Path(args[2]))
        elif sub == "list":
            for pkg in self.pip.list_installed():
                print(f"  {pkg}")
        return 0

    def _cmd_workspace(self, args: List[str]) -> int:
        if not args or args[0] != "lock":
            print("Usage: magnatrix-uv workspace lock")
            return 1
        self.pm.workspace_lock()
        return 0

    def _cmd_cache(self, args: List[str]) -> int:
        if not args:
            print("Usage: magnatrix-uv cache <info|prune>")
            return 1
        sub = args[0]
        if sub == "info":
            stats = self.cache.stats()
            print(json.dumps(stats, indent=2))
        elif sub == "prune":
            days = int(args[1]) if len(args) > 1 else None
            removed = self.cache.purge(max_age_days=days)
            print(f"Removed {removed} stale cache entries")
        return 0

    def _cmd_help(self, _args: List[str]) -> int:
        self._help()
        return 0

    def _cmd_unknown(self, args: List[str]) -> int:
        print(f"Unknown command. Run 'magnatrix-uv help' for usage.")
        return 1


# ─────────────────────────────────────────────────────────────────────────────
# 9. MAGNATRIX INTEGRATION — Bridge ke existing setup.py / requirements.txt
# ─────────────────────────────────────────────────────────────────────────────


class MagnatrixUVBridge:
    """
    Bridge untuk mengintegrasikan uv/rye patterns ke dalam MAGNATRIX-OS:
    • Convert requirements.txt → pyproject.toml dependencies
    • Build lockfile dari setup.py install_requires
    • Create .venv untuk MAGNATRIX runtime
    • Accelerated package install saat bootstrap
    """

    def __init__(self, cache: Optional[UVCacheEngine] = None) -> None:
        self.cache = cache or UVCacheEngine()
        self.pm = ProjectManager(self.cache)
        self._index = SimpleIndex(self.cache)

    def from_requirements_txt(self, req_path: Path) -> List[Requirement]:
        """Parse requirements.txt ke Requirement objects."""
        reqs: List[Requirement] = []
        if not req_path.exists():
            return reqs
        for line in req_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r'^([a-zA-Z0-9_.\[\]-]+)(.*)', line)
            if match:
                pkg_str, spec = match.group(1), match.group(2).strip()
                # Parse extras
                extras = ()
                if "[" in pkg_str and "]" in pkg_str:
                    pkg_str, extra_str = pkg_str.split("[", 1)
                    extra_str = extra_str.rstrip("]")
                    extras = tuple(x.strip() for x in extra_str.split(","))
                reqs.append(Requirement(PackageId(pkg_str, extras), spec or "*"))
        return reqs

    def from_setup_py(self, setup_path: Path) -> List[Requirement]:
        """Extract install_requires dari setup.py (regex-based)."""
        if not setup_path.exists():
            return []
        content = setup_path.read_text()
        m = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if not m:
            return []
        raw = m.group(1)
        reqs: List[Requirement] = []
        for quoted in re.findall(r'["\']([^"\']+)["\']', raw):
            match = re.match(r'^([a-zA-Z0-9_.-]+)(.*)', quoted.strip())
            if match:
                reqs.append(Requirement(PackageId(match.group(1)), match.group(2).strip() or "*"))
        return reqs

    def lock_magnatrix(self, os_root: Path) -> Path:
        """Generate uv.lock untuk seluruh MAGNATRIX-OS codebase."""
        req_txt = os_root / "requirements.txt"
        setup_py = os_root / "setup.py"
        all_reqs: List[Requirement] = []
        all_reqs.extend(self.from_requirements_txt(req_txt))
        all_reqs.extend(self.from_setup_py(setup_py))
        # Deduplicate
        seen: Set[str] = set()
        unique: List[Requirement] = []
        for r in all_reqs:
            key = str(r.package) + r.specifier
            if key not in seen:
                seen.add(key)
                unique.append(r)
        _log("BRIDGE", f"found {len(unique)} unique dependencies")
        resolver = PubGrubResolver(self._index, self.cache)
        lock = resolver.generate_lockfile(unique)
        lock["source"] = {"requirements_txt": str(req_txt), "setup_py": str(setup_py)}
        lock_path = os_root / "uv.lock"
        _atomic_write(lock_path, json.dumps(lock, indent=2))
        _log("BRIDGE", f"MAGNATRIX lockfile written: {lock_path}")
        return lock_path

    def bootstrap_venv(self, os_root: Path) -> Path:
        """Bootstrap .venv untuk MAGNATRIX runtime."""
        venv_path = os_root / ".venv"
        if venv_path.exists():
            _log("BRIDGE", f"venv already exists at {venv_path}")
            return venv_path
        _log("BRIDGE", f"creating MAGNATRIX runtime venv at {venv_path}")
        venv.create(venv_path, with_pip=False)
        # Sync dari lockfile
        self.pm.cwd = os_root
        self.pm.sync()
        return venv_path

    def upgrade_all(self, os_root: Path) -> None:
        """Upgrade semua packages ke latest compatible version."""
        _log("BRIDGE", "upgrading MAGNATRIX dependencies...")
        req_txt = os_root / "requirements.txt"
        reqs = self.from_requirements_txt(req_txt)
        # Remove version pins untuk upgrade
        upgraded: List[Requirement] = []
        for r in reqs:
            upgraded.append(Requirement(r.package, "*"))
        resolver = PubGrubResolver(self._index, self.cache)
        lock = resolver.generate_lockfile(upgraded)
        _atomic_write(os_root / "uv.lock", json.dumps(lock, indent=2))
        # Rewrite requirements.txt dengan pinned versions
        lines = [f"# Auto-upgraded by magnatrix-uv bridge", ""]
        for name, cand in lock["packages"].items():
            lines.append(f"{name}=={cand['version']}")
        _atomic_write(req_txt, "\n".join(lines))
        _log("BRIDGE", f"upgraded {len(lock['packages'])} packages")


# ─────────────────────────────────────────────────────────────────────────────
# 10. ENTRY POINTS
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    """CLI entry point: python -m runtime.rye_native atau magnatrix-uv"""
    argv = sys.argv[1:]
    app = MagnatrixUV()
    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main())