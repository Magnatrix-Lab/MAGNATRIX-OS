#!/usr/bin/env python3
"""
Pattern Extractor — Clone, Read, Parse, Summarise
Layer 13.5 — Self Improvement

Takes a repo result, clones (or fetches tree), extracts:
  - README patterns (architecture, features, tech stack)
  - AST patterns from Python source (classes, functions, decorators, imports)
  - File-structure patterns (naming conventions, module layout)
  - Dependency patterns (requirements, imports, package.json hints)

Outputs a structured pattern-summary JSON.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Set
from pathlib import Path

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class PatternSummary:
    repo_full_name: str
    repo_url: str
    extraction_time: str
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)
    architecture_notes: List[str] = field(default_factory=list)
    file_structure: Dict[str, Any] = field(default_factory=dict)
    code_metrics: Dict[str, Any] = field(default_factory=dict)
    raw_readme_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

# ---------------------------------------------------------------------------
# README Pattern Extractor
# ---------------------------------------------------------------------------
class ReadmeExtractor:
    """Extract structured patterns from a repository's README."""

    # Regex patterns for common README sections
    SECTION_RE = re.compile(r"^#{1,3}\s+(.*)$", re.MULTILINE)
    CODE_BLOCK_RE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    LIST_ITEM_RE = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)
    NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.+)$", re.MULTILINE)
    URL_RE = re.compile(r"https?://[^\s\)\"\'>]+")
    BADGE_RE = re.compile(r"!\[([^\]]*)\]\(([^\)]+)\)")

    ARCHITECTURE_KEYWORDS = [
        "architecture", "design", "pattern", "layer", "module", "component",
        "service", "microservice", "middleware", "pipeline", "orchestrator",
        "gateway", "router", "proxy", "cache", "queue", "event", "bus",
        "state machine", "actor", "entity", "aggregate", "repository",
        "domain", "application", "infrastructure", "presentation",
    ]

    TECH_KEYWORDS = [
        "python", "typescript", "javascript", "rust", "go", "golang",
        "react", "vue", "angular", "svelte", "next.js", "nuxt",
        "fastapi", "flask", "django", "express", "spring", "rails",
        "docker", "kubernetes", "k8s", "terraform", "aws", "gcp", "azure",
        "postgresql", "mysql", "mongodb", "redis", "sqlite", "elasticsearch",
        "kafka", "rabbitmq", "grpc", "rest", "graphql", "websocket",
        "tensorflow", "pytorch", "jax", "huggingface", "scikit-learn",
        "solidity", "ethereum", "web3", "ipfs", "blockchain",
    ]

    def __init__(self, readme_text: str):
        self.text = readme_text
        self.lines = readme_text.splitlines()

    def _find_sections(self) -> Dict[str, str]:
        """Split README into heading-section chunks."""
        sections: Dict[str, str] = {}
        current_heading = "__intro__"
        current_body: List[str] = []

        for line in self.lines:
            m = self.SECTION_RE.match(line)
            if m:
                sections[current_heading] = "\n".join(current_body).strip()
                current_heading = m.group(1).strip().lower()
                current_body = []
            else:
                current_body.append(line)
        sections[current_heading] = "\n".join(current_body).strip()
        return sections

    def extract_architecture_notes(self) -> List[str]:
        """Pull sentences mentioning architecture or design patterns."""
        notes: List[str] = []
        sections = self._find_sections()
        for heading, body in sections.items():
            if any(kw in heading for kw in self.ARCHITECTURE_KEYWORDS):
                # Take first 5 non-empty lines as summary
                for line in body.splitlines()[:8]:
                    line = line.strip()
                    if line and len(line) > 10:
                        notes.append(line)
            # Also scan body for pattern sentences
            sentences = re.split(r"(?<=[.!?])\s+", body)
            for sent in sentences:
                if any(kw in sent.lower() for kw in self.ARCHITECTURE_KEYWORDS):
                    if len(sent) > 20 and len(sent) < 300:
                        notes.append(sent.strip())
        # Deduplicate while preserving order
        seen: Set[str] = set()
        deduped: List[str] = []
        for n in notes:
            key = re.sub(r"\s+", " ", n.lower())[:80]
            if key not in seen:
                seen.add(key)
                deduped.append(n)
        return deduped[:15]

    def extract_tech_stack(self) -> List[str]:
        """Infer tech stack from README badges, code blocks, and mentions."""
        stack: Set[str] = set()
        # Badges often contain tech names
        for _, url in self.BADGE_RE.findall(self.text):
            for tech in self.TECH_KEYWORDS:
                if tech in url.lower():
                    stack.add(tech)
        # Code-block languages
        for lang, _ in self.CODE_BLOCK_RE.findall(self.text):
            if lang:
                stack.add(lang.lower())
        # Direct mentions in text
        lower_text = self.text.lower()
        for tech in self.TECH_KEYWORDS:
            if tech in lower_text:
                stack.add(tech)
        # Special normalisation
        if "golang" in stack:
            stack.discard("golang")
            stack.add("go")
        return sorted(stack)

    def extract_raw_summary(self, max_chars: int = 2000) -> str:
        """Collapsible summary of README for downstream generators."""
        sections = self._find_sections()
        parts: List[str] = []
        for heading, body in sections.items():
            if heading == "__intro__":
                parts.append(body[:500])
                continue
            if any(kw in heading for kw in ["install", "usage", "example", "quick", "getting"]):
                parts.append(f"### {heading}\n{body[:400]}")
            if any(kw in heading for kw in self.ARCHITECTURE_KEYWORDS):
                parts.append(f"### {heading}\n{body[:600]}")
        text = "\n\n".join(parts)
        return text[:max_chars]

