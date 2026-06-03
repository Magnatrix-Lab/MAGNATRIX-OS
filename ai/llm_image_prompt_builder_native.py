"""LLM Image Prompt Builder — Native Python (stdlib only)."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class ArtStyle(Enum):
    REALISTIC = auto()
    ANIME = auto()
    OIL_PAINTING = auto()
    WATERCOLOR = auto()
    DIGITAL_ART = auto()
    SKETCH = auto()

class ImagePromptBuilder:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._subjects = ["a mountain landscape", "a futuristic city", "a mystical forest", "an ancient temple", "a cosmic nebula"]
        self._styles = ["realistic", "anime style", "oil painting", "watercolor", "digital art", "pencil sketch"]
        self._lighting = ["golden hour", "moonlight", "neon lights", "soft ambient", "dramatic shadows"]
        self._moods = ["serene", "epic", "mysterious", "whimsical", "dark"]
        self._details = ["highly detailed", "8k resolution", "intricate patterns", "vivid colors", "atmospheric"]

    def build_prompt(self, subject: Optional[str] = None, style: Optional[ArtStyle] = None, include_details: bool = True) -> str:
        parts = []
        parts.append(subject or self._rng.choice(self._subjects))
        if style:
            parts.append("in " + self._styles[style.value - 1] + " style")
        else:
            parts.append("in " + self._rng.choice(self._styles) + " style")
        parts.append(self._rng.choice(self._lighting) + " lighting")
        parts.append(self._rng.choice(self._moods) + " mood")
        if include_details:
            parts.append(self._rng.choice(self._details))
        return ", ".join(parts)

    def build_negative_prompt(self) -> str:
        negatives = ["blurry", "low quality", "deformed", "extra limbs", "bad anatomy", "watermark", "text"]
        return ", ".join(self._rng.sample(negatives, 4))

    def build_variations(self, base_prompt: str, count: int = 3) -> List[str]:
        variations = []
        for _ in range(count):
            variation = base_prompt + ", " + self._rng.choice(self._details)
            variations.append(variation)
        return variations

    def get_stats(self) -> Dict[str, Any]:
        return {"subjects": len(self._subjects), "styles": len(self._styles), "lighting": len(self._lighting)}

def run() -> None:
    print("Image Prompt Builder test")
    e = ImagePromptBuilder(seed=42)
    print("  Prompt: " + e.build_prompt())
    print("  Styled: " + e.build_prompt("a dragon", ArtStyle.OIL_PAINTING))
    print("  Negative: " + e.build_negative_prompt())
    print("  Variations: " + str(len(e.build_variations("a castle", 3))))
    print("  Stats: " + str(e.get_stats()))
    print("Image Prompt Builder test complete.")

if __name__ == "__main__":
    run()
