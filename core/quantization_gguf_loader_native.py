"""GGUF Loader — GGUF format parser, tensor metadata."""
from dataclasses import dataclass
from pathlib import Path
import json, struct

@dataclass
class GGUFTensor:
    name: str = ""
    n_dims: int = 0
    dims: list[int] = None
    dtype: str = ""
    offset: int = 0
    size: int = 0

    def __post_init__(self):
        if self.dims is None:
            self.dims = []

class QuantizationGGUFLoader:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._header: dict = {}
        self._tensors: list[GGUFTensor] = []
        self._kv: dict[str, str | int | float] = {}
        self._persist_path = self.root / "gguf_loader.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._header = data.get("header", {})
            self._tensors = [GGUFTensor(**t) for t in data.get("tensors", [])]
            self._kv = data.get("kv", {})

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "header": self._header,
            "tensors": [t.__dict__ for t in self._tensors],
            "kv": self._kv
        }, indent=2))

    def parse_header(self, magic: int = 0x46554747, version: int = 3) -> dict:
        self._header = {"magic": magic, "version": version, "tensor_count": 0, "kv_count": 0}
        self._save()
        return self._header

    def add_kv(self, key: str, value: str | int | float) -> None:
        self._kv[key] = value
        self._header["kv_count"] = len(self._kv)
        self._save()

    def add_tensor(self, tensor: GGUFTensor) -> None:
        self._tensors.append(tensor)
        self._header["tensor_count"] = len(self._tensors)
        self._save()

    def get_tensor(self, name: str) -> GGUFTensor | None:
        for t in self._tensors:
            if t.name == name:
                return t
        return None

    def to_dict(self) -> dict:
        return {"header": self._header, "tensor_count": len(self._tensors), "kv_count": len(self._kv)}

    def get_stats(self) -> dict:
        return {"tensors": len(self._tensors), "kv_pairs": len(self._kv), "version": self._header.get("version", 0)}

__all__ = ["QuantizationGGUFLoader", "GGUFTensor"]
