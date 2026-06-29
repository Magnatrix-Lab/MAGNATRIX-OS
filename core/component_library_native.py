"""
component_library_native.py
MAGNATRIX-OS — Component Library

Inspired by Langflow (langflow-ai): Shared component library for reusable flow nodes.
Library of pre-built components with templates and documentation. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class LibraryComponent:
    component_id: str
    name: str
    description: str
    category: str
    template: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0


class ComponentLibrary:
    """Shared component library for reusable flow nodes."""

    BUILT_IN_COMPONENTS = {
        "openai_chat": {
            "name": "OpenAI Chat", "description": "Chat with OpenAI models",
            "category": "models", "template": "openai_chat",
            "parameters": {"model": "gpt-4", "temperature": 0.7, "max_tokens": 2000},
            "tags": ["llm", "openai"],
        },
        "anthropic_chat": {
            "name": "Anthropic Chat", "description": "Chat with Claude models",
            "category": "models", "template": "anthropic_chat",
            "parameters": {"model": "claude-3", "max_tokens": 4000},
            "tags": ["llm", "anthropic"],
        },
        "local_llm": {
            "name": "Local LLM", "description": "Run local LLM via Ollama",
            "category": "models", "template": "local_llm",
            "parameters": {"model": "llama3", "base_url": "http://localhost:11434"},
            "tags": ["llm", "local"],
        },
        "chroma_db": {
            "name": "ChromaDB", "description": "Chroma vector store",
            "category": "vector_store", "template": "chroma_db",
            "parameters": {"collection": "default", "persist": True},
            "tags": ["vector", "chroma"],
        },
        "web_search": {
            "name": "Web Search", "description": "Search the web",
            "category": "tools", "template": "web_search",
            "parameters": {"engine": "duckduckgo", "max_results": 5},
            "tags": ["search", "web"],
        },
        "code_executor": {
            "name": "Code Executor", "description": "Execute Python code",
            "category": "tools", "template": "code_executor",
            "parameters": {"language": "python", "timeout": 30},
            "tags": ["code", "execution"],
        },
        "file_reader": {
            "name": "File Reader", "description": "Read file contents",
            "category": "io", "template": "file_reader",
            "parameters": {"path": "", "encoding": "utf-8"},
            "tags": ["file", "io"],
        },
        "csv_parser": {
            "name": "CSV Parser", "description": "Parse CSV data",
            "category": "processing", "template": "csv_parser",
            "parameters": {"delimiter": ",", "has_header": True},
            "tags": ["csv", "data"],
        },
    }

    def __init__(self, library_dir: str = "./component_library"):
        self.library_dir = Path(library_dir)
        self.library_dir.mkdir(exist_ok=True)
        self.components: Dict[str, LibraryComponent] = {}
        self._load()

    def _load(self) -> None:
        file = self.library_dir / "components.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid, cd in data.items():
                        self.components[cid] = LibraryComponent(**cd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.library_dir / "components.json", "w", encoding="utf-8") as f:
            json.dump({cid: asdict(c) for cid, c in self.components.items()}, f, indent=2)

    def register(self, component_id: str, name: str, description: str, category: str,
                 template: str, parameters: Dict[str, Any], tags: Optional[List[str]] = None) -> LibraryComponent:
        comp = LibraryComponent(
            component_id=component_id, name=name, description=description,
            category=category, template=template, parameters=parameters, tags=tags or [],
        )
        self.components[component_id] = comp
        self._save()
        return comp

    def register_builtin(self, component_id: str) -> Optional[LibraryComponent]:
        if component_id not in self.BUILT_IN_COMPONENTS:
            return None
        info = self.BUILT_IN_COMPONENTS[component_id]
        return self.register(
            component_id=component_id, name=info["name"], description=info["description"],
            category=info["category"], template=info["template"],
            parameters=info["parameters"], tags=info.get("tags", []),
        )

    def use(self, component_id: str) -> Optional[LibraryComponent]:
        comp = self.components.get(component_id)
        if comp:
            comp.usage_count += 1
            self._save()
        return comp

    def search(self, query: str) -> List[LibraryComponent]:
        q = query.lower()
        return [c for c in self.components.values() if q in c.name.lower() or q in c.description.lower() or any(q in t for t in c.tags)]

    def get_by_category(self, category: str) -> List[LibraryComponent]:
        return [c for c in self.components.values() if c.category == category]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.components)
        categories = {}
        for c in self.components.values():
            categories[c.category] = categories.get(c.category, 0) + 1
        return {"total": total, "categories": categories, "builtins": len(self.BUILT_IN_COMPONENTS)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ComponentLibrary", "LibraryComponent"]