#!/usr/bin/env python3
"""
Native Generator — Pattern Summary → Native Python Implementation
Layer 13.5 — Self Improvement

Reads a PatternSummary JSON, synthesises a native Python module that
re-implements the discovered patterns using only stdlib.  Auto-names
and auto-places the output into the correct MAGNATRIX layer directory.
"""

import json
import os
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# ---------------------------------------------------------------------------
# Layer Map (MAGNATRIX OS layer → directory)
# ---------------------------------------------------------------------------
LAYER_MAP = {
    "layer1": "/mnt/agents/MAGNATRIX-OS/core",
    "layer2": "/mnt/agents/MAGNATRIX-OS/security",
    "layer3": "/mnt/agents/MAGNATRIX-OS/storage",
    "layer4": "/mnt/agents/MAGNATRIX-OS/network",
    "layer5": "/mnt/agents/MAGNATRIX-OS/knowledge",
    "layer6": "/mnt/agents/MAGNATRIX-OS/ai",
    "layer7": "/mnt/agents/MAGNATRIX-OS/devops",
    "layer8": "/mnt/agents/MAGNATRIX-OS/edge",
    "layer9": "/mnt/agents/MAGNATRIX-OS/quantum",
    "layer10": "/mnt/agents/MAGNATRIX-OS/interface",
    "layer11": "/mnt/agents/MAGNATRIX-OS/governance",
    "layer12": "/mnt/agents/MAGNATRIX-OS/market",
    "layer13": "/mnt/agents/MAGNATRIX-OS/growth",
    "layer13.5": "/mnt/agents/MAGNATRIX-OS/auto_repo_hunter",
}

# ---------------------------------------------------------------------------
# Heuristic: map repo topic → layer
# ---------------------------------------------------------------------------
LAYER_HEURISTICS: List[Tuple[set, str, str]] = [
    ({"security", "crypto", "cipher", "encrypt", "hash", "auth", "audit", "defi"}, "layer2", "security"),
    ({"database", "storage", "kv", "sqlite", "persist", "index", "cache"}, "layer3", "storage"),
    ({"network", "socket", "websocket", "grpc", "http", "tcp", "udp", "proxy"}, "layer4", "network"),
    ({"knowledge", "graph", "ontology", "semantic", "embed", "vector", "rag"}, "layer5", "knowledge"),
    ({"ai", "ml", "model", "transformer", "neural", "inference", "llm", "agent"}, "layer6", "ai"),
    ({"devops", "docker", "k8s", "deploy", "ci", "cd", "orchestrat", "schedule"}, "layer7", "devops"),
    ({"edge", "iot", "embedded", "sensor", "gateway", "firmware", "mqtt"}, "layer8", "edge"),
    ({"quantum", "qubit", "quantum_computing", "quantum_algorith"}, "layer9", "quantum"),
    ({"ui", "interface", "frontend", "react", "vue", "html", "css", "component"}, "layer10", "interface"),
    ({"governance", "constitution", "ethic", "policy", "compliance", "rule"}, "layer11", "governance"),
    ({"market", "trading", "exchange", "arbitrage", "portfolio", "finance", "stock"}, "layer12", "market"),
    ({"growth", "seo", "marketing", "campaign", "analytics", "funnel"}, "layer13", "growth"),
    ({"self", "improve", "auto", "hunt", "repo", "pattern", "extract"}, "layer13.5", "self_improvement"),
]

