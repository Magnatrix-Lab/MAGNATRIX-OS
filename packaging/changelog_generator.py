#!/usr/bin/env python3
"""
MAGNATRIX-OS Changelog Generator
Parse git commits since last tag, categorize, generate CHANGELOG.md.
Usage:
    python packaging/changelog_generator.py
"""
import os, re, subprocess, json
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"

CATEGORIES = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "docs": "Documentation",
    "perf": "Performance",
    "security": "Security",
    "refactor": "Refactoring",
    "test": "Tests",
    "build": "Build System",
    "ci": "CI/CD",
    "chore": "Chores",
}


def get_last_tag():
    try:
        out = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], cwd=REPO_ROOT, text=True)
        return out.strip()
    except subprocess.CalledProcessError:
        return None


def get_commits_since(tag):
    range_spec = f"{tag}..HEAD" if tag else "HEAD"
    try:
        out = subprocess.check_output(
            ["git", "log", range_spec, "--pretty=format:%H|%s"],
            cwd=REPO_ROOT, text=True, errors="replace"
        )
    except subprocess.CalledProcessError:
        return []

    commits = []
    for line in out.strip().splitlines():
        parts = line.split("|", 1)
        if len(parts) == 2:
            commits.append((parts[0], parts[1]))
    return commits


def parse_commit(subject):
    pattern = r"^(\w+)(?:\(([^)]+)\))?:\s*(.+)"
    m = re.match(pattern, subject)
    if not m:
        return "chore", "", subject, False
    type_, scope, msg = m.groups()
    breaking = "BREAKING" in subject or "BREAKING CHANGE" in subject
    return type_, scope or "", msg.strip(), breaking


def generate_changelog(tag=None):
    commits = get_commits_since(tag)
    if not commits:
        print("[CHANGELOG] No commits since last tag.")
        return

    grouped = {cat: [] for cat in CATEGORIES.values()}
    breaking = []

    for commit_hash, subject in commits:
        type_, scope, msg, is_breaking = parse_commit(subject)
        cat = CATEGORIES.get(type_, "Chores")
        entry = f"- {msg}"
        if scope:
            entry += f" (`{scope}`)"
        entry += f" — [{commit_hash[:7]}]"
        grouped[cat].append(entry)
        if is_breaking:
            breaking.append(f"- **BREAKING**: {msg}")

    version = datetime.now().strftime("%Y.%m.%d")
    lines = [f"## [{version}]\n"]

    if breaking:
        lines.append("### Breaking Changes\n")
        lines.extend(breaking)
        lines.append("")

    for cat_name in CATEGORIES.values():
        entries = grouped.get(cat_name, [])
        if entries:
            lines.append(f"### {cat_name}\n")
            lines.extend(entries)
            lines.append("")

    return "\n".join(lines)


def update_changelog():
    tag = get_last_tag()
    new_section = generate_changelog(tag)
    if not new_section:
        return

    header = "# MAGNATRIX-OS Changelog\n\nAll notable changes.\n\n"
    if CHANGELOG_PATH.exists():
        existing = CHANGELOG_PATH.read_text()
        if "## [" in existing:
            pos = existing.find("## [", len(header))
            content = existing[:pos] + new_section + "\n" + existing[pos:]
        else:
            content = header + new_section + "\n" + existing
    else:
        content = header + new_section + "\n"

    CHANGELOG_PATH.write_text(content)
    print(f"[CHANGELOG] Updated: {CHANGELOG_PATH}")


def main():
    update_changelog()


if __name__ == "__main__":
    main()
