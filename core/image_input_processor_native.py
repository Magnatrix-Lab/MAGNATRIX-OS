"""
image_input_processor_native.py
MAGNATRIX-OS — Image Input Processor

Inspired by gajae-code: Process image input for agent vision. Pure stdlib.
"""

import json
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ImageInput:
    input_id: str
    image_path: str
    description: str
    base64_data: str
    mime_type: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ImageInputProcessor:
    """Process image input for agent vision tasks."""

    def __init__(self, cache_dir: str = "./image_inputs"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.inputs: Dict[str, ImageInput] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "inputs.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for iid, idata in data.items():
                        self.inputs[iid] = ImageInput(**idata)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "inputs.json", "w", encoding="utf-8") as f:
            json.dump({iid: asdict(i) for iid, i in self.inputs.items()}, f, indent=2)

    def load_image(self, input_id: str, image_path: str, description: str = "") -> ImageInput:
        try:
            with open(image_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            mime = "image/png" if image_path.endswith(".png") else "image/jpeg" if image_path.endswith((".jpg", ".jpeg")) else "image/webp"
        except Exception:
            data = ""
            mime = "unknown"
        inp = ImageInput(
            input_id=input_id, image_path=image_path, description=description,
            base64_data=data, mime_type=mime,
        )
        self.inputs[input_id] = inp
        self._save()
        return inp

    def get_input(self, input_id: str) -> Optional[ImageInput]:
        return self.inputs.get(input_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.inputs)
        total_size = sum(len(i.base64_data) for i in self.inputs.values())
        return {"total_images": total, "total_base64_size": total_size}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ImageInputProcessor", "ImageInput"]