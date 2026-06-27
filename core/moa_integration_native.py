#!/usr/bin/env python3
"""
Mixture of Agents (MoA) Integration for MAGNATRIX-OS
====================================================
Implements MoA pattern inspired by Hermes Agent (Nous Research).
Multiple reference models provide perspective → aggregator synthesizes
and executes with tool schema. Pure stdlib.

Integrates with:
  - SwarmIntelligence (nodes as reference models)
  - MultiModelLLMAdapter (model routing)
  - CacheEngine (prompt prefix caching)
  - ConfigManager (preset configuration)
  - EventBus (broadcasting reference outputs)

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, re, time, threading
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union


@dataclass
class ModelConfig:
    """Configuration for a model."""
    provider: str = "local"
    model: str = "default"
    temperature: float = 0.6
    max_tokens: int = 4096
    timeout: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MOAPreset:
    """MoA preset configuration."""
    preset_id: str
    name: str
    reference_models: List[ModelConfig] = field(default_factory=list)
    aggregator: ModelConfig = field(default_factory=lambda: ModelConfig())
    reference_temperature: float = 0.6
    aggregator_temperature: float = 0.4
    max_tokens: int = 4096
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["reference_models"] = [m.to_dict() for m in self.reference_models]
        d["aggregator"] = self.aggregator.to_dict()
        return d


@dataclass
class ReferenceOutput:
    """Output from a reference model."""
    model_provider: str
    model_name: str
    content: str
    latency_ms: float = 0.0
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MOAContext:
    """Context passed through the MoA pipeline."""
    user_message: str
    system_prompt: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    tool_schema: Optional[Dict[str, Any]] = None
    reference_outputs: List[ReferenceOutput] = field(default_factory=list)
    aggregator_response: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    turn_id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_message": self.user_message,
            "system_prompt": self.system_prompt[:200] + "..." if len(self.system_prompt) > 200 else self.system_prompt,
            "history_len": len(self.conversation_history),
            "reference_count": len(self.reference_outputs),
            "aggregator_response": self.aggregator_response[:200] + "..." if len(self.aggregator_response) > 200 else self.aggregator_response,
            "tool_calls": len(self.tool_calls),
            "turn_id": self.turn_id,
        }


class ModelRouter:
    """Routes calls to model providers. Pure stdlib simulation."""

    def __init__(self) -> None:
        self._providers: Dict[str, Callable] = {}
        self._stats: Dict[str, Dict[str, Any]] = {}

    def register_provider(self, name: str, handler: Callable) -> None:
        self._providers[name] = handler

    def call(self, config: ModelConfig, messages: List[Dict[str, str]], tools: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call a model. Returns dict with content and metadata."""
        provider = config.provider
        if provider in self._providers:
            try:
                t0 = time.time()
                result = self._providers[provider](config, messages, tools)
                latency_ms = (time.time() - t0) * 1000
                if provider not in self._stats:
                    self._stats[provider] = {"calls": 0, "errors": 0, "avg_latency_ms": 0.0}
                self._stats[provider]["calls"] += 1
                self._stats[provider]["avg_latency_ms"] = (self._stats[provider]["avg_latency_ms"] * (self._stats[provider]["calls"] - 1) + latency_ms) / self._stats[provider]["calls"]
                return {"content": result, "latency_ms": latency_ms, "error": None}
            except Exception as e:
                if provider not in self._stats:
                    self._stats[provider] = {"calls": 0, "errors": 0, "avg_latency_ms": 0.0}
                self._stats[provider]["errors"] += 1
                return {"content": "", "latency_ms": 0.0, "error": str(e)}
        # Default simulation
        return {
            "content": f"[{provider}/{config.model}] Analysis of: {messages[-1]['content'][:100]}...",
            "latency_ms": 100.0 + (hash(config.model) % 200),
            "error": None,
        }

    def get_stats(self) -> Dict[str, Any]:
        return self._stats.copy()


class PromptCache:
    """Cache for stable prompt prefixes."""

    def __init__(self, max_size: int = 100) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._cache[key]["last_access"] = time.time()
                self._hits += 1
                return self._cache[key]["value"]
            self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._cache) >= self._max_size:
                oldest = min(self._cache, key=lambda k: self._cache[k]["last_access"])
                del self._cache[oldest]
            self._cache[key] = {"value": value, "last_access": time.time()}

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
                "size": len(self._cache),
                "max_size": self._max_size,
            }

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)