# ---------------------------------------------------------------------------
# AST Pattern Extractor (Python)
# ---------------------------------------------------------------------------
class AstPatternExtractor:
    """Walk Python AST to extract structural code patterns."""

    def __init__(self, source: str, filename: str = "<unknown>"):
        self.source = source
        self.filename = filename
        try:
            self.tree = ast.parse(source, filename=filename)
        except SyntaxError:
            self.tree = None

    def extract(self) -> Dict[str, Any]:
        if self.tree is None:
            return {"error": "syntax_error", "filename": self.filename}

        patterns: Dict[str, Any] = {
            "filename": self.filename,
            "total_lines": len(self.source.splitlines()),
            "classes": [],
            "functions": [],
            "decorators": [],
            "imports": [],
            "dataclasses": [],
            "async_defs": [],
            "generators": [],
            "context_managers": [],
            "type_hints": False,
            "abstract_classes": [],
            "property_getters": [],
            "custom_exceptions": [],
            "main_guard": False,
        }

        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                cls_info = {
                    "name": node.name,
                    "bases": [self._name(b) for b in node.bases],
                    "methods": [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
                    "decorators": [self._name(d) for d in node.decorator_list],
                    "line": node.lineno,
                }
                patterns["classes"].append(cls_info)
                if any("dataclass" in str(d) for d in node.decorator_list):
                    patterns["dataclasses"].append(node.name)
                if any("ABC" in str(b) or "abstract" in str(b).lower() for b in node.bases):
                    patterns["abstract_classes"].append(node.name)
                # Check properties
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if any("property" in str(d) for d in item.decorator_list):
                            patterns["property_getters"].append(f"{node.name}.{item.name}")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_info = {
                    "name": node.name,
                    "args_count": len(node.args.args),
                    "has_defaults": any(node.args.defaults),
                    "has_varargs": node.args.vararg is not None,
                    "has_kwargs": node.args.kwarg is not None,
                    "decorators": [self._name(d) for d in node.decorator_list],
                    "returns_annotated": node.returns is not None,
                    "line": node.lineno,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                }
                patterns["functions"].append(fn_info)
                if isinstance(node, ast.AsyncFunctionDef):
                    patterns["async_defs"].append(node.name)
                for d in node.decorator_list:
                    dn = self._name(d)
                    if dn and dn not in patterns["decorators"]:
                        patterns["decorators"].append(dn)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    patterns["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    patterns["imports"].append(f"{mod}.{alias.name}" if mod else alias.name)

            elif isinstance(node, ast.Yield):
                patterns["generators"] = True
            elif isinstance(node, ast.YieldFrom):
                patterns["generators"] = True
            elif isinstance(node, ast.With):
                patterns["context_managers"] = True
            elif isinstance(node, ast.AnnAssign):
                patterns["type_hints"] = True
            elif isinstance(node, ast.Try):
                for handler in node.handlers:
                    if isinstance(handler.type, ast.Name) and handler.type.id == "Exception":
                        pass  # generic
            elif isinstance(node, ast.Raise):
                if isinstance(node.exc, ast.Call):
                    call_name = self._name(node.exc.func)
                    if call_name and "Error" in call_name:
                        if call_name not in patterns["custom_exceptions"]:
                            patterns["custom_exceptions"].append(call_name)

            elif isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    if any(isinstance(op, ast.Eq) for op in node.test.ops):
                        if self._is_name(node.test.left, "__name__"):
                            patterns["main_guard"] = True

        # Normalise booleans to list length for generators/context_managers
        patterns["generators"] = ["yield_used"] if patterns["generators"] else []
        patterns["context_managers"] = ["with_used"] if patterns["context_managers"] else []
        patterns["type_hints"] = ["annotated"] if patterns["type_hints"] else []
        return patterns

    def _name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._name(node.value)}.{node.attr}"
        if isinstance(node, ast.Call):
            return self._name(node.func)
        if isinstance(node, ast.Constant):
            return str(node.value)
        return ""

    def _is_name(self, node: ast.AST, name: str) -> bool:
        return isinstance(node, ast.Name) and node.id == name

# ---------------------------------------------------------------------------
# File-Structure Analyser
# ---------------------------------------------------------------------------
class FileStructureAnalyser:
    """Analyse directory layout and naming conventions."""

    def analyse(self, root_dir: str) -> Dict[str, Any]:
        root = Path(root_dir)
        if not root.exists():
            return {"error": "directory_not_found", "path": root_dir}

        structure: Dict[str, Any] = {
            "root": root_dir,
            "total_files": 0,
            "total_dirs": 0,
            "python_files": [],
            "test_files": [],
            "config_files": [],
            "doc_files": [],
            "entry_points": [],
            "naming_conventions": {},
            "depth_histogram": {},
        }

        for path in root.rglob("*"):
            rel = path.relative_to(root)
            depth = len(rel.parts)
            structure["depth_histogram"][depth] = structure["depth_histogram"].get(depth, 0) + 1

            if path.is_file():
                structure["total_files"] += 1
                name = path.name
                if name.endswith(".py"):
                    structure["python_files"].append(str(rel))
                    if name.startswith("test_") or "_test.py" in name or "/tests/" in str(rel).lower():
                        structure["test_files"].append(str(rel))
                    if name == "__main__.py" or "main" in name.lower():
                        structure["entry_points"].append(str(rel))
                elif name in ("requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile"):
                    structure["config_files"].append(str(rel))
                elif name in ("README.md", "README.rst", "CONTRIBUTING.md", "LICENSE", "CHANGELOG.md"):
                    structure["doc_files"].append(str(rel))
            else:
                structure["total_dirs"] += 1

        # Detect naming convention
        snake = sum(1 for f in structure["python_files"] if "_" in Path(f).stem and "-" not in Path(f).stem)
        kebab = sum(1 for f in structure["python_files"] if "-" in Path(f).stem)
        total_py = len(structure["python_files"]) or 1
        structure["naming_conventions"] = {
            "snake_case_ratio": round(snake / total_py, 2),
            "kebab_case_ratio": round(kebab / total_py, 2),
            "dominant": "snake_case" if snake >= kebab else "kebab_case" if kebab else "mixed",
        }
        return structure

# ---------------------------------------------------------------------------
# Pattern Extractor Orchestrator
# ---------------------------------------------------------------------------
class PatternExtractor:
    """High-level extractor: clone/fetch → analyse → summarise."""

    def __init__(self, clone_dir: Optional[str] = None, use_git: bool = True):
        self.clone_dir = clone_dir or os.path.join(tempfile.gettempdir(), "repo_hunter_clones")
        os.makedirs(self.clone_dir, exist_ok=True)
        self.use_git = use_git

    def _clone_repo(self, repo_url: str, repo_name: str) -> str:
        """Clone a repo to temp dir; return local path."""
        target = os.path.join(self.clone_dir, repo_name.replace("/", "__"))
        if os.path.exists(target):
            shutil.rmtree(target)
        cmd = ["git", "clone", "--depth", "1", "--single-branch", repo_url, target]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback: directory may not exist; return empty path
            return ""
        return target

    def extract(self, repo_full_name: str, repo_url: str,
                local_path: Optional[str] = None,
                max_py_files: int = 20) -> PatternSummary:
        """Run full extraction pipeline on a repository."""
        from datetime import datetime, timezone

        if local_path is None:
            local_path = self._clone_repo(repo_url, repo_full_name)

        summary = PatternSummary(
            repo_full_name=repo_full_name,
            repo_url=repo_url,
            extraction_time=datetime.now(timezone.utc).isoformat(),
        )

        # --- README analysis ---
        readme_path = None
        for candidate in ["README.md", "README.rst", "README.txt", "README"]:
            p = os.path.join(local_path, candidate)
            if os.path.exists(p):
                readme_path = p
                break
        if readme_path:
            with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
                readme_text = f.read()
            rext = ReadmeExtractor(readme_text)
            summary.architecture_notes = rext.extract_architecture_notes()
            summary.tech_stack = rext.extract_tech_stack()
            summary.raw_readme_summary = rext.extract_raw_summary()

        # --- File structure ---
        if local_path and os.path.isdir(local_path):
            fsa = FileStructureAnalyser()
            summary.file_structure = fsa.analyse(local_path)

        # --- AST pattern extraction (Python only) ---
        py_files = summary.file_structure.get("python_files", [])[:max_py_files]
        all_patterns: List[Dict[str, Any]] = []
        total_lines = 0
        class_count = 0
        func_count = 0
        for rel_path in py_files:
            full = os.path.join(local_path, rel_path)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    src = f.read()
            except Exception:
                continue
            extractor = AstPatternExtractor(src, filename=rel_path)
            pat = extractor.extract()
            if "error" not in pat:
                all_patterns.append(pat)
                total_lines += pat.get("total_lines", 0)
                class_count += len(pat.get("classes", []))
                func_count += len(pat.get("functions", []))

        summary.code_metrics = {
            "python_files_scanned": len(py_files),
            "total_lines": total_lines,
            "total_classes": class_count,
            "total_functions": func_count,
            "avg_lines_per_file": round(total_lines / max(len(py_files), 1), 1),
        }
        summary.patterns = self._deduplicate_patterns(all_patterns)
        return summary

    def _deduplicate_patterns(self, raw_patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collapse repeated patterns across files into summary records."""
        # Aggregate decorator usage
        decorator_counts: Dict[str, int] = {}
        import_counts: Dict[str, int] = {}
        class_names: Set[str] = set()
        async_count = 0
        dataclass_count = 0
        property_count = 0
        custom_ex_count = 0

        for p in raw_patterns:
            for d in p.get("decorators", []):
                decorator_counts[d] = decorator_counts.get(d, 0) + 1
            for imp in p.get("imports", []):
                top = imp.split(".")[0]
                import_counts[top] = import_counts.get(top, 0) + 1
            for c in p.get("classes", []):
                class_names.add(c["name"])
            async_count += len(p.get("async_defs", []))
            dataclass_count += len(p.get("dataclasses", []))
            property_count += len(p.get("property_getters", []))
            custom_ex_count += len(p.get("custom_exceptions", []))

        patterns: List[Dict[str, Any]] = []
        if decorator_counts:
            patterns.append({
                "type": "decorator_usage",
                "data": dict(sorted(decorator_counts.items(), key=lambda x: -x[1])[:10]),
            })
        if import_counts:
            patterns.append({
                "type": "top_imports",
                "data": dict(sorted(import_counts.items(), key=lambda x: -x[1])[:15]),
            })
        if class_names:
            patterns.append({
                "type": "class_inventory",
                "data": sorted(class_names)[:20],
            })
        if async_count:
            patterns.append({
                "type": "async_pattern",
                "count": async_count,
                "note": "async/await usage detected across files",
            })
        if dataclass_count:
            patterns.append({
                "type": "dataclass_pattern",
                "count": dataclass_count,
                "note": "@dataclass usage detected",
            })
        if property_count:
            patterns.append({
                "type": "property_pattern",
                "count": property_count,
                "note": "@property getter/setter pattern detected",
            })
        if custom_ex_count:
            patterns.append({
                "type": "custom_exception_pattern",
                "count": custom_ex_count,
                "note": "custom exception classes detected",
            })

        # Structural patterns
        has_main_guard = any(p.get("main_guard") for p in raw_patterns)
        if has_main_guard:
            patterns.append({"type": "main_guard", "note": "if __name__ == '__main__' pattern used"})

        has_generators = any(p.get("generators") for p in raw_patterns)
        if has_generators:
            patterns.append({"type": "generator_pattern", "note": "yield / yield from detected"})

        has_ctx = any(p.get("context_managers") for p in raw_patterns)
        if has_ctx:
            patterns.append({"type": "context_manager_pattern", "note": "with-statement usage detected"})

        has_types = any(p.get("type_hints") for p in raw_patterns)
        if has_types:
            patterns.append({"type": "type_hint_pattern", "note": "PEP 484 type annotations detected"})

        return patterns

    def save(self, summary: PatternSummary, out_dir: str) -> str:
        """Save pattern summary JSON to a file. Returns path."""
        os.makedirs(out_dir, exist_ok=True)
        safe_name = summary.repo_full_name.replace("/", "__")
        path = os.path.join(out_dir, f"{safe_name}_patterns.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(summary.to_json())
        return path

# ---------------------------------------------------------------------------
# Self-Test
# ---------------------------------------------------------------------------
def _demo() -> None:
    import sys
    # Demo: analyse a known small Python repo from local filesystem if provided
    repo = sys.argv[1] if len(sys.argv) > 1 else None
    if repo and os.path.isdir(repo):
        extractor = PatternExtractor()
        summary = extractor.extract(
            repo_full_name="local/demo",
            repo_url="file://" + os.path.abspath(repo),
            local_path=repo,
            max_py_files=10,
        )
        print(summary.to_json())
    else:
        print("Usage: python pattern_extractor_native.py <local_repo_path>")
        print("  or run as part of the self-improvement loop.")

if __name__ == "__main__":
    _demo()
