#!/usr/bin/env python3
"""docs/adr_generator_native.py — Architecture Decision Record Generator"""
from __future__ import annotations
import os, re, json
from datetime import datetime
from typing import Dict, List, Optional

class ADRGenerator:
    def __init__(self, dir: str = "docs/adr"):
        self.dir = dir
        os.makedirs(dir, exist_ok=True)
        self.registry: List[str] = []
        self._load_registry()

    def _load_registry(self):
        for f in os.listdir(self.dir):
            if f.endswith(".md"):
                self.registry.append(f)
        self.registry.sort()

    def create(self, title: str, context: str, decision: str, consequences: str, status: str = "proposed") -> str:
        num = len(self.registry) + 1
        date = datetime.now().strftime("%Y-%m-%d")
        filename = f"{num:04d}-{re.sub(r'[^\w-]', '_', title.lower())}.md"
        content = f"""# ADR-{num:04d}: {title}

**Status:** {status} | **Date:** {date}

## Context

{context}

## Decision

{decision}

## Consequences

{consequences}
"""
        path = os.path.join(self.dir, filename)
        with open(path, "w") as f:
            f.write(content)
        self.registry.append(filename)
        return path

    def search(self, query: str) -> List[str]:
        results = []
        for f in self.registry:
            path = os.path.join(self.dir, f)
            with open(path) as fh:
                text = fh.read()
            if query.lower() in text.lower():
                results.append(f)
        return results

    def link(self, src_num: int, dst_num: int) -> None:
        src = f"{src_num:04d}-"
        dst = f"{dst_num:04d}-"
        for f in self.registry:
            if f.startswith(src):
                path = os.path.join(self.dir, f)
                with open(path) as fh:
                    content = fh.read()
                with open(path, "w") as fh:
                    fh.write(content + f"
**Related:** ADR-{dst_num:04d}
")

    def export_index(self, path: str) -> None:
        with open(path, "w") as f:
            f.write("# Architecture Decision Records

")
            for f in self.registry:
                f_path = os.path.join(self.dir, f)
                with open(f_path) as fh:
                    first = fh.readline().strip()
                f.write(f"- [{first}](adr/{f})
")

if __name__ == "__main__":
    adr = ADRGenerator("/tmp/adr")
    adr.create("Use Python", "Need scripting", "Python 3.11", "Easy to read")
    adr.create("Use SQLite", "Need persistence", "SQLite backend", "Zero config")
    print(f"ADRs: {len(adr.registry)}")
    print(f"Search 'Python': {adr.search('Python')}")
