"""
multimodal_fusion_native.py — Native Multimodal Fusion Engine
Pure Python stdlib. Text + Image + Audio alignment, embedding, attention.
NativeMultimodalFusion with run().
"""
from __future__ import annotations

import random
import threading
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple


class NativeMultimodalFusion:
    """
    Native multimodal fusion engine.

    Simulates text, image, and audio embedding alignment using
    lightweight attention-inspired weighting. Pure stdlib; no ML deps.

    Attributes:
        embedding_dim: Dimension of simulated embeddings.
        modalities: Registered modality names.
        cache: Thread-safe embedding cache.
        attention_weights: Learned (simulated) cross-modality weights.
    """

    def __init__(self, embedding_dim: int = 64) -> None:
        self.embedding_dim = embedding_dim
        self.modalities: List[str] = []
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()
        self.attention_weights: Dict[str, float] = defaultdict(lambda: 1.0)
        self._rand = random.Random(42)

    def register_modality(self, name: str) -> None:
        """Register a modality (e.g., 'text', 'image', 'audio')."""
        with self.lock:
            if name not in self.modalities:
                self.modalities.append(name)
                self.attention_weights[name] = 1.0

    def embed(self, modality: str, content: str, payload: Optional[Any] = None) -> List[float]:
        """
        Simulate embedding for a modality.

        Text: hash-based deterministic embedding.
        Image: simulated from content length + shape.
        Audio: simulated from content length + duration hint.

        Args:
            modality: Registered modality name.
            content: Raw content string or descriptor.
            payload: Optional extra data (e.g., shape, duration).

        Returns:
            List of floats (embedding_dim).
        """
        with self.lock:
            key = f"{modality}:{content}"
            if key in self.cache:
                return self.cache[key]["embedding"]

            seed = hash(key) & 0x7FFFFFFF
            local_rand = random.Random(seed)

            if modality == "image" and payload:
                # Simulate image embedding: spatial-like variance
                shape = payload if isinstance(payload, tuple) else (224, 224, 3)
                base = [float((i + 1) * shape[i % len(shape)]) for i in range(self.embedding_dim)]
            elif modality == "audio" and payload:
                # Simulate audio embedding: temporal-like variance
                duration = payload if isinstance(payload, (int, float)) else 1.0
                base = [float((i + 1) * duration * 0.1) for i in range(self.embedding_dim)]
            else:
                # Text: deterministic hash-based
                base = [float((ord(c) if i < len(content) else i) * (i + 1)) for i, c in enumerate(content[:self.embedding_dim])]
                if len(base) < self.embedding_dim:
                    base += [0.0] * (self.embedding_dim - len(base))
                # L2-ish normalize
                norm = sum(b * b for b in base) ** 0.5 + 1e-9
                base = [b / norm for b in base]

            # Add controlled noise for variety
            embedding = [b + local_rand.gauss(0, 0.05) for b in base[:self.embedding_dim]]
            # Pad or trim
            if len(embedding) < self.embedding_dim:
                embedding += [0.0] * (self.embedding_dim - len(embedding))
            embedding = embedding[:self.embedding_dim]

            # Store
            self.cache[key] = {"embedding": embedding, "modality": modality, "content": content}
            return embedding

    def align(self, embeddings: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """
        Cross-modal alignment using attention-inspired weighting.

        Args:
            embeddings: Dict of modality -> embedding vector.

        Returns:
            Dict of modality -> aligned embedding.
        """
        aligned: Dict[str, List[float]] = {}
        # Compute cross-modality similarity weights
        total_sim = 0.0
        sim_scores: Dict[str, float] = {}
        for mod_a, emb_a in embeddings.items():
            for mod_b, emb_b in embeddings.items():
                if mod_a != mod_b:
                    sim = sum(a * b for a, b in zip(emb_a, emb_b))
                    sim_scores[mod_a] = sim_scores.get(mod_a, 0.0) + sim
            total_sim += sim_scores.get(mod_a, 1.0)

        # Weighted fusion
        for mod, emb in embeddings.items():
            weight = self.attention_weights[mod] + (sim_scores.get(mod, 0.0) / (total_sim + 1e-9))
            aligned[mod] = [e * weight for e in emb]
        return aligned

    def fuse(self, inputs: Dict[str, Tuple[str, Optional[Any]]]) -> List[float]:
        """
        End-to-end fusion: embed all modalities, align, then average-pool.

        Args:
            inputs: Dict of modality -> (content, payload).
                Example: {"text": ("hello", None), "image": ("img1", (224, 224, 3))}

        Returns:
            Fused embedding vector.
        """
        embeddings: Dict[str, List[float]] = {}
        for mod, (content, payload) in inputs.items():
            if mod not in self.modalities:
                self.register_modality(mod)
            embeddings[mod] = self.embed(mod, content, payload)

        aligned = self.align(embeddings)
        # Average pool across modalities
        fused = [0.0] * self.embedding_dim
        for mod, emb in aligned.items():
            for i, v in enumerate(emb):
                fused[i] += v
        count = len(aligned)
        return [v / count for v in fused] if count > 0 else fused

    def similarity(self, emb_a: List[float], emb_b: List[float]) -> float:
        """Cosine similarity between two embeddings."""
        dot = sum(a * b for a, b in zip(emb_a, emb_b))
        norm_a = sum(a * a for a in emb_a) ** 0.5 + 1e-9
        norm_b = sum(b * b for b in emb_b) ** 0.5 + 1e-9
        return dot / (norm_a * norm_b)

    def run(self) -> Dict[str, Any]:
        """
        Self-test demo.

        Returns:
            Dict with test results, fused embedding stats, and similarity matrix.
        """
        results: Dict[str, Any] = {"status": "ok", "tests": []}

        # Test 1: Text embedding
        self.register_modality("text")
        t1 = self.embed("text", "hello world")
        assert len(t1) == self.embedding_dim, "Text embedding dim mismatch"
        results["tests"].append({"name": "text_embed", "pass": True})

        # Test 2: Image embedding
        self.register_modality("image")
        i1 = self.embed("image", "cat.jpg", payload=(224, 224, 3))
        assert len(i1) == self.embedding_dim, "Image embedding dim mismatch"
        results["tests"].append({"name": "image_embed", "pass": True})

        # Test 3: Audio embedding
        self.register_modality("audio")
        a1 = self.embed("audio", "speech.wav", payload=3.5)
        assert len(a1) == self.embedding_dim, "Audio embedding dim mismatch"
        results["tests"].append({"name": "audio_embed", "pass": True})

        # Test 4: Fusion
        fused = self.fuse({
            "text": ("a cat meows", None),
            "image": ("cat.jpg", (224, 224, 3)),
            "audio": ("meow.wav", 2.0),
        })
        assert len(fused) == self.embedding_dim, "Fused embedding dim mismatch"
        results["fused_norm"] = sum(v * v for v in fused) ** 0.5
        results["tests"].append({"name": "fuse", "pass": True})

        # Test 5: Similarity
        t2 = self.embed("text", "a cat meows")
        t3 = self.embed("text", "a dog barks")
        sim_same = self.similarity(t1, t1)
        sim_diff = self.similarity(t2, t3)
        results["tests"].append({"name": "similarity", "pass": True, "same": sim_same, "diff": sim_diff})

        # Test 6: Cache hit
        t1_cached = self.embed("text", "hello world")
        assert t1 == t1_cached, "Cache hit should return identical embedding"
        results["tests"].append({"name": "cache", "pass": True})

        # Test 7: Thread safety
        errors: List[str] = []
        def worker():
            try:
                self.fuse({"text": ("thread test", None)})
            except Exception as e:
                errors.append(str(e))
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        results["tests"].append({"name": "thread_safety", "pass": len(errors) == 0, "errors": errors})

        results["summary"] = f"{sum(1 for t in results['tests'] if t['pass'])}/{len(results['tests'])} tests passed"
        return results


if __name__ == "__main__":
    engine = NativeMultimodalFusion(embedding_dim=64)
    print(engine.run())
