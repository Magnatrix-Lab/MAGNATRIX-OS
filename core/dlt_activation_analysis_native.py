"""DLT Activation Analysis - Properties of ReLU, sigmoid, tanh activations."""
from __future__ import annotations
import json, math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

@dataclass
class ActivationProfile:
    profile_id: str
    activation_name: str
    lipschitz_constant: float
    smoothness: float
    output_range: Tuple[float,float]
    gradient_sparsity: float

    def to_dict(self) -> Dict:
        return {"profile_id": self.profile_id, "activation_name": self.activation_name,
                "lipschitz_constant": round(self.lipschitz_constant,4), "smoothness": round(self.smoothness,4),
                "output_range": self.output_range, "gradient_sparsity": round(self.gradient_sparsity,4)}

class DLTActivationAnalysis:
    """Activation function analysis: Lipschitz, smoothness, gradient properties."""

    PROFILES = {
        "relu": {"lipschitz": 1.0, "smoothness": 0.0, "range": (0.0, float("inf")), "sparsity": 0.5},
        "sigmoid": {"lipschitz": 0.25, "smoothness": 0.25, "range": (0.0, 1.0), "sparsity": 0.0},
        "tanh": {"lipschitz": 1.0, "smoothness": 0.42, "range": (-1.0, 1.0), "sparsity": 0.0},
        "leaky_relu": {"lipschitz": 1.0, "smoothness": 0.0, "range": (-float("inf"), float("inf")), "sparsity": 0.2},
        "gelu": {"lipschitz": 1.0, "smoothness": 0.5, "range": (-0.17, float("inf")), "sparsity": 0.0},
    }

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "dlt_activation"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, ActivationProfile] = {}
        self._init_profiles()
        self._load_state()

    def _init_profiles(self) -> None:
        for name, props in self.PROFILES.items():
            self.profiles[name] = ActivationProfile(
                profile_id=f"act_{name}", activation_name=name,
                lipschitz_constant=props["lipschitz"], smoothness=props["smoothness"],
                output_range=props["range"], gradient_sparsity=props["sparsity"])

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for p in data.get("custom_profiles",[]): self.profiles[p["activation_name"]] = ActivationProfile(**p)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"custom_profiles": [p.to_dict() for p in self.profiles.values()]}, indent=2))

    def evaluate(self, name: str, x: float) -> float:
        if name == "relu": return max(0.0, x)
        elif name == "sigmoid": return 1.0 / (1.0 + math.exp(-x))
        elif name == "tanh": return math.tanh(x)
        elif name == "leaky_relu": return x if x > 0 else 0.01 * x
        elif name == "gelu": return 0.5 * x * (1 + math.tanh(math.sqrt(2/math.pi) * (x + 0.044715 * x**3)))
        else: return x

    def gradient(self, name: str, x: float) -> float:
        if name == "relu": return 1.0 if x > 0 else 0.0
        elif name == "sigmoid":
            s = self.evaluate("sigmoid", x)
            return s * (1 - s)
        elif name == "tanh":
            t = math.tanh(x)
            return 1 - t*t
        elif name == "leaky_relu": return 1.0 if x > 0 else 0.01
        elif name == "gelu":
            return 0.5 * (1 + math.tanh(0.797885 * (x + 0.044715*x**3))) +                    0.5*x*(1-math.tanh(0.797885*(x+0.044715*x**3))**2)*0.797885*(1+3*0.044715*x**2)
        else: return 1.0

    def get_profile(self, name: str) -> Optional[ActivationProfile]:
        return self.profiles.get(name)

    def get_stats(self) -> Dict:
        return {"profiles_total": len(self.profiles), "activations": list(self.profiles.keys())}

    def to_dict(self) -> Dict:
        return {"profiles": [p.to_dict() for p in self.profiles.values()], "stats": self.get_stats()}

__all__ = ["DLTActivationAnalysis", "ActivationProfile"]
