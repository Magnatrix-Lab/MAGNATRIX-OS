#!/usr/bin/env python3
"""
Release Manager for MAGNATRIX-OS
Version bumping, changelog generation, git tagging, and
release artifact packaging. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclasses.dataclass
class Version:
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None

    def __str__(self) -> str:
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            v += f"-{self.prerelease}"
        return v

    @classmethod
    def parse(cls, text: str) -> Version:
        m = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-(.+))?", text.strip().lstrip("v"))
        if not m:
            raise ValueError(f"Invalid version: {text}")
        return cls(int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4))

    def bump_major(self) -> Version:
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> Version:
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> Version:
        return Version(self.major, self.minor, self.patch + 1)


class ReleaseManager:
    """Manages versioning, changelogs, and release artifacts."""

    def __init__(self, repo_root: str, version_file: str = "version.json") -> None:
        self.root = Path(repo_root)
        self.version_file = self.root / version_file
        self._current = self._load_version()

    def _load_version(self) -> Version:
        if self.version_file.exists():
            try:
                data = json.loads(self.version_file.read_text())
                return Version.parse(data.get("version", "0.0.0"))
            except Exception:
                pass
        return Version(0, 0, 0)

    def _save_version(self) -> None:
        self.version_file.write_text(json.dumps({"version": str(self._current), "updated": time.time()}, indent=2))

    def get_version(self) -> Version:
        return self._current

    def bump(self, level: str = "patch") -> Version:
        if level == "major":
            self._current = self._current.bump_major()
        elif level == "minor":
            self._current = self._current.bump_minor()
        else:
            self._current = self._current.bump_patch()
        self._save_version()
        return self._current

    def generate_changelog(self, since_tag: Optional[str] = None) -> str:
        """Generate changelog from git commits."""
        try:
            cmd = ["git", "log", "--oneline", "--no-decorate"]
            if since_tag:
                cmd.extend([f"{since_tag}..HEAD"])
            else:
                cmd.extend(["-30"])
            result = subprocess.run(cmd, cwd=str(self.root), capture_output=True, text=True)
            lines = result.stdout.strip().split("\n")
            changelog = f"## Changelog for v{self._current}\n\n"
            for line in lines:
                if line.strip():
                    changelog += f"- {line.strip()}\n"
            return changelog
        except Exception as e:
            return f"# Changelog\n\nError generating changelog: {e}"

    def write_changelog(self, path: str = "CHANGELOG.md") -> str:
        changelog = self.generate_changelog()
        changelog_path = self.root / path
        existing = ""
        if changelog_path.exists():
            existing = changelog_path.read_text()
        changelog_path.write_text(changelog + "\n" + existing)
        return str(changelog_path)

    def create_tag(self, message: Optional[str] = None) -> str:
        tag = f"v{self._current}"
        try:
            subprocess.run(["git", "tag", "-a", tag, "-m", message or f"Release {tag}"], cwd=str(self.root), check=True)
        except subprocess.CalledProcessError:
            pass
        return tag

    def package(self, output_dir: str = "dist") -> str:
        """Create a release tarball."""
        out = self.root / output_dir
        out.mkdir(exist_ok=True)
        tag = f"v{self._current}"
        tar_name = f"magnatrix-os-{tag}.tar.gz"
        try:
            subprocess.run(
                ["git", "archive", "--format=tar.gz", f"--output={out / tar_name}", "HEAD"],
                cwd=str(self.root), check=True
            )
        except subprocess.CalledProcessError:
            pass
        return str(out / tar_name)

    def stats(self) -> Dict[str, Any]:
        return {
            "version": str(self._current),
            "version_file": str(self.version_file),
            "repo_root": str(self.root),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="magnatrix_rel_"))
    # Init git repo
    subprocess.run(["git", "init"], cwd=str(tmp), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp), capture_output=True)
    (tmp / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=str(tmp), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=str(tmp), capture_output=True)
    rm = ReleaseManager(str(tmp))
    print("=== Release Manager Demo ===\n")
    print(f"Initial version: {rm.get_version()}")
    rm.bump("minor")
    print(f"After minor bump: {rm.get_version()}")
    rm.bump("patch")
    print(f"After patch bump: {rm.get_version()}")
    changelog = rm.generate_changelog()
    print(f"\nChangelog preview:\n{changelog[:200]}")
    tag = rm.create_tag("Release test")
    print(f"Tag: {tag}")
    print(f"Stats: {rm.stats()}")
    # Cleanup
    import shutil
    shutil.rmtree(tmp)


if __name__ == "__main__":
    _demo()