class MOAReferenceEngine:
    """Runs reference models without tool schemas."""

    def __init__(self, router: ModelRouter, cache: PromptCache) -> None:
        self.router = router
        self.cache = cache
        self._outputs: List[ReferenceOutput] = []

    def run(self, preset: MOAPreset, context: MOAContext) -> List[ReferenceOutput]:
        """Run all reference models for a preset."""
        outputs = []
        # Build stable prompt prefix key
        prefix_key = self._build_prefix_key(context)
        cached_prefix = self.cache.get(prefix_key)

        for model_config in preset.reference_models:
            t0 = time.time()
            # Reference models receive only user/assistant text, no system prompt or tools
            messages = self._build_reference_messages(context, cached_prefix)
            result = self.router.call(model_config, messages, tools=None)
            latency_ms = (time.time() - t0) * 1000 if result["latency_ms"] == 0.0 else result["latency_ms"]

            output = ReferenceOutput(
                model_provider=model_config.provider,
                model_name=model_config.model,
                content=result["content"],
                latency_ms=latency_ms,
                error=result.get("error"),
            )
            outputs.append(output)

        # Cache the prefix for next iteration
        if cached_prefix is None:
            self.cache.set(prefix_key, messages)

        self._outputs = outputs
        return outputs

    def _build_prefix_key(self, context: MOAContext) -> str:
        # Hash of system prompt + conversation history (stable prefix)
        stable = context.system_prompt + json.dumps(context.conversation_history[-10:], sort_keys=True)
        return hashlib_hash(stable)

    def _build_reference_messages(self, context: MOAContext, cached_prefix: Optional[Any]) -> List[Dict[str, str]]:
        if cached_prefix:
            return cached_prefix + [{"role": "user", "content": context.user_message}]
        messages = []
        if context.conversation_history:
            messages.extend([{"role": h["role"], "content": h["content"]} for h in context.conversation_history[-10:]])
        messages.append({"role": "user", "content": context.user_message})
        return messages

    def get_outputs(self) -> List[ReferenceOutput]:
        return self._outputs.copy()


def hashlib_hash(data: str) -> str:
    import hashlib
    return hashlib.md5(data.encode()).hexdigest()[:16]


