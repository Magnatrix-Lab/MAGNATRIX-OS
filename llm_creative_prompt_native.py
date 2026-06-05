"""Creative Prompt Generator — randomization, constraints, variation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random

@dataclass
class CreativePrompt:
    subjects: List[str] = field(default_factory=lambda: ["dragon", "robot", "forest", "city", "ocean"])
    styles: List[str] = field(default_factory=lambda: ["surreal", "realistic", "abstract", "minimalist", "cyberpunk"])
    mediums: List[str] = field(default_factory=lambda: ["oil painting", "digital art", "photograph", "sketch", "3D render"])
    moods: List[str] = field(default_factory=lambda: ["mysterious", "joyful", "melancholic", "epic", "peaceful"])
    colors: List[str] = field(default_factory=lambda: ["warm tones", "cool tones", "monochrome", "vibrant", "pastel"])

    def generate(self, constraints: Dict[str, str] = None) -> str:
        c = constraints or {}
        subject = c.get("subject", random.choice(self.subjects))
        style = c.get("style", random.choice(self.styles))
        medium = c.get("medium", random.choice(self.mediums))
        mood = c.get("mood", random.choice(self.moods))
        color = c.get("color", random.choice(self.colors))
        return f"A {style} {medium} of a {subject}, evoking a {mood} atmosphere with {color}."

    def variations(self, base: str, n: int = 3) -> List[str]:
        results = [base]
        for _ in range(n - 1):
            words = base.split()
            if words:
                idx = random.randint(0, len(words) - 1)
                words[idx] = random.choice(self.subjects + self.styles + self.mediums)
                results.append(' '.join(words))
        return results

    def constrain(self, prompt: str, must_include: List[str]) -> str:
        for word in must_include:
            if word.lower() not in prompt.lower():
                prompt += f" including {word}."
        return prompt

    def stats(self) -> Dict:
        total = len(self.subjects) * len(self.styles) * len(self.mediums) * len(self.moods) * len(self.colors)
        return {"combinations": total}

def run():
    cp = CreativePrompt()
    print(cp.generate())
    print("Variations:", cp.variations(cp.generate(), 3))
    print(cp.stats())

if __name__ == "__main__":
    run()
