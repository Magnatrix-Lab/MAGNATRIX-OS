"""Muse Generator — random combinations, constraints, themes, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random

@dataclass
class MuseGenerator:
    themes: List[str] = field(default_factory=lambda: ["love", "death", "nature", "technology", "identity", "time"])
    forms: List[str] = field(default_factory=lambda: ["poem", "story", "song", "painting", "film", "sculpture"])
    emotions: List[str] = field(default_factory=lambda: ["joy", "sorrow", "awe", "anger", "fear", "hope"])
    settings: List[str] = field(default_factory=lambda: ["future", "past", "dream", "underwater", "space", "urban"])
    conflicts: List[str] = field(default_factory=lambda: ["man vs nature", "man vs self", "man vs society", "man vs technology"])

    def inspire(self, fixed: Dict[str, str] = None) -> Dict:
        f = fixed or {}
        return {
            "theme": f.get("theme", random.choice(self.themes)),
            "form": f.get("form", random.choice(self.forms)),
            "emotion": f.get("emotion", random.choice(self.emotions)),
            "setting": f.get("setting", random.choice(self.settings)),
            "conflict": f.get("conflict", random.choice(self.conflicts))
        }

    def narrative_prompt(self, inspiration: Dict) -> str:
        return f"Create a {inspiration['form']} about {inspiration['theme']} set in a {inspiration['setting']} world, exploring {inspiration['conflict']} with a tone of {inspiration['emotion']}."

    def random_mashup(self, n: int = 2) -> List[str]:
        return random.sample(self.themes, min(n, len(self.themes)))

    def what_if(self, base: str) -> str:
        twists = ["but in reverse", "from the villain's perspective", "without dialogue", "in complete silence", "as a comedy", "as a tragedy"]
        return f"{base} {random.choice(twists)}"

    def stats(self) -> Dict:
        total = len(self.themes) * len(self.forms) * len(self.emotions) * len(self.settings) * len(self.conflicts)
        return {"combinations": total}

def run():
    mg = MuseGenerator()
    insp = mg.inspire()
    print(insp)
    print(mg.narrative_prompt(insp))
    print("What if:", mg.what_if(mg.narrative_prompt(insp)))
    print(mg.stats())

if __name__ == "__main__":
    run()
