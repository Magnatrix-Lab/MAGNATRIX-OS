"""Model Exporter — Quantized model serialization, compatibility."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class ExportedModel:
    name: str = ""
    format: str = ""  # gguf | onnx | json
    version: str = "1.0"
    tensor_count: int = 0
    quantized: bool = False
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class QuantizationModelExporter:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._exports: list[ExportedModel] = []
        self._persist_path = self.root / "model_exports.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._exports = [ExportedModel(**e) for e in data.get("exports", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "exports": [e.__dict__ for e in self._exports]
        }, indent=2))

    def export_gguf(self, name: str, tensors: list[dict], metadata: dict) -> ExportedModel:
        model = ExportedModel(name=name, format="gguf", tensor_count=len(tensors), quantized=True, metadata=metadata)
        self._exports.append(model)
        self._save()
        return model

    def export_json(self, name: str, model_dict: dict) -> ExportedModel:
        model = ExportedModel(name=name, format="json", tensor_count=len(model_dict.get("tensors", [])), quantized=model_dict.get("quantized", False), metadata=model_dict.get("metadata", {}))
        self._exports.append(model)
        self._save()
        return model

    def check_compatibility(self, model: ExportedModel, target_runtime: str) -> bool:
        compat = {
            "gguf": ["llama.cpp", "koboldcpp", "tabbyapi"],
            "onnx": ["onnxruntime", "onnxruntime-gpu"],
            "json": ["magnatrix-os", "custom"]
        }
        return target_runtime in compat.get(model.format, [])

    def list_exports(self) -> list[ExportedModel]:
        return self._exports

    def get_export(self, name: str) -> ExportedModel | None:
        for e in self._exports:
            if e.name == name:
                return e
        return None

    def to_dict(self) -> dict:
        return {"export_count": len(self._exports), "formats": list(set(e.format for e in self._exports))}

    def get_stats(self) -> dict:
        return {"exports": len(self._exports), "quantized": sum(1 for e in self._exports if e.quantized), "by_format": {f: sum(1 for e in self._exports if e.format == f) for f in set(e.format for e in self._exports)}}

__all__ = ["QuantizationModelExporter", "ExportedModel"]
