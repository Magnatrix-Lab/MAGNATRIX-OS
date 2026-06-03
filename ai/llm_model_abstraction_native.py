"""
llm_model_abstraction_native.py
MAGNATRIX-OS Model Abstraction Engine
Native Python, stdlib only.
Provides unified model interface, adapter pattern, capability detection, and cross-model fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class ModelCapability(Enum):
    TEXT_COMPLETION = "text_completion"
    CHAT = "chat"
    VISION = "vision"
    EMBEDDING = "embedding"
    FINE_TUNING = "fine_tuning"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"


class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class ModelAdapter:
    model_id: str
    provider: ModelProvider
    capabilities: List[ModelCapability]
    max_tokens: int
    supports_system_prompt: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    generate_fn: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id, "provider": self.provider.value,
            "capabilities": [c.value for c in self.capabilities],
            "max_tokens": self.max_tokens, "supports_system_prompt": self.supports_system_prompt,
        }

    def can_handle(self, capabilities: List[ModelCapability]) -> bool:
        return all(c in self.capabilities for c in capabilities)

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        if self.generate_fn:
            return self.generate_fn(prompt, **kwargs)
        return f"[Simulated response from {self.model_id}]"


class ModelAbstractionEngine:
    """Unified model interface with capability-based routing."""

    def __init__(self) -> None:
        self._adapters: Dict[str, ModelAdapter] = {}
        self._fallback_chain: List[str] = []

    def register_adapter(self, adapter: ModelAdapter) -> None:
        self._adapters[adapter.model_id] = adapter

    def set_fallback_chain(self, model_ids: List[str]) -> None:
        self._fallback_chain = model_ids

    def select_model(self, required_capabilities: List[ModelCapability], preferred: Optional[str] = None) -> Optional[ModelAdapter]:
        if preferred and preferred in self._adapters:
            adapter = self._adapters[preferred]
            if adapter.can_handle(required_capabilities):
                return adapter

        for model_id in self._fallback_chain:
            adapter = self._adapters.get(model_id)
            if adapter and adapter.can_handle(required_capabilities):
                return adapter

        for adapter in self._adapters.values():
            if adapter.can_handle(required_capabilities):
                return adapter
        return None

    def generate(self, prompt: str, capabilities: Optional[List[ModelCapability]] = None,
                 preferred: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        caps = capabilities or [ModelCapability.TEXT_COMPLETION]
        adapter = self.select_model(caps, preferred)
        if not adapter:
            return {"error": "No model available for required capabilities", "capabilities": [c.value for c in caps]}
        try:
            result = adapter.generate(prompt, **kwargs)
            return {"model": adapter.model_id, "result": result, "success": True}
        except Exception as e:
            # Try fallback
            for fallback_id in self._fallback_chain:
                if fallback_id == adapter.model_id:
                    continue
                fallback = self._adapters.get(fallback_id)
                if fallback and fallback.can_handle(caps):
                    try:
                        result = fallback.generate(prompt, **kwargs)
                        return {"model": fallback.model_id, "result": result, "success": True, "fallback": True}
                    except Exception:
                        continue
            return {"error": str(e), "model": adapter.model_id, "success": False}

    def list_models(self, capability: Optional[ModelCapability] = None) -> List[ModelAdapter]:
        adapters = list(self._adapters.values())
        if capability:
            adapters = [a for a in adapters if capability in a.capabilities]
        return adapters

    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        adapter = self._adapters.get(model_id)
        return adapter.to_dict() if adapter else None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "models": len(self._adapters),
            "capabilities": list(set(c.value for a in self._adapters.values() for c in a.capabilities)),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Model Abstraction Engine")
    print("=" * 60)

    engine = ModelAbstractionEngine()

    def gpt4_generate(prompt: str, **kwargs) -> str:
        return f"GPT-4o: {prompt[:30]}..."

    def claude_generate(prompt: str, **kwargs) -> str:
        return f"Claude: {prompt[:30]}..."

    def local_generate(prompt: str, **kwargs) -> str:
        return f"Local: {prompt[:30]}..."

    engine.register_adapter(ModelAdapter(
        "gpt-4o", ModelProvider.OPENAI,
        [ModelCapability.TEXT_COMPLETION, ModelCapability.CHAT, ModelCapability.VISION, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING],
        128000, generate_fn=gpt4_generate
    ))
    engine.register_adapter(ModelAdapter(
        "claude-3", ModelProvider.ANTHROPIC,
        [ModelCapability.TEXT_COMPLETION, ModelCapability.CHAT, ModelCapability.VISION],
        200000, generate_fn=claude_generate
    ))
    engine.register_adapter(ModelAdapter(
        "local-llm", ModelProvider.LOCAL,
        [ModelCapability.TEXT_COMPLETION, ModelCapability.CHAT],
        4096, generate_fn=local_generate
    ))

    engine.set_fallback_chain(["gpt-4o", "claude-3", "local-llm"])

    print("\n--- Generate with capabilities ---")
    result = engine.generate("Hello world", capabilities=[ModelCapability.CHAT])
    print(f"  {result}")

    print("\n--- Vision request ---")
    result = engine.generate("Describe image", capabilities=[ModelCapability.VISION])
    print(f"  {result}")

    print("\n--- Fallback simulation ---")
    # Request a capability only local has (none, will fallback)
    result = engine.generate("Test", capabilities=[ModelCapability.FUNCTION_CALLING], preferred="local-llm")
    print(f"  {result}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nModel Abstraction test complete.")


if __name__ == "__main__":
    run()
