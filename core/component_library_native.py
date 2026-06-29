"""
component_library_native.py
MAGNATRIX-OS — Component Library

Inspired by langflow-ai/langflow component system:
Reusable AI components for prompts, LLMs, tools, memory, vector stores. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Component:
    component_id: str
    name: str
    category: str
    description: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    template_code: str = ""
    tags: List[str] = field(default_factory=list)


class ComponentLibrary:
    """Reusable AI component library for building flows."""

    COMPONENT_LIBRARY = {
        "prompt_template": Component(
            component_id="prompt_template", name="Prompt Template",
            category="prompt", description="Template for generating prompts with variable substitution",
            inputs=["template", "variables"], outputs=["prompt"],
            config_schema={"template": "str", "variables": "dict"},
            template_code="prompt = template.format(**variables)", tags=["prompt", "template"],
        ),
        "llm_call": Component(
            component_id="llm_call", name="LLM Call",
            category="llm", description="Call an LLM with a prompt and return the response",
            inputs=["prompt", "model", "temperature"], outputs=["response", "tokens"],
            config_schema={"model": "str", "temperature": "float", "max_tokens": "int"},
            template_code="response = llm.generate(prompt, model=model, temperature=temperature)", tags=["llm", "generation"],
        ),
        "memory_store": Component(
            component_id="memory_store", name="Memory Store",
            category="memory", description="Store and retrieve conversation history",
            inputs=["message", "session_id"], outputs=["history", "context"],
            config_schema={"max_history": "int", "session_id": "str"},
            template_code="history = memory.get(session_id); memory.add(session_id, message)", tags=["memory", "conversation"],
        ),
        "vector_search": Component(
            component_id="vector_search", name="Vector Search",
            category="vector_store", description="Search vector store for similar documents",
            inputs=["query", "top_k"], outputs=["results", "scores"],
            config_schema={"index_name": "str", "top_k": "int", "embedding_model": "str"},
            template_code="results = vector_store.search(query, top_k=top_k)", tags=["rag", "vector", "search"],
        ),
        "tool_executor": Component(
            component_id="tool_executor", name="Tool Executor",
            category="tool", description="Execute a tool with given parameters",
            inputs=["tool_name", "parameters"], outputs=["result", "error"],
            config_schema={"tool_name": "str", "timeout": "int"},
            template_code="result = tools.execute(tool_name, **parameters)", tags=["tool", "execution"],
        ),
        "agent_router": Component(
            component_id="agent_router", name="Agent Router",
            category="agent", description="Route queries to appropriate agents or tools",
            inputs=["query", "agents"], outputs=["selected_agent", "confidence"],
            config_schema={"agents": "list", "fallback": "str"},
            template_code="agent = router.select(query, agents)", tags=["agent", "routing"],
        ),
        "condition_branch": Component(
            component_id="condition_branch", name="Condition Branch",
            category="logic", description="Branch flow based on a condition evaluation",
            inputs=["condition", "true_value", "false_value"], outputs=["result"],
            config_schema={"operator": "str", "threshold": "float"},
            template_code="result = true_value if condition else false_value", tags=["logic", "control"],
        ),
        "output_parser": Component(
            component_id="output_parser", name="Output Parser",
            category="output", description="Parse structured output from LLM responses",
            inputs=["raw_output", "format"], outputs=["parsed", "validation_error"],
            config_schema={"format": "str", "schema": "dict"},
            template_code="parsed = parser.parse(raw_output, format=format)", tags=["output", "parsing"],
        ),
        "document_loader": Component(
            component_id="document_loader", name="Document Loader",
            category="data", description="Load and preprocess documents for RAG",
            inputs=["source", "format"], outputs=["chunks", "metadata"],
            config_schema={"chunk_size": "int", "chunk_overlap": "int", "format": "str"},
            template_code="chunks = loader.load(source, chunk_size=chunk_size)", tags=["data", "rag", "loading"],
        ),
        "web_search": Component(
            component_id="web_search", name="Web Search",
            category="tool", description="Search the web for information",
            inputs=["query", "num_results"], outputs=["results", "sources"],
            config_schema={"num_results": "int", "engine": "str"},
            template_code="results = search.web(query, num_results=num_results)", tags=["tool", "search", "web"],
        ),
    }

    def __init__(self, lib_dir: str = "./components"):
        self.lib_dir = Path(lib_dir)
        self.lib_dir.mkdir(exist_ok=True)
        self.custom_components: Dict[str, Component] = {}
        self._load()

    def _load(self) -> None:
        file = self.lib_dir / "custom.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid, cd in data.items():
                        self.custom_components[cid] = Component(**cd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.lib_dir / "custom.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.custom_components.items()}, f, indent=2)

    def get_component(self, component_id: str) -> Optional[Component]:
        return self.COMPONENT_LIBRARY.get(component_id) or self.custom_components.get(component_id)

    def list_components(self, category: Optional[str] = None) -> List[str]:
        all_comp = {**self.COMPONENT_LIBRARY, **self.custom_components}
        if category:
            return [c.component_id for c in all_comp.values() if c.category == category]
        return list(all_comp.keys())

    def create_component(self, component_id: str, name: str, category: str, description: str,
                         inputs: List[str], outputs: List[str], config_schema: Dict[str, Any],
                         template_code: str, tags: List[str]) -> Component:
        comp = Component(
            component_id=component_id, name=name, category=category, description=description,
            inputs=inputs, outputs=outputs, config_schema=config_schema,
            template_code=template_code, tags=tags,
        )
        self.custom_components[component_id] = comp
        self._save()
        return comp

    def get_stats(self) -> Dict[str, Any]:
        categories = {}
        for c in {**self.COMPONENT_LIBRARY, **self.custom_components}.values():
            categories[c.category] = categories.get(c.category, 0) + 1
        return {"total_components": len(self.COMPONENT_LIBRARY) + len(self.custom_components), "categories": categories}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ComponentLibrary", "Component"]