"""Quant Autoencoder Macro - Nonlinear dimensionality reduction for macro features."""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class MacroFeature:
    feature_id: str
    name: str
    value: float
    timestamp: float = 0.0
    category: str = "economic"  # economic, inflation, labor, monetary

    def to_dict(self) -> Dict:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "value": round(self.value, 4),
            "timestamp": self.timestamp,
            "category": self.category,
        }


@dataclass
class EncodedMacroState:
    state_id: str
    timestamp: float
    latent_vector: List[float] = field(default_factory=list)
    reconstruction_error: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "state_id": self.state_id,
            "timestamp": self.timestamp,
            "latent_vector": [round(x, 4) for x in self.latent_vector],
            "reconstruction_error": round(self.reconstruction_error, 6),
        }


class QuantAutoencoderMacro:
    """Autoencoder-inspired nonlinear dimensionality reduction for macroeconomic features."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "quant_ae"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.features: List[MacroFeature] = []
        self.encoded_states: List[EncodedMacroState] = []
        self.weights: Dict[str, List[List[float]]] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for f in data.get("features", []):
                    self.features.append(MacroFeature(**f))
                for s in data.get("encoded_states", []):
                    self.encoded_states.append(EncodedMacroState(**s))
                self.weights = data.get("weights", {})
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "features": [f.to_dict() for f in self.features[-1000:]],
            "encoded_states": [s.to_dict() for s in self.encoded_states[-500:]],
            "weights": self.weights,
        }
        state_file.write_text(json.dumps(state, indent=2))

    def _sigmoid(self, x: float) -> float:
        return 1.0 / (1.0 + math.exp(-max(-50, min(50, x))))

    def _mat_vec_mul(self, matrix: List[List[float]], vec: List[float]) -> List[float]:
        return [sum(matrix[i][j] * vec[j] for j in range(len(vec))) for i in range(len(matrix))]

    def _init_weights(self, input_dim: int, latent_dim: int = 3) -> None:
        """Initialize encoder/decoder weights with random values."""
        import random
        random.seed(42)
        # Encoder: input_dim -> latent_dim
        encoder = [[random.uniform(-0.5, 0.5) for _ in range(input_dim)] for _ in range(latent_dim)]
        # Decoder: latent_dim -> input_dim
        decoder = [[random.uniform(-0.5, 0.5) for _ in range(latent_dim)] for _ in range(input_dim)]
        self.weights = {"encoder": encoder, "decoder": decoder, "latent_dim": latent_dim}

    def encode(self, feature_values: List[float], timestamp: float = 0.0) -> EncodedMacroState:
        """Encode macro features into latent space."""
        if not self.weights:
            self._init_weights(len(feature_values))
        encoder = self.weights["encoder"]
        latent = self._mat_vec_mul(encoder, feature_values)
        latent = [self._sigmoid(x) for x in latent]

        decoder = self.weights["decoder"]
        reconstructed = self._mat_vec_mul(decoder, latent)
        reconstructed = [self._sigmoid(x) for x in reconstructed]

        error = math.sqrt(sum((feature_values[i] - reconstructed[i]) ** 2 for i in range(len(feature_values)))) / max(1, len(feature_values))

        state = EncodedMacroState(
            state_id=f"ae_{int(time.time() * 1000)}",
            timestamp=timestamp,
            latent_vector=[round(x, 4) for x in latent],
            reconstruction_error=round(error, 6),
        )
        self.encoded_states.append(state)
        self._save_state()
        return state

    def decode(self, latent_vector: List[float]) -> List[float]:
        """Decode latent vector back to feature space."""
        if not self.weights:
            return []
        decoder = self.weights["decoder"]
        output = self._mat_vec_mul(decoder, latent_vector)
        return [self._sigmoid(x) for x in output]

    def add_feature(self, name: str, value: float, category: str = "economic", timestamp: float = 0.0) -> MacroFeature:
        feature = MacroFeature(
            feature_id=f"feat_{name}_{int(time.time())}",
            name=name,
            value=value,
            timestamp=timestamp,
            category=category,
        )
        self.features.append(feature)
        self._save_state()
        return feature

    def get_feature_history(self, name: str) -> List[MacroFeature]:
        return [f for f in self.features if f.name == name]

    def get_stats(self) -> Dict:
        avg_error = sum(s.reconstruction_error for s in self.encoded_states) / max(1, len(self.encoded_states))
        categories = {}
        for f in self.features:
            categories[f.category] = categories.get(f.category, 0) + 1
        return {
            "features_total": len(self.features),
            "encoded_states": len(self.encoded_states),
            "avg_reconstruction_error": round(avg_error, 6),
            "latent_dim": self.weights.get("latent_dim", 0),
            "categories": categories,
        }

    def to_dict(self) -> Dict:
        return {
            "features": [f.to_dict() for f in self.features[-100:]],
            "encoded_states": [s.to_dict() for s in self.encoded_states[-50:]],
            "stats": self.get_stats(),
        }


__all__ = ["QuantAutoencoderMacro", "MacroFeature", "EncodedMacroState"]
