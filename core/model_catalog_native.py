#!/usr/bin/env python3
"""
Model Catalog for MAGNATRIX-OS Local LLM Hosting
Curated registry of lightweight, high-performance open-source LLMs.
Hardware-aware model selection with quantization profiles.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Dict, List, Optional, Tuple, Any


class QuantizationLevel(enum.Enum):
    """GGUF quantization presets. Lower = smaller/faster, higher = better quality."""
    Q2_K = "Q2_K"      # ~2-bit, smallest, lowest quality
    Q3_K_S = "Q3_K_S"  # ~3-bit small
    Q3_K_M = "Q3_K_M"  # ~3-bit medium
    Q3_K_L = "Q3_K_L"  # ~3-bit large
    Q4_K_S = "Q4_K_S"  # ~4-bit small
    Q4_K_M = "Q4_K_M"  # ~4-bit medium — sweet spot for most use cases
    Q4_0 = "Q4_0"      # Legacy 4-bit
    Q5_K_S = "Q5_K_S"  # ~5-bit small
    Q5_K_M = "Q5_K_M"  # ~5-bit medium — high quality
    Q6_K = "Q6_K"      # ~6-bit — near FP16 quality
    Q8_0 = "Q8_0"      # ~8-bit — best quantized quality


class ModelFamily(enum.Enum):
    LLAMA = "llama"         # Meta AI
    QWEN = "qwen"           # Alibaba Cloud
    PHI = "phi"             # Microsoft
    GEMMA = "gemma"         # Google
    MISTRAL = "mistral"     # Mistral AI
    DEEPSEEK = "deepseek"   # DeepSeek AI
    LLAMA4 = "llama4"       # Meta AI (latest)
    SMOLLM = "smollm"       # HuggingFace BigCode
    GRANITE = "granite"     # IBM


@dataclasses.dataclass
class ModelSpec:
    """Specification for a downloadable local LLM."""
    # Identity
    family: ModelFamily
    model_id: str              # Ollama model ID (e.g., "llama3.2:3b")
    name: str                  # Human-readable name
    description: str

    # Capabilities
    parameters: str            # e.g., "3B", "7B", "8B"
    context_window: int        # Maximum token context
    supports_vision: bool = False
    supports_tools: bool = False
    supports_code: bool = False
    supports_embedding: bool = False
    supports_multilingual: bool = False

    # Hardware requirements per quantization level
    # Maps QuantizationLevel -> (ram_gb_min, ram_gb_recommended, disk_gb)
    hardware_profile: Dict[QuantizationLevel, Tuple[float, float, float]] = dataclasses.field(default_factory=dict)

    # Default quantization for auto-selection
    default_quantization: QuantizationLevel = QuantizationLevel.Q4_K_M

    # Ollama-specific
    ollama_tags: List[str] = dataclasses.field(default_factory=list)

    # Performance ratings (1-10)
    speed_rating: int = 5      # Inference speed
    quality_rating: int = 5    # Output quality
    reasoning_rating: int = 5  # Reasoning/coding ability

    # URL to model card / docs
    docs_url: str = ""

    def ram_required_gb(self, quant: Optional[QuantizationLevel] = None) -> float:
        """Minimum RAM required for given quantization."""
        q = quant or self.default_quantization
        return self.hardware_profile.get(q, (4.0, 8.0, 2.0))[0]

    def ram_recommended_gb(self, quant: Optional[QuantizationLevel] = None) -> float:
        """Recommended RAM for comfortable operation."""
        q = quant or self.default_quantization
        return self.hardware_profile.get(q, (4.0, 8.0, 2.0))[1]

    def disk_required_gb(self, quant: Optional[QuantizationLevel] = None) -> float:
        """Disk space required for the model file."""
        q = quant or self.default_quantization
        return self.hardware_profile.get(q, (4.0, 8.0, 2.0))[2]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family": self.family.value,
            "model_id": self.model_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "context_window": self.context_window,
            "supports_vision": self.supports_vision,
            "supports_tools": self.supports_tools,
            "supports_code": self.supports_code,
            "supports_embedding": self.supports_embedding,
            "supports_multilingual": self.supports_multilingual,
            "hardware_profile": {k.value: v for k, v in self.hardware_profile.items()},
            "default_quantization": self.default_quantization.value,
            "ollama_tags": self.ollama_tags,
            "speed_rating": self.speed_rating,
            "quality_rating": self.quality_rating,
            "reasoning_rating": self.reasoning_rating,
            "docs_url": self.docs_url,
        }


class ModelCatalog:
    """Curated catalog of recommended local LLMs for MAGNATRIX-OS."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelSpec] = {}
        self._register_defaults()

    def _register(self, spec: ModelSpec) -> None:
        self._models[spec.model_id] = spec

    def _register_defaults(self) -> None:
        """Register the curated list of best lightweight models."""

        # ────────────────────────────────────────────
        # META LLAMA FAMILY
        # ────────────────────────────────────────────

        # Llama 3.2 3B — Ultra-lightweight, massive context, best for edge/CPU
        self._register(ModelSpec(
            family=ModelFamily.LLAMA,
            model_id="llama3.2:3b",
            name="Llama 3.2 3B",
            description="Meta's ultra-lightweight model. 128K context window, excellent for edge devices and CPU-only inference. Best speed/quality ratio under 4B parameters.",
            parameters="3B",
            context_window=128000,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (2.0, 4.0, 1.9),
                QuantizationLevel.Q5_K_M: (2.5, 5.0, 2.2),
                QuantizationLevel.Q8_0: (4.0, 8.0, 3.4),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["3b", " instruct", "text-only"],
            speed_rating=9,
            quality_rating=7,
            reasoning_rating=7,
            docs_url="https://ollama.com/library/llama3.2",
        ))

        # Llama 3.2 1B — Extreme lightweight
        self._register(ModelSpec(
            family=ModelFamily.LLAMA,
            model_id="llama3.2:1b",
            name="Llama 3.2 1B",
            description="Meta's smallest model. 128K context, blazing fast on any hardware. Good for simple tasks, classification, and fast responses.",
            parameters="1B",
            context_window=128000,
            supports_tools=False,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (1.0, 2.0, 0.7),
                QuantizationLevel.Q8_0: (1.5, 3.0, 1.3),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["1b", "fast"],
            speed_rating=10,
            quality_rating=5,
            reasoning_rating=5,
            docs_url="https://ollama.com/library/llama3.2",
        ))

        # Llama 3.1 8B — The workhorse
        self._register(ModelSpec(
            family=ModelFamily.LLAMA,
            model_id="llama3.1:8b",
            name="Llama 3.1 8B",
            description="Meta's most popular open model. 128K context, strong reasoning, coding, and tool use. The standard for local LLM deployments.",
            parameters="8B",
            context_window=128000,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (5.0, 8.0, 4.7),
                QuantizationLevel.Q5_K_M: (6.0, 10.0, 5.5),
                QuantizationLevel.Q8_0: (10.0, 16.0, 8.5),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["8b", "instruct", "tool-use"],
            speed_rating=7,
            quality_rating=8,
            reasoning_rating=8,
            docs_url="https://ollama.com/library/llama3.1",
        ))

        # Llama 4 Scout — Latest with long context (when available on Ollama)
        self._register(ModelSpec(
            family=ModelFamily.LLAMA4,
            model_id="llama4:scout",
            name="Llama 4 Scout",
            description="Meta's latest multimodal model with 10M token context. Mixture-of-Experts architecture. State-of-the-art for long-document analysis.",
            parameters="109B",
            context_window=10000000,
            supports_vision=True,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (64.0, 128.0, 60.0),
                QuantizationLevel.Q5_K_M: (80.0, 160.0, 72.0),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["109b", "moe", "multimodal", "long-context"],
            speed_rating=4,
            quality_rating=10,
            reasoning_rating=10,
            docs_url="https://ollama.com/library/llama4",
        ))

        # ────────────────────────────────────────────
        # QWEN FAMILY (Alibaba)
        # ────────────────────────────────────────────

        # Qwen 2.5 7B — Strong all-rounder, excellent for coding
        self._register(ModelSpec(
            family=ModelFamily.QWEN,
            model_id="qwen2.5:7b",
            name="Qwen 2.5 7B",
            description="Alibaba's flagship open model. 131K context, exceptional coding and math reasoning. Strong multilingual support including Chinese, Japanese, Korean.",
            parameters="7B",
            context_window=131072,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (5.0, 8.0, 4.4),
                QuantizationLevel.Q5_K_M: (6.0, 10.0, 5.2),
                QuantizationLevel.Q8_0: (10.0, 16.0, 8.0),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["7b", "coding", "multilingual"],
            speed_rating=7,
            quality_rating=8,
            reasoning_rating=9,
            docs_url="https://ollama.com/library/qwen2.5",
        ))

        # Qwen 2.5 14B — Higher quality, still manageable
        self._register(ModelSpec(
            family=ModelFamily.QWEN,
            model_id="qwen2.5:14b",
            name="Qwen 2.5 14B",
            description="Larger Qwen variant with significantly better reasoning. 131K context. Best for complex coding and analysis tasks on machines with 16GB+ RAM.",
            parameters="14B",
            context_window=131072,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (9.0, 16.0, 8.7),
                QuantizationLevel.Q5_K_M: (11.0, 20.0, 10.2),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["14b", "coding", "advanced"],
            speed_rating=6,
            quality_rating=9,
            reasoning_rating=9,
            docs_url="https://ollama.com/library/qwen2.5",
        ))

        # Qwen 2.5 0.5B — Tiny but capable
        self._register(ModelSpec(
            family=ModelFamily.QWEN,
            model_id="qwen2.5:0.5b",
            name="Qwen 2.5 0.5B",
            description="Smallest Qwen model. 131K context window. Surprisingly capable for classification, summarization, and simple Q&A. Runs on Raspberry Pi.",
            parameters="0.5B",
            context_window=131072,
            supports_tools=False,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (0.5, 1.0, 0.4),
                QuantizationLevel.Q8_0: (1.0, 2.0, 0.7),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["0.5b", "tiny", "edge"],
            speed_rating=10,
            quality_rating=5,
            reasoning_rating=5,
            docs_url="https://ollama.com/library/qwen2.5",
        ))

        # Qwen 2.5 Coder — Specialized for code
        self._register(ModelSpec(
            family=ModelFamily.QWEN,
            model_id="qwen2.5-coder:7b",
            name="Qwen 2.5 Coder 7B",
            description="Code-specialized Qwen model. Trained on 5.5 trillion code tokens. Exceptional at code generation, completion, and debugging across 40+ languages.",
            parameters="7B",
            context_window=131072,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (5.0, 8.0, 4.4),
                QuantizationLevel.Q5_K_M: (6.0, 10.0, 5.2),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["7b", "code-specialized", "fill-in-middle"],
            speed_rating=7,
            quality_rating=8,
            reasoning_rating=9,
            docs_url="https://ollama.com/library/qwen2.5-coder",
        ))

        # ────────────────────────────────────────────
        # MICROSOFT PHI FAMILY
        # ────────────────────────────────────────────

        # Phi-4 Mini — Extremely efficient small model
        self._register(ModelSpec(
            family=ModelFamily.PHI,
            model_id="phi4:mini",
            name="Phi-4 Mini",
            description="Microsoft's newest small model. Remarkable quality for its size. Strong reasoning, math, and coding. 128K context. Very efficient memory usage.",
            parameters="3.8B",
            context_window=128000,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (2.5, 4.0, 2.2),
                QuantizationLevel.Q5_K_M: (3.0, 5.0, 2.6),
                QuantizationLevel.Q8_0: (5.0, 8.0, 4.2),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["3.8b", "efficient", "reasoning"],
            speed_rating=9,
            quality_rating=8,
            reasoning_rating=8,
            docs_url="https://ollama.com/library/phi4",
        ))

        # Phi-4 Regular — Larger variant
        self._register(ModelSpec(
            family=ModelFamily.PHI,
            model_id="phi4:14b",
            name="Phi-4 14B",
            description="Microsoft's larger Phi model. Excellent reasoning and instruction following. 16K context. Competitive with much larger models on many benchmarks.",
            parameters="14B",
            context_window=16000,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (9.0, 16.0, 8.5),
                QuantizationLevel.Q5_K_M: (11.0, 20.0, 10.0),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["14b", "reasoning", "instruction"],
            speed_rating=6,
            quality_rating=9,
            reasoning_rating=9,
            docs_url="https://ollama.com/library/phi4",
        ))

        # Phi-3 Mini — Previous generation, still good
        self._register(ModelSpec(
            family=ModelFamily.PHI,
            model_id="phi3:mini",
            name="Phi-3 Mini",
            description="Microsoft's earlier small model. 3.8B params, 128K context. Good for basic tasks and fast responses. Very widely compatible.",
            parameters="3.8B",
            context_window=128000,
            supports_tools=False,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (2.5, 4.0, 2.2),
                QuantizationLevel.Q8_0: (5.0, 8.0, 4.2),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["3.8b", "legacy", "fast"],
            speed_rating=9,
            quality_rating=7,
            reasoning_rating=7,
            docs_url="https://ollama.com/library/phi3",
        ))

        # ────────────────────────────────────────────
        # GOOGLE GEMMA FAMILY
        # ────────────────────────────────────────────

        # Gemma 2 9B — Google's strong performer
        self._register(ModelSpec(
            family=ModelFamily.GEMMA,
            model_id="gemma2:9b",
            name="Gemma 2 9B",
            description="Google's open model. Knowledge cutoff 2024, strong factual accuracy. 8K context. Good for general knowledge tasks and safe responses.",
            parameters="9B",
            context_window=8192,
            supports_tools=False,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (6.0, 10.0, 5.4),
                QuantizationLevel.Q5_K_M: (7.0, 12.0, 6.4),
                QuantizationLevel.Q8_0: (12.0, 20.0, 10.0),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["9b", "google", "knowledge"],
            speed_rating=7,
            quality_rating=8,
            reasoning_rating=7,
            docs_url="https://ollama.com/library/gemma2",
        ))

        # Gemma 2 2B — Ultra small
        self._register(ModelSpec(
            family=ModelFamily.GEMMA,
            model_id="gemma2:2b",
            name="Gemma 2 2B",
            description="Google's smallest open model. Good for basic classification, sentiment analysis, and simple generation. Runs on almost any device.",
            parameters="2B",
            context_window=8192,
            supports_tools=False,
            supports_code=False,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (1.5, 3.0, 1.5),
                QuantizationLevel.Q8_0: (2.5, 5.0, 2.8),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["2b", "tiny", "basic"],
            speed_rating=10,
            quality_rating=5,
            reasoning_rating=4,
            docs_url="https://ollama.com/library/gemma2",
        ))

        # ────────────────────────────────────────────
        # MISTRAL FAMILY
        # ────────────────────────────────────────────

        # Mistral 7B — Proven performer
        self._register(ModelSpec(
            family=ModelFamily.MISTRAL,
            model_id="mistral:7b",
            name="Mistral 7B",
            description="Mistral AI's original breakthrough model. Still competitive. 32K context, strong performance on many benchmarks. Widely supported ecosystem.",
            parameters="7B",
            context_window=32768,
            supports_tools=False,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (5.0, 8.0, 4.1),
                QuantizationLevel.Q5_K_M: (6.0, 10.0, 4.8),
                QuantizationLevel.Q8_0: (10.0, 16.0, 7.8),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["7b", "classic", "balanced"],
            speed_rating=7,
            quality_rating=8,
            reasoning_rating=7,
            docs_url="https://ollama.com/library/mistral",
        ))

        # Mistral Small 3.1 — Latest efficient model
        self._register(ModelSpec(
            family=ModelFamily.MISTRAL,
            model_id="mistral-small:24b",
            name="Mistral Small 3.1",
            description="Mistral's latest efficient model. 128K context, strong tool use and reasoning. 24B parameters but feels faster than many 7B models.",
            parameters="24B",
            context_window=128000,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (15.0, 24.0, 14.0),
                QuantizationLevel.Q5_K_M: (18.0, 32.0, 16.5),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["24b", "efficient", "tool-use"],
            speed_rating=7,
            quality_rating=9,
            reasoning_rating=8,
            docs_url="https://ollama.com/library/mistral-small",
        ))

        # ────────────────────────────────────────────
        # DEEPSEEK FAMILY
        # ────────────────────────────────────────────

        # DeepSeek V3 — Emerging strong model
        self._register(ModelSpec(
            family=ModelFamily.DEEPSEEK,
            model_id="deepseek-v3:671b",
            name="DeepSeek V3",
            description="DeepSeek's MoE model with 671B total params. State-of-the-art reasoning and coding. 64K context. Requires significant hardware but delivers GPT-4 class performance locally.",
            parameters="671B",
            context_window=64000,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (400.0, 512.0, 380.0),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["671b", "moe", "state-of-the-art"],
            speed_rating=3,
            quality_rating=10,
            reasoning_rating=10,
            docs_url="https://ollama.com/library/deepseek-v3",
        ))

        # DeepSeek R1 — Reasoning specialist
        self._register(ModelSpec(
            family=ModelFamily.DEEPSEEK,
            model_id="deepseek-r1:7b",
            name="DeepSeek R1 7B",
            description="Distilled reasoning model from DeepSeek. Excels at math, logic, and step-by-step reasoning. 7B parameters but punches above its weight on reasoning tasks.",
            parameters="7B",
            context_window=64000,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (5.0, 8.0, 4.5),
                QuantizationLevel.Q5_K_M: (6.0, 10.0, 5.3),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["7b", "reasoning", "distilled"],
            speed_rating=6,
            quality_rating=8,
            reasoning_rating=10,
            docs_url="https://ollama.com/library/deepseek-r1",
        ))

        # DeepSeek R1 1.5B — Tiny reasoning model
        self._register(ModelSpec(
            family=ModelFamily.DEEPSEEK,
            model_id="deepseek-r1:1.5b",
            name="DeepSeek R1 1.5B",
            description="Smallest reasoning model. Surprisingly good at math and logic for its size. 1.5B params, 64K context. Best for quick reasoning tasks on limited hardware.",
            parameters="1.5B",
            context_window=64000,
            supports_tools=False,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (1.0, 2.0, 1.1),
                QuantizationLevel.Q8_0: (2.0, 4.0, 2.0),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["1.5b", "reasoning", "tiny"],
            speed_rating=9,
            quality_rating=6,
            reasoning_rating=8,
            docs_url="https://ollama.com/library/deepseek-r1",
        ))

        # ────────────────────────────────────────────
        # SMOLLM / HUGGINGFACE
        # ────────────────────────────────────────────

        # SmolLM2 — Ultra small from HuggingFace
        self._register(ModelSpec(
            family=ModelFamily.SMOLLM,
            model_id="smollm2:1.7b",
            name="SmolLM2 1.7B",
            description="HuggingFace's ultra-small model. Trained on high-quality data. 1.7B params, 16K context. Excellent for edge devices and constrained environments.",
            parameters="1.7B",
            context_window=16384,
            supports_tools=False,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (1.0, 2.0, 1.0),
                QuantizationLevel.Q8_0: (2.0, 4.0, 1.9),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["1.7b", "edge", "huggingface"],
            speed_rating=10,
            quality_rating=6,
            reasoning_rating=6,
            docs_url="https://ollama.com/library/smollm2",
        ))

        # ────────────────────────────────────────────
        # IBM GRANITE
        # ────────────────────────────────────────────

        # Granite 3.1 8B — IBM's enterprise model
        self._register(ModelSpec(
            family=ModelFamily.GRANITE,
            model_id="granite3.1:8b",
            name="Granite 3.1 8B",
            description="IBM's enterprise-focused model. 128K context, strong code generation, tool use. Designed for business applications and RAG workflows.",
            parameters="8B",
            context_window=128000,
            supports_tools=True,
            supports_code=True,
            supports_multilingual=True,
            hardware_profile={
                QuantizationLevel.Q4_K_M: (5.0, 8.0, 4.5),
                QuantizationLevel.Q5_K_M: (6.0, 10.0, 5.3),
            },
            default_quantization=QuantizationLevel.Q4_K_M,
            ollama_tags=["8b", "enterprise", "ibm"],
            speed_rating=7,
            quality_rating=8,
            reasoning_rating=8,
            docs_url="https://ollama.com/library/granite3.1",
        ))

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get(self, model_id: str) -> Optional[ModelSpec]:
        return self._models.get(model_id)

    def list_all(self) -> List[ModelSpec]:
        return list(self._models.values())

    def list_by_family(self, family: ModelFamily) -> List[ModelSpec]:
        return [m for m in self._models.values() if m.family == family]

    def list_by_capability(self, capability: str) -> List[ModelSpec]:
        """Filter by capability: 'vision', 'tools', 'code', 'embedding', 'multilingual'."""
        attr_map = {
            "vision": "supports_vision",
            "tools": "supports_tools",
            "code": "supports_code",
            "embedding": "supports_embedding",
            "multilingual": "supports_multilingual",
        }
        attr = attr_map.get(capability)
        if not attr:
            return []
        return [m for m in self._models.values() if getattr(m, attr, False)]

    def recommend_for_hardware(
        self,
        ram_gb: float,
        cpu_cores: int = 4,
        has_gpu: bool = False,
        gpu_vram_gb: float = 0.0,
        prefer_quality: bool = False,
        prefer_speed: bool = False,
        need_vision: bool = False,
        need_tools: bool = False,
    ) -> List[ModelSpec]:
        """Recommend models sorted by best fit for detected hardware."""
        candidates = []
        for spec in self._models.values():
            # Filter by capability requirements
            if need_vision and not spec.supports_vision:
                continue
            if need_tools and not spec.supports_tools:
                continue

            # Check hardware fit
            ram_min = spec.ram_required_gb()
            ram_rec = spec.ram_recommended_gb()

            # Score: higher = better fit
            fit_score = 0.0

            # RAM fit (most important)
            if ram_gb >= ram_rec * 1.5:
                fit_score += 30  # Very comfortable
            elif ram_gb >= ram_rec:
                fit_score += 25  # Good fit
            elif ram_gb >= ram_min:
                fit_score += 15  # Tight but workable
            else:
                fit_score -= 50  # Insufficient RAM

            # GPU bonus
            if has_gpu and gpu_vram_gb > 4:
                fit_score += 10

            # CPU cores bonus for larger models
            if cpu_cores >= 8:
                fit_score += 5

            # Quality/speed preference
            if prefer_quality:
                fit_score += spec.quality_rating * 2 + spec.reasoning_rating
            if prefer_speed:
                fit_score += spec.speed_rating * 2

            # Penalty for models that are too small (waste of capable hardware)
            if ram_gb >= 16 and spec.parameters in ("0.5B", "1B", "1.5B"):
                fit_score -= 10

            # Context window bonus for RAG/multimodal use
            fit_score += min(spec.context_window / 16000, 5)

            if fit_score > 0:
                candidates.append((fit_score, spec))

        # Sort by fit score descending
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [spec for _, spec in candidates]

    def recommend_quick_picks(self, ram_gb: float) -> List[ModelSpec]:
        """Return 3-5 quick recommendation picks for common hardware profiles."""
        all_models = self.recommend_for_hardware(ram_gb)

        # Deduplicate by parameter size tier
        tiers: Dict[str, ModelSpec] = {}
        for m in all_models:
            tier = m.parameters
            if tier not in tiers:
                tiers[tier] = m

        # Return top picks from different tiers
        picks = []
        param_order = ["3B", "3.8B", "7B", "8B", "9B", "14B", "24B", "109B", "671B"]
        for p in param_order:
            if p in tiers and len(picks) < 5:
                picks.append(tiers[p])

        return picks[:5]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "models": {k: v.to_dict() for k, v in self._models.items()},
            "count": len(self._models),
            "families": list(set(m.family.value for m in self._models.values())),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    catalog = ModelCatalog()
    print("=== MAGNATRIX-OS Model Catalog ===\n")
    print(f"Total models registered: {len(catalog.list_all())}\n")

    # Show all families
    families = set(m.family.value for m in catalog.list_all())
    print(f"Families: {', '.join(sorted(families))}\n")

    # Quick picks for different RAM configurations
    for ram in [4, 8, 16, 32]:
        picks = catalog.recommend_quick_picks(ram)
        print(f"--- {ram}GB RAM recommendations ---")
        for m in picks[:3]:
            print(f"  [{m.parameters}] {m.name} — RAM: {m.ram_required_gb():.1f}GB, Context: {m.context_window:,} tokens")
        print()

    # Show coding-specialized models
    code_models = catalog.list_by_capability("code")
    print(f"Coding models: {len(code_models)}")
    for m in code_models[:5]:
        print(f"  {m.name} — reasoning: {m.reasoning_rating}/10")

    print("\n=== Model Catalog Demo Complete ===")


if __name__ == "__main__":
    _demo()
