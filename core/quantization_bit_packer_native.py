"""Bit Packer — 4/8-bit packing, LUT dequantization."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class PackedTensor:
    name: str = ""
    bits: int = 4
    packed_data: list[int] = None
    scale: float = 1.0
    zero_point: float = 0.0
    shape: list[int] = None

    def __post_init__(self):
        if self.packed_data is None:
            self.packed_data = []
        if self.shape is None:
            self.shape = []

class QuantizationBitPacker:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._tensors: list[PackedTensor] = []
        self._persist_path = self.root / "bit_packer.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._tensors = [PackedTensor(**t) for t in data.get("tensors", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "tensors": [t.__dict__ for t in self._tensors]
        }, indent=2))

    def pack_4bit(self, weights: list[float], name: str, scale: float, zp: float) -> PackedTensor:
        # Quantize to 4-bit (0-15), then pack 2 values per byte
        quant = [max(0, min(15, int(round((w - zp) / scale)))) for w in weights]
        packed = []
        for i in range(0, len(quant), 2):
            low = quant[i]
            high = quant[i+1] if i+1 < len(quant) else 0
            packed.append((high << 4) | low)
        tensor = PackedTensor(name=name, bits=4, packed_data=packed, scale=scale, zero_point=zp, shape=[len(weights)])
        self._tensors.append(tensor)
        self._save()
        return tensor

    def pack_8bit(self, weights: list[float], name: str, scale: float, zp: float) -> PackedTensor:
        quant = [max(0, min(255, int(round((w - zp) / scale)))) for w in weights]
        tensor = PackedTensor(name=name, bits=8, packed_data=quant, scale=scale, zero_point=zp, shape=[len(weights)])
        self._tensors.append(tensor)
        self._save()
        return tensor

    def unpack(self, tensor: PackedTensor) -> list[float]:
        if tensor.bits == 8:
            return [q * tensor.scale + tensor.zero_point for q in tensor.packed_data]
        elif tensor.bits == 4:
            unpacked = []
            for byte in tensor.packed_data:
                unpacked.append((byte & 0x0F) * tensor.scale + tensor.zero_point)
                unpacked.append(((byte >> 4) & 0x0F) * tensor.scale + tensor.zero_point)
            return unpacked[:tensor.shape[0]] if tensor.shape else unpacked
        return []

    def to_dict(self) -> dict:
        return {"tensor_count": len(self._tensors), "bits": list(set(t.bits for t in self._tensors))}

    def get_stats(self) -> dict:
        return {"tensors": len(self._tensors), "total_packed_bytes": sum(len(t.packed_data) for t in self._tensors)}

__all__ = ["QuantizationBitPacker", "PackedTensor"]