# ---------------------------------------------------------------------------
# Code Generator Core
# ---------------------------------------------------------------------------
class NativeGenerator:
    """Generate a native Python module from a PatternSummary."""

    HEADER_TEMPLATE = '''#!/usr/bin/env python3
"""
{title}
Auto-generated from pattern extraction of `{repo_full_name}`
Layer: {layer} | Generated: {timestamp}

Description:
{description}
"""

import json
import os
import re
import sys
import math
import hashlib
import random
import string
import itertools
import collections
import datetime
import time
import typing
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Callable, Tuple, Set

'''

    def __init__(self, summary_path: str):
        with open(summary_path, "r", encoding="utf-8") as f:
            self.summary = json.load(f)
        self.repo = self.summary.get("repo_full_name", "unknown/repo")
        self.tech_stack = self.summary.get("tech_stack", [])
        self.patterns = self.summary.get("patterns", [])
        self.arch_notes = self.summary.get("architecture_notes", [])
        self.file_struct = self.summary.get("file_structure", {})
        self.metrics = self.summary.get("code_metrics", {})
        self.readme_summary = self.summary.get("raw_readme_summary", "")
        self.generated_parts: List[str] = []

    def _snake_name(self, text: str) -> str:
        """Convert repo name to snake_case Python module name."""
        text = text.replace("/", "_").replace("-", "_").replace(".", "_")
        text = re.sub(r"[^a-zA-Z0-9_]", "", text)
        text = re.sub(r"_+", "_", text).strip("_").lower()
        if text and text[0].isdigit():
            text = "n_" + text
        return text[:60] or "generated_module"

    def _classify_layer(self) -> Tuple[str, str]:
        """Return (layer_key, layer_dir) based on tech stack + arch notes."""
        corpus = " ".join(self.tech_stack + self.arch_notes + [self.readme_summary]).lower()
        scores: Dict[str, int] = {}
        for keywords, layer_key, _ in LAYER_HEURISTICS:
            score = sum(1 for kw in keywords if kw in corpus)
            if score:
                scores[layer_key] = scores.get(layer_key, 0) + score
        if scores:
            best = max(scores, key=scores.get)
            return best, LAYER_MAP.get(best, "/mnt/agents/MAGNATRIX-OS/core")
        return "layer13.5", LAYER_MAP["layer13.5"]

    def _generate_dataclass(self, name: str, fields: List[Tuple[str, str, Any]]) -> str:
        """Generate a @dataclass definition."""
        lines = [f"@dataclass", f"class {name}:", f'    """Auto-generated data model."""']
        for field_name, type_hint, default in fields:
            if default is None:
                lines.append(f"    {field_name}: {type_hint}")
            elif isinstance(default, (list, dict)):
                lines.append(f"    {field_name}: {type_hint} = field(default_factory={type(default).__name__})")
            else:
                lines.append(f"    {field_name}: {type_hint} = {repr(default)}")
        lines.append("")
        return "\n".join(lines)

    def _generate_class(self, name: str, bases: List[str], methods: List[Dict[str, Any]]) -> str:
        """Generate a class with methods inferred from pattern summary."""
        base_str = f"({', '.join(bases)})" if bases else ""
        lines = [f"class {name}{base_str}:", f'    """Auto-generated class from pattern extraction."""']
        for m in methods:
            mname = m.get("name", "method")
            is_async = m.get("is_async", False)
            args_count = m.get("args_count", 1)
            prefix = "async " if is_async else ""
            args = ["self"] + [f"arg{i}: Any" for i in range(1, args_count)]
            sig = ", ".join(args)
            ret = m.get("returns_annotated", False)
            ret_hint = " -> Any" if ret else ""
            lines.append(f"    def {prefix}{mname}({sig}){ret_hint}:")
            lines.append(f'        """Auto-generated method stub."""')
            lines.append(f"        pass")
            lines.append("")
        if not methods:
            lines.append("    pass")
        lines.append("")
        return "\n".join(lines)

    def _generate_function(self, name: str, args: List[str], is_async: bool = False,
                           doc: str = "", body: List[str] = None) -> str:
        """Generate a top-level function."""
        prefix = "async " if is_async else ""
        sig = ", ".join(args) if args else ""
        lines = [f"{prefix}def {name}({sig}):", f'    """{doc or "Auto-generated function."}"""']
        if body:
            for line in body:
                lines.append(f"    {line}")
        else:
            lines.append("    pass")
        lines.append("")
        return "\n".join(lines)

    def _generate_decorator_stub(self, name: str) -> str:
        return f'''def {name}(func: Callable) -> Callable:
    """Auto-generated decorator stub."""
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)
    return wrapper

'''

    def _generate_main_guard(self) -> str:
        return '''if __name__ == "__main__":
    # Auto-generated entry point — adapt as needed
    print("Module loaded. Define your own _demo() or CLI here.")
'''

    # -----------------------------------------------------------------------
    # Pattern-driven synthesis
    # -----------------------------------------------------------------------
    def _synthesise_from_patterns(self) -> None:
        """Walk discovered patterns and emit matching code stubs."""
        for pat in self.patterns:
            ptype = pat.get("type", "")

            if ptype == "decorator_usage":
                for dec_name in pat.get("data", {}).keys():
                    stub_name = re.sub(r"[^a-zA-Z0-9_]", "", dec_name).lower() or "my_decorator"
                    self.generated_parts.append(self._generate_decorator_stub(stub_name))

            elif ptype == "class_inventory":
                for cls_name in pat.get("data", []):
                    safe_cls = re.sub(r"[^a-zA-Z0-9_]", "", cls_name)
                    if not safe_cls[0].isupper():
                        safe_cls = safe_cls.capitalize()
                    self.generated_parts.append(
                        self._generate_class(safe_cls, bases=[], methods=[])
                    )

            elif ptype == "async_pattern":
                self.generated_parts.append(
                    self._generate_function("async_task", ["coro: Any"], is_async=True,
                                           doc="Async task runner stub.")
                )

            elif ptype == "dataclass_pattern":
                self.generated_parts.append(
                    self._generate_dataclass("DataModel", [
                        ("id", "str", None),
                        ("name", "str", ""),
                        ("metadata", "Dict[str, Any]", None),
                        ("tags", "List[str]", []),
                    ])
                )

            elif ptype == "property_pattern":
                self.generated_parts.append(
                    self._generate_class("PropertyMixin", bases=[],
                        methods=[{"name": "value", "is_async": False, "args_count": 1,
                                 "returns_annotated": True}]
                    )
                )

            elif ptype == "custom_exception_pattern":
                self.generated_parts.append(
                    self._generate_class("DomainError", bases=["Exception"],
                        methods=[{"name": "__init__", "is_async": False, "args_count": 2,
                                 "returns_annotated": False}]
                    )
                )

            elif ptype == "main_guard":
                # main guard is appended at end; skip here
                pass

            elif ptype == "generator_pattern":
                self.generated_parts.append(
                    self._generate_function("lazy_sequence", ["items: List[Any]"], is_async=False,
                                           doc="Generator yielding items lazily.",
                                           body=["for item in items:", "    yield item"])
                )

            elif ptype == "context_manager_pattern":
                self.generated_parts.append(
                    self._generate_class("ResourceContext", bases=[],
                        methods=[
                            {"name": "__enter__", "is_async": False, "args_count": 1, "returns_annotated": True},
                            {"name": "__exit__", "is_async": False, "args_count": 4, "returns_annotated": False},
                        ]
                    )
                )

            elif ptype == "type_hint_pattern":
                # Already covered by imports — no extra code needed
                pass

            elif ptype == "top_imports":
                # Imports are handled in header — no extra code
                pass

    def _synthesise_from_architecture(self) -> None:
        """Generate structural code from README architecture notes."""
        # Heuristic: if notes mention "registry", "orchestrator", "scheduler", emit matching stubs
        corpus = " ".join(self.arch_notes).lower()
        keywords_to_classes = {
            "registry": ("ServiceRegistry", ["register", "deregister", "discover"]),
            "orchestrator": ("Orchestrator", ["submit", "schedule", "cancel"]),
            "scheduler": ("TaskScheduler", ["enqueue", "dequeue", "peek"]),
            "pipeline": ("Pipeline", ["add_stage", "run", "reset"]),
            "cache": ("CacheLayer", ["get", "set", "invalidate"]),
            "queue": ("MessageQueue", ["push", "pop", "length"]),
            "router": ("RequestRouter", ["add_route", "resolve", "dispatch"]),
            "gateway": ("APIGateway", ["authenticate", "forward", "rate_limit"]),
            "proxy": ("ProxyHandler", ["intercept", "forward", "log"]),
            "middleware": ("MiddlewareStack", ["add", "remove", "process"]),
            "event": ("EventBus", ["subscribe", "publish", "unsubscribe"]),
            "bus": ("EventBus", ["subscribe", "publish", "unsubscribe"]),
            "state machine": ("StateMachine", ["transition", "current_state", "is_valid"]),
            "repository": ("Repository", ["find", "save", "delete", "list_all"]),
            "aggregate": ("AggregateRoot", ["apply", "commit", "version"]),
            "domain": ("DomainModel", ["validate", "to_dict", "from_dict"]),
        }
        emitted: set = set()
        for kw, (cls_name, methods) in keywords_to_classes.items():
            if kw in corpus and cls_name not in emitted:
                emitted.add(cls_name)
                method_stubs = [
                    {"name": m, "is_async": False, "args_count": 2, "returns_annotated": True}
                    for m in methods
                ]
                self.generated_parts.append(
                    self._generate_class(cls_name, bases=[], methods=method_stubs)
                )

    def generate(self, output_dir: Optional[str] = None,
                 module_name_override: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate the full module. Returns (file_path, module_name).
        """
        layer_key, layer_dir = self._classify_layer()
        timestamp = datetime.now(timezone.utc).isoformat()
        module_name = module_name_override or self._snake_name(self.repo) + "_native"
        title = module_name.replace("_", " ").title()

        description_lines: List[str] = []
        description_lines.append(f"Tech stack: {', '.join(self.tech_stack[:8]) or 'unknown'}")
        description_lines.append(f"Architecture notes: {len(self.arch_notes)} extracted")
        description_lines.append(f"Code metrics: {json.dumps(self.metrics)}")
        description = "\n".join(description_lines)

        # Build header
        header = self.HEADER_TEMPLATE.format(
            title=title,
            repo_full_name=self.repo,
            layer=layer_key,
            timestamp=timestamp,
            description=description,
        )

        # Synthesise patterns
        self._synthesise_from_patterns()
        self._synthesise_from_architecture()

        # Build body
        body = "\n".join(self.generated_parts)

        # Main guard
        main_guard = self._generate_main_guard()

        # Assemble
        source = header + body + main_guard

        # Determine output path
        if output_dir is None:
            output_dir = layer_dir
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{module_name}.py")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(source)

        # Metadata sidecar
        meta_path = out_path.replace(".py", "_meta.json")
        meta = {
            "repo": self.repo,
            "layer": layer_key,
            "generated_at": timestamp,
            "module_name": module_name,
            "tech_stack": self.tech_stack,
            "patterns_found": len(self.patterns),
            "lines_of_code": len(source.splitlines()),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        return out_path, module_name

# ---------------------------------------------------------------------------
# Batch Generator
# ---------------------------------------------------------------------------
class BatchGenerator:
    """Process multiple pattern-summary JSONs in one run."""

    def __init__(self, summaries_dir: str, output_base: Optional[str] = None):
        self.summaries_dir = summaries_dir
        self.output_base = output_base or "/mnt/agents/MAGNATRIX-OS"
        self.results: List[Dict[str, Any]] = []

    def run(self) -> List[Dict[str, Any]]:
        """Find all *_patterns.json files and generate modules."""
        for fname in sorted(os.listdir(self.summaries_dir)):
            if not fname.endswith("_patterns.json"):
                continue
            path = os.path.join(self.summaries_dir, fname)
            print(f"[BatchGenerator] processing {fname} ...")
            try:
                gen = NativeGenerator(path)
                out_path, mod_name = gen.generate(output_dir=None)
                self.results.append({
                    "input": fname,
                    "output_path": out_path,
                    "module_name": mod_name,
                    "layer": gen._classify_layer()[0],
                })
            except Exception as e:
                self.results.append({
                    "input": fname,
                    "error": str(e),
                })
        return self.results

    def report(self) -> str:
        """Generate a Markdown report of all generated modules."""
        lines = ["# Native Generator Batch Report\n", f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n"]
        for r in self.results:
            if "error" in r:
                lines.append(f"- ❌ `{r['input']}` → ERROR: {r['error']}")
            else:
                lines.append(f"- ✅ `{r['input']}` → `{r['module_name']}` @ `{r['output_path']}` (layer {r['layer']})")
        return "\n".join(lines)

# ---------------------------------------------------------------------------
# Self-Test
# ---------------------------------------------------------------------------
def _demo() -> None:
    import sys
    if len(sys.argv) < 2:
        print("Usage: python native_generator_native.py <pattern_summary.json>")
        print("   or: python native_generator_native.py --batch <summaries_dir/>")
        return

    if sys.argv[1] == "--batch":
        dir_path = sys.argv[2] if len(sys.argv) > 2 else "."
        batch = BatchGenerator(dir_path)
        batch.run()
        print(batch.report())
    else:
        gen = NativeGenerator(sys.argv[1])
        path, name = gen.generate()
        print(f"✅ Generated: {path}")
        print(f"   Module: {name}")
        print(f"   Layer:  {gen._classify_layer()[0]}")

if __name__ == "__main__":
    _demo()