class MOAAggregator:
    """Aggregator model that synthesizes reference outputs and executes tools."""

    def __init__(self, router: ModelRouter, cache: PromptCache) -> None:
        self.router = router
        self.cache = cache

    def run(self, preset: MOAPreset, context: MOAContext) -> MOAContext:
        """Run aggregator with full tool schema and reference outputs."""
        # Build aggregator messages: stable prefix + user message + reference outputs
        messages = self._build_aggregator_messages(context)
        result = self.router.call(preset.aggregator, messages, tools=context.tool_schema)
        context.aggregator_response = result["content"]
        # Extract tool calls if any
        context.tool_calls = self._extract_tool_calls(result["content"])
        return context

    def _build_aggregator_messages(self, context: MOAContext) -> List[Dict[str, str]]:
        messages = []
        if context.system_prompt:
            messages.append({"role": "system", "content": context.system_prompt})
        if context.conversation_history:
            messages.extend([{"role": h["role"], "content": h["content"]} for h in context.conversation_history[-10:]])
        # Append reference outputs as context
        if context.reference_outputs:
            ref_text = "\n\n--- Reference Model Outputs ---\n\n"
            for ref in context.reference_outputs:
                if ref.error:
                    ref_text += f"[{ref.model_provider}/{ref.model_name}] ERROR: {ref.error}\n\n"
                else:
                    ref_text += f"[{ref.model_provider}/{ref.model_name}] {ref.content}\n\n"
            messages.append({"role": "system", "content": ref_text})
        messages.append({"role": "user", "content": context.user_message})
        return messages

    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Extract tool calls from aggregator response."""
        tool_calls = []
        # Look for JSON tool call patterns
        patterns = [
            r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^}]*\})\s*\}',
            r'```json\s*\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^}]*\})\s*\}\s*```',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                try:
                    tool_calls.append({
                        "tool": match.group(1),
                        "arguments": json.loads(match.group(2)),
                    })
                except Exception:
                    pass
        return tool_calls


class MOAEngine:
    """Top-level MoA orchestrator."""

    def __init__(self, repo_root: str = "") -> None:
        self.repo_root = repo_root
        self.router = ModelRouter()
        self.cache = PromptCache()
        self.reference_engine = MOAReferenceEngine(self.router, self.cache)
        self.aggregator = MOAAggregator(self.router, self.cache)
        self.presets: Dict[str, MOAPreset] = {}
        self.active_preset: Optional[str] = None
        self._turn_counter = 0
        self._lock = threading.RLock()
        self._history: List[MOAContext] = []
        self._seed_presets()

    def _seed_presets(self) -> None:
        # Default preset: multi-model aggregation
        self.presets["default"] = MOAPreset(
            preset_id="default",
            name="Default MoA",
            reference_models=[
                ModelConfig(provider="local", model="analyst", temperature=0.6),
                ModelConfig(provider="local", model="critic", temperature=0.6),
            ],
            aggregator=ModelConfig(provider="local", model="leader", temperature=0.4),
            reference_temperature=0.6,
            aggregator_temperature=0.4,
            description="Default 2-reference + 1-aggregator MoA preset",
        )
        # Review preset: focused on code review
        self.presets["review"] = MOAPreset(
            preset_id="review",
            name="Code Review MoA",
            reference_models=[
                ModelConfig(provider="local", model="security", temperature=0.5),
                ModelConfig(provider="local", model="performance", temperature=0.5),
                ModelConfig(provider="local", model="style", temperature=0.7),
            ],
            aggregator=ModelConfig(provider="local", model="architect", temperature=0.3),
            reference_temperature=0.5,
            aggregator_temperature=0.3,
            description="3-reference code review + architect aggregator",
        )
        # Swarm preset: distributed nodes as references
        self.presets["swarm"] = MOAPreset(
            preset_id="swarm",
            name="Swarm MoA",
            reference_models=[
                ModelConfig(provider="swarm", model="node_1", temperature=0.6),
                ModelConfig(provider="swarm", model="node_2", temperature=0.6),
                ModelConfig(provider="swarm", model="node_3", temperature=0.6),
            ],
            aggregator=ModelConfig(provider="swarm", model="coordinator", temperature=0.4),
            reference_temperature=0.6,
            aggregator_temperature=0.4,
            description="Swarm intelligence MoA with 3 nodes + coordinator",
        )

    def configure_preset(self, preset: MOAPreset) -> None:
        with self._lock:
            self.presets[preset.preset_id] = preset

    def select_preset(self, preset_id: str) -> bool:
        with self._lock:
            if preset_id in self.presets:
                self.active_preset = preset_id
                return True
            return False

    def run_turn(self, user_message: str, system_prompt: str = "", tool_schema: Optional[Dict[str, Any]] = None) -> MOAContext:
        """Execute one MoA turn."""
        with self._lock:
            self._turn_counter += 1
            preset = self.presets.get(self.active_preset or "default")
            if not preset or not preset.enabled:
                # Fallback: aggregator only
                preset = MOAPreset(
                    preset_id="fallback",
                    name="Fallback",
                    reference_models=[],
                    aggregator=ModelConfig(provider="local", model="default"),
                )

            context = MOAContext(
                user_message=user_message,
                system_prompt=system_prompt,
                conversation_history=self._get_history(),
                tool_schema=tool_schema,
                turn_id=self._turn_counter,
            )

            # Step 1: Run reference models (if enabled and has references)
            if preset.enabled and preset.reference_models:
                context.reference_outputs = self.reference_engine.run(preset, context)

            # Step 2: Run aggregator
            context = self.aggregator.run(preset, context)

            # Step 3: Record history
            self._history.append(context)
            if len(self._history) > 100:
                self._history = self._history[-50:]

            return context

    def execute_tools(self, context: MOAContext, tool_registry: Optional[Dict[str, Callable]] = None) -> List[Dict[str, Any]]:
        """Execute tool calls from aggregator response."""
        results = []
        for tc in context.tool_calls:
            tool_name = tc.get("tool")
            args = tc.get("arguments", {})
            if tool_registry and tool_name in tool_registry:
                try:
                    result = tool_registry[tool_name](**args)
                    results.append({"tool": tool_name, "status": "success", "result": result})
                except Exception as e:
                    results.append({"tool": tool_name, "status": "error", "error": str(e)})
            else:
                results.append({"tool": tool_name, "status": "not_found", "error": "Tool not registered"})
        return results

    def _get_history(self) -> List[Dict[str, str]]:
        history = []
        for ctx in self._history[-10:]:
            history.append({"role": "user", "content": ctx.user_message})
            history.append({"role": "assistant", "content": ctx.aggregator_response})
        return history

    def get_preset(self, preset_id: str) -> Optional[MOAPreset]:
        return self.presets.get(preset_id)

    def list_presets(self) -> List[Dict[str, Any]]:
        return [{"id": k, "name": v.name, "enabled": v.enabled, "description": v.description} for k, v in self.presets.items()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_turns": self._turn_counter,
            "active_preset": self.active_preset,
            "presets": len(self.presets),
            "cache": self.cache.get_stats(),
            "router": self.router.get_stats(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
