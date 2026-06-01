"""Multimodal Processor — Text + image + audio simulation, modality fusion, cross-modal reasoning.

Modul ini menyediakan:
- ModalityEncoder untuk encoding berbagai input modalities
- MultimodalFusion untuk menggabungkan multiple modalities
- CrossModalReasoner untuk reasoning across modalities
- ModalityRouter untuk routing ke encoder yang sesuai
- ModalityCache untuk caching multimodal representations

Arsitektur: Text/Image/Audio → Encoder → Fusion → Reasoner → Output
"""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ModalityType(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    STRUCTURED = "structured"


class FusionStrategy(Enum):
    CONCATENATION = auto()
    ATTENTION = auto()
    WEIGHTED = auto()
    INTERACTION = auto()


@dataclass
class ModalityInput:
    """Input from a single modality."""
    input_id: str
    modality: ModalityType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_text(self) -> str:
        if self.modality == ModalityType.TEXT:
            return str(self.content)
        elif self.modality == ModalityType.IMAGE:
            return f"[Image: {self.metadata.get('description', 'visual content')}]"
        elif self.modality == ModalityType.AUDIO:
            return f"[Audio: {self.metadata.get('transcript', 'audio content')}]"
        elif self.modality == ModalityType.VIDEO:
            return f"[Video: {self.metadata.get('description', 'video content')}]"
        return f"[{self.modality.value}: {str(self.content)[:50]}]"


@dataclass
class ModalityRepresentation:
    """Encoded representation of a modality."""
    rep_id: str
    modality: ModalityType
    features: List[float]
    text_equivalent: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FusionResult:
    """Result of multimodal fusion."""
    fusion_id: str
    representations: List[ModalityRepresentation]
    fused_features: List[float]
    strategy: FusionStrategy
    confidence: float = 0.0


class ModalityEncoder:
    """Encode different modalities into feature vectors."""

    def __init__(self, dim: int = 64):
        self.dim = dim

    def encode(self, input_data: ModalityInput) -> ModalityRepresentation:
        if input_data.modality == ModalityType.TEXT:
            features = self._encode_text(str(input_data.content))
        elif input_data.modality == ModalityType.IMAGE:
            features = self._encode_image(input_data.metadata)
        elif input_data.modality == ModalityType.AUDIO:
            features = self._encode_audio(input_data.metadata)
        elif input_data.modality == ModalityType.VIDEO:
            features = self._encode_video(input_data.metadata)
        else:
            features = [0.0] * self.dim
        return ModalityRepresentation(
            rep_id=str(uuid.uuid4())[:12],
            modality=input_data.modality,
            features=features,
            text_equivalent=input_data.to_text()
        )

    def _encode_text(self, text: str) -> List[float]:
        # Simple hash-based encoding simulation
        h = hashlib.sha256(text.encode()).hexdigest()
        return [int(h[i:i+2], 16) / 255.0 for i in range(0, min(len(h), self.dim * 2), 2)]

    def _encode_image(self, metadata: Dict[str, Any]) -> List[float]:
        desc = metadata.get("description", "")
        return self._encode_text(f"IMG:{desc}")

    def _encode_audio(self, metadata: Dict[str, Any]) -> List[float]:
        transcript = metadata.get("transcript", "")
        return self._encode_text(f"AUD:{transcript}")

    def _encode_video(self, metadata: Dict[str, Any]) -> List[float]:
        desc = metadata.get("description", "")
        return self._encode_text(f"VID:{desc}")


class MultimodalFusion:
    """Fuse multiple modality representations."""

    def __init__(self, strategy: FusionStrategy = FusionStrategy.WEIGHTED, dim: int = 64):
        self.strategy = strategy
        self.dim = dim
        self._weights: Dict[ModalityType, float] = {
            ModalityType.TEXT: 0.4,
            ModalityType.IMAGE: 0.3,
            ModalityType.AUDIO: 0.2,
            ModalityType.VIDEO: 0.25,
            ModalityType.STRUCTURED: 0.35,
        }

    def fuse(self, representations: List[ModalityRepresentation]) -> FusionResult:
        if not representations:
            return FusionResult(
                fusion_id=str(uuid.uuid4())[:12],
                representations=[],
                fused_features=[0.0] * self.dim,
                strategy=self.strategy,
                confidence=0.0
            )
        if self.strategy == FusionStrategy.CONCATENATION:
            fused = self._concatenate(representations)
        elif self.strategy == FusionStrategy.WEIGHTED:
            fused = self._weighted(representations)
        elif self.strategy == FusionStrategy.ATTENTION:
            fused = self._attention(representations)
        else:
            fused = self._interaction(representations)
        return FusionResult(
            fusion_id=str(uuid.uuid4())[:12],
            representations=representations,
            fused_features=fused,
            strategy=self.strategy,
            confidence=sum(r.metadata.get("confidence", 1.0) for r in representations) / len(representations)
        )

    def _concatenate(self, reps: List[ModalityRepresentation]) -> List[float]:
        result = []
        for r in reps:
            result.extend(r.features[:self.dim // len(reps)])
        return result[:self.dim]

    def _weighted(self, reps: List[ModalityRepresentation]) -> List[float]:
        result = [0.0] * self.dim
        total_weight = 0.0
        for r in reps:
            weight = self._weights.get(r.modality, 0.1)
            for i in range(min(len(r.features), self.dim)):
                result[i] += r.features[i] * weight
            total_weight += weight
        if total_weight > 0:
            result = [x / total_weight for x in result]
        return result

    def _attention(self, reps: List[ModalityRepresentation]) -> List[float]:
        # Simple attention: text gets higher attention
        result = [0.0] * self.dim
        for r in reps:
            weight = 1.5 if r.modality == ModalityType.TEXT else 1.0
            for i in range(min(len(r.features), self.dim)):
                result[i] += r.features[i] * weight
        return [x / len(reps) for x in result]

    def _interaction(self, reps: List[ModalityRepresentation]) -> List[float]:
        # Element-wise product interaction
        if not reps:
            return [0.0] * self.dim
        result = [1.0] * self.dim
        for r in reps:
            for i in range(min(len(r.features), self.dim)):
                result[i] *= r.features[i]
        return result

    def set_weight(self, modality: ModalityType, weight: float) -> None:
        self._weights[modality] = weight


class CrossModalReasoner:
    """Reason across multiple modalities."""

    def __init__(self, encoder: ModalityEncoder, fusion: MultimodalFusion):
        self.encoder = encoder
        self.fusion = fusion

    def reason(self, inputs: List[ModalityInput], question: str) -> Dict[str, Any]:
        reps = [self.encoder.encode(inp) for inp in inputs]
        fused = self.fusion.fuse(reps)
        text_context = " ".join(r.text_equivalent for r in reps)
        return {
            "question": question,
            "context": text_context,
            "modalities": [r.modality.value for r in reps],
            "fused_confidence": fused.confidence,
            "answer": f"Based on {len(inputs)} modalities: {text_context[:100]}...",
            "reasoning": "Cross-modal alignment and fusion performed."
        }

    def describe_image(self, image_input: ModalityInput, text_context: Optional[ModalityInput] = None) -> str:
        reps = [self.encoder.encode(image_input)]
        if text_context:
            reps.append(self.encoder.encode(text_context))
        fused = self.fusion.fuse(reps)
        return f"Image description: {image_input.to_text()} (confidence: {fused.confidence:.2f})"

    def answer_from_audio(self, audio_input: ModalityInput, question: str) -> str:
        rep = self.encoder.encode(audio_input)
        return f"From audio: {audio_input.to_text()} -> Answer: {question}"


class ModalityRouter:
    """Route inputs to appropriate encoder and processor."""

    def __init__(self):
        self._routes: Dict[ModalityType, Callable[[ModalityInput], Any]] = {}

    def register(self, modality: ModalityType, handler: Callable[[ModalityInput], Any]) -> None:
        self._routes[modality] = handler

    def process(self, input_data: ModalityInput) -> Any:
        handler = self._routes.get(input_data.modality)
        if handler:
            return handler(input_data)
        return input_data.to_text()

    def batch_process(self, inputs: List[ModalityInput]) -> List[Any]:
        return [self.process(inp) for inp in inputs]


class ModalityCache:
    """Cache for multimodal representations."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache: Dict[str, ModalityRepresentation] = {}

    def _make_key(self, input_data: ModalityInput) -> str:
        return hashlib.sha256(f"{input_data.modality.value}:{str(input_data.content)}".encode()).hexdigest()[:16]

    def get(self, input_data: ModalityInput) -> Optional[ModalityRepresentation]:
        key = self._make_key(input_data)
        return self._cache.get(key)

    def put(self, input_data: ModalityInput, rep: ModalityRepresentation) -> None:
        key = self._make_key(input_data)
        if len(self._cache) >= self.max_size:
            self._cache.pop(next(iter(self._cache.keys())))
        self._cache[key] = rep

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)


class MultimodalProcessor:
    """End-to-end multimodal processor."""

    def __init__(self, dim: int = 64):
        self.encoder = ModalityEncoder(dim)
        self.fusion = MultimodalFusion(FusionStrategy.WEIGHTED, dim)
        self.reasoner = CrossModalReasoner(self.encoder, self.fusion)
        self.router = ModalityRouter()
        self.cache = ModalityCache()

    def process(self, inputs: List[ModalityInput], question: str = "") -> Dict[str, Any]:
        reps = []
        for inp in inputs:
            cached = self.cache.get(inp)
            if cached:
                reps.append(cached)
            else:
                rep = self.encoder.encode(inp)
                self.cache.put(inp, rep)
                reps.append(rep)
        return self.reasoner.reason(inputs, question)

    def process_single(self, input_data: ModalityInput) -> ModalityRepresentation:
        cached = self.cache.get(input_data)
        if cached:
            return cached
        rep = self.encoder.encode(input_data)
        self.cache.put(input_data, rep)
        return rep

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cache_size": self.cache.size(),
            "fusion_strategy": self.fusion.strategy.name,
            "encoder_dim": self.encoder.dim,
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MULTIMODAL PROCESSOR DEMO")
    print("=" * 70)

    processor = MultimodalProcessor(dim=32)

    # 1. Text processing
    print("\n[1] Text Processing")
    text_input = ModalityInput(
        input_id="t1",
        modality=ModalityType.TEXT,
        content="Explain how photosynthesis works in plants."
    )
    rep = processor.process_single(text_input)
    print(f"  Text: {rep.text_equivalent}")
    print(f"  Features dim: {len(rep.features)}")

    # 2. Image processing
    print("\n[2] Image Processing")
    image_input = ModalityInput(
        input_id="i1",
        modality=ModalityType.IMAGE,
        content="<image_data>",
        metadata={"description": "A diagram of photosynthesis in a leaf cell"}
    )
    rep = processor.process_single(image_input)
    print(f"  Image: {rep.text_equivalent}")
    print(f"  Features dim: {len(rep.features)}")

    # 3. Audio processing
    print("\n[3] Audio Processing")
    audio_input = ModalityInput(
        input_id="a1",
        modality=ModalityType.AUDIO,
        content="<audio_data>",
        metadata={"transcript": "The process of photosynthesis converts light energy into chemical energy"}
    )
    rep = processor.process_single(audio_input)
    print(f"  Audio: {rep.text_equivalent}")
    print(f"  Features dim: {len(rep.features)}")

    # 4. Cross-modal reasoning
    print("\n[4] Cross-Modal Reasoning")
    result = processor.process([text_input, image_input, audio_input], "What is photosynthesis?")
    print(f"  Question: {result['question']}")
    print(f"  Modalities: {result['modalities']}")
    print(f"  Confidence: {result['fused_confidence']:.2f}")
    print(f"  Answer: {result['answer'][:80]}...")

    # 5. Fusion strategies comparison
    print("\n[5] Fusion Strategies Comparison")
    for strategy in [FusionStrategy.CONCATENATION, FusionStrategy.WEIGHTED, FusionStrategy.ATTENTION, FusionStrategy.INTERACTION]:
        fusion = MultimodalFusion(strategy, dim=32)
        reps = [processor.process_single(inp) for inp in [text_input, image_input]]
        result = fusion.fuse(reps)
        print(f"  {strategy.name}: confidence={result.confidence:.2f}, features={len(result.fused_features)}")

    # 6. Image description with text context
    print("\n[6] Image Description with Context")
    description = processor.reasoner.describe_image(image_input, text_input)
    print(f"  {description}")

    # 7. Cache performance
    print("\n[7] Cache Performance")
    print(f"  Cache size before: {processor.cache.size()}")
    # Process same inputs again (should hit cache)
    processor.process([text_input, image_input])
    print(f"  Cache size after: {processor.cache.size()}")
    print(f"  Stats: {processor.get_stats()}")

    # 8. Structured data
    print("\n[8] Structured Data Processing")
    structured_input = ModalityInput(
        input_id="s1",
        modality=ModalityType.STRUCTURED,
        content={"temperature": 25, "humidity": 60, "light": 800},
        metadata={"type": "sensor_data"}
    )
    rep = processor.process_single(structured_input)
    print(f"  Structured: {rep.text_equivalent}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
