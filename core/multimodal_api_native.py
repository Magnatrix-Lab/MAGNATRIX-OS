"""
multimodal_api_native.py
MAGNATRIX-OS — Multimodal API

Inspired by OmniRoute: Unified multimodal API for text, image, audio. Pure stdlib.
"""

import json
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class MultimodalInput:
    input_id: str
    text: str = ""
    image_data: str = ""  # base64 encoded
    audio_data: str = ""  # base64 encoded
    mime_type: str = "text/plain"


class MultimodalAPI:
    """Unified multimodal API abstraction for text, image, audio."""

    SUPPORTED_MODES = ["text", "image", "audio", "mixed"]

    def __init__(self, cache_dir: str = "./multimodal"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.inputs: Dict[str, MultimodalInput] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "inputs.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for iid, idata in data.items():
                        self.inputs[iid] = MultimodalInput(**idata)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "inputs.json", "w", encoding="utf-8") as f:
            json.dump({iid: asdict(i) for iid, i in self.inputs.items()}, f, indent=2)

    def encode_text(self, input_id: str, text: str) -> MultimodalInput:
        inp = MultimodalInput(input_id=input_id, text=text, mime_type="text/plain")
        self.inputs[input_id] = inp
        self._save()
        return inp

    def encode_image(self, input_id: str, image_path: str, text: str = "") -> MultimodalInput:
        try:
            with open(image_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            img_data = ""
        inp = MultimodalInput(input_id=input_id, text=text, image_data=img_data, mime_type="image/png")
        self.inputs[input_id] = inp
        self._save()
        return inp

    def encode_audio(self, input_id: str, audio_path: str, text: str = "") -> MultimodalInput:
        try:
            with open(audio_path, "rb") as f:
                aud_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            aud_data = ""
        inp = MultimodalInput(input_id=input_id, text=text, audio_data=aud_data, mime_type="audio/wav")
        self.inputs[input_id] = inp
        self._save()
        return inp

    def get_input(self, input_id: str) -> Optional[MultimodalInput]:
        return self.inputs.get(input_id)

    def get_stats(self) -> Dict[str, Any]:
        text_count = sum(1 for i in self.inputs.values() if i.mime_type == "text/plain")
        image_count = sum(1 for i in self.inputs.values() if i.image_data)
        audio_count = sum(1 for i in self.inputs.values() if i.audio_data)
        return {"total": len(self.inputs), "text": text_count, "image": image_count, "audio": audio_count}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MultimodalAPI", "MultimodalInput"]