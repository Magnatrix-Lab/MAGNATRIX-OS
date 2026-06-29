"""
flow_component_node_native.py
MAGNATRIX-OS — Flow Component Node

Inspired by Langflow (langflow-ai): Reusable component nodes with typed inputs/outputs.
Define component specs with validation, defaults, and render hints. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ComponentSpec:
    spec_id: str
    name: str
    description: str
    category: str
    inputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)


class FlowComponentNode:
    """Reusable component nodes with typed inputs/outputs and validation."""

    BUILT_IN_COMPONENTS = {
        "chat_input": {
            "name": "Chat Input", "description": "User message input",
            "category": "inputs",
            "inputs": {},
            "outputs": {"message": {"type": "string", "description": "User message"}},
            "parameters": {"placeholder": {"type": "string", "default": "Enter message..."}},
        },
        "chat_output": {
            "name": "Chat Output", "description": "Display assistant response",
            "category": "outputs",
            "inputs": {"message": {"type": "string", "required": True}},
            "outputs": {},
            "parameters": {},
        },
        "llm": {
            "name": "LLM", "description": "Large Language Model node",
            "category": "models",
            "inputs": {"prompt": {"type": "string", "required": True}},
            "outputs": {"response": {"type": "string", "description": "LLM response"}},
            "parameters": {"model": {"type": "string", "default": "gpt-4"}, "temperature": {"type": "float", "default": 0.7}},
        },
        "memory": {
            "name": "Memory", "description": "Conversation memory buffer",
            "category": "memory",
            "inputs": {"input": {"type": "string", "required": True}, "history": {"type": "list", "required": False}},
            "outputs": {"context": {"type": "string", "description": "Formatted conversation context"}},
            "parameters": {"window_size": {"type": "integer", "default": 10}},
        },
        "agent": {
            "name": "Agent", "description": "Autonomous agent executor",
            "category": "agents",
            "inputs": {"task": {"type": "string", "required": True}},
            "outputs": {"result": {"type": "string", "description": "Agent execution result"}},
            "parameters": {"max_iterations": {"type": "integer", "default": 5}},
        },
        "tool": {
            "name": "Tool", "description": "External tool invocation",
            "category": "tools",
            "inputs": {"args": {"type": "dict", "required": True}},
            "outputs": {"result": {"type": "any", "description": "Tool result"}},
            "parameters": {"tool_name": {"type": "string", "required": True}},
        },
        "condition": {
            "name": "Condition", "description": "Branching condition",
            "category": "logic",
            "inputs": {"value": {"type": "any", "required": True}},
            "outputs": {"true": {"type": "any"}, "false": {"type": "any"}},
            "parameters": {"operator": {"type": "string", "default": "equals"}, "compare_to": {"type": "any", "default": ""}},
        },
        "text_splitter": {
            "name": "Text Splitter", "description": "Split text into chunks",
            "category": "processing",
            "inputs": {"text": {"type": "string", "required": True}},
            "outputs": {"chunks": {"type": "list", "description": "Text chunks"}},
            "parameters": {"chunk_size": {"type": "integer", "default": 1000}, "overlap": {"type": "integer", "default": 200}},
        },
    }

    def __init__(self, components_dir: str = "./flow_components"):
        self.components_dir = Path(components_dir)
        self.components_dir.mkdir(exist_ok=True)
        self.components: Dict[str, ComponentSpec] = {}
        self._load()

    def _load(self) -> None:
        file = self.components_dir / "components.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid, cd in data.items():
                        self.components[cid] = ComponentSpec(**cd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.components_dir / "components.json", "w", encoding="utf-8") as f:
            json.dump({cid: asdict(c) for cid, c in self.components.items()}, f, indent=2)

    def register(self, spec_id: str, name: str, description: str, category: str,
                 inputs: Dict[str, Dict[str, Any]], outputs: Dict[str, Dict[str, Any]],
                 parameters: Optional[Dict[str, Any]] = None) -> ComponentSpec:
        spec = ComponentSpec(
            spec_id=spec_id, name=name, description=description, category=category,
            inputs=inputs, outputs=outputs, parameters=parameters or {},
        )
        self.components[spec_id] = spec
        self._save()
        return spec

    def register_builtin(self, spec_id: str) -> Optional[ComponentSpec]:
        if spec_id not in self.BUILT_IN_COMPONENTS:
            return None
        info = self.BUILT_IN_COMPONENTS[spec_id]
        return self.register(
            spec_id=spec_id, name=info["name"], description=info["description"],
            category=info["category"], inputs=info["inputs"], outputs=info["outputs"],
            parameters=info.get("parameters", {}),
        )

    def validate_inputs(self, spec_id: str, provided: Dict[str, Any]) -> List[str]:
        spec = self.components.get(spec_id)
        if not spec:
            return ["Component not found"]
        errors = []
        for name, meta in spec.inputs.items():
            if meta.get("required", False) and name not in provided:
                errors.append(f"Missing required input: {name}")
        return errors

    def get_component(self, spec_id: str) -> Optional[ComponentSpec]:
        return self.components.get(spec_id)

    def list_by_category(self, category: str) -> List[ComponentSpec]:
        return [c for c in self.components.values() if c.category == category]

    def get_stats(self) -> Dict[str, Any]:
        categories = {}
        for c in self.components.values():
            categories[c.category] = categories.get(c.category, 0) + 1
        return {"total": len(self.components), "categories": categories, "builtins": len(self.BUILT_IN_COMPONENTS)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["FlowComponentNode", "ComponentSpec"]