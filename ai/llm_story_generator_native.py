"""LLM Story Generator — Native Python (stdlib only)."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class StoryGenre(Enum):
    FANTASY = auto()
    SCIENCE_FICTION = auto()
    MYSTERY = auto()
    ROMANCE = auto()
    HORROR = auto()
    ADVENTURE = auto()

@dataclass
class StoryBeat:
    id: str
    scene: str
    characters: List[str] = field(default_factory=list)
    conflict: str = ""
    resolution: str = ""

class StoryGenerator:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._templates: Dict[StoryGenre, List[str]] = {
            StoryGenre.FANTASY: ["In a realm of {setting}, {hero} discovered {artifact}.", "The {creature} guarded {location} for centuries.", "Magic flowed through {hero} as they faced {villain}."],
            StoryGenre.SCIENCE_FICTION: ["The colony on {planet} received a strange signal.", "{hero} piloted the {ship} into the unknown.", "The AI known as {name} questioned its own existence."],
            StoryGenre.MYSTERY: ["The case of the missing {item} baffled {hero}.", "A shadow moved through {location} at midnight.", "The clue was hidden in the {object} all along."]
        }
        self._settings: Dict[str, List[str]] = {
            "setting": ["shadows", "light", "crystal mountains", "eternal forests"],
            "hero": ["Aria", "Kael", "Luna", "Orion"],
            "artifact": ["the Crystal Orb", "the Ancient Tome", "the Star Blade"],
            "creature": ["dragon", "phoenix", "griffin", "serpent"],
            "location": ["the Tower", "the Abyss", "the Citadel"],
            "villain": ["the Dark Lord", "the Shadow King", "the Void Walker"],
            "planet": ["Mars-7", "Kepler-9", "Proxima-b"],
            "ship": ["Nebula", "Starfire", "Voyager-X"],
            "name": ["Eve", "Hal", "Neo", "Aria"],
            "item": ["necklace", "painting", "manuscript"],
            "object": ["clock", "mirror", "diary"]
        }

    def generate_story(self, genre: StoryGenre, beats: int = 3) -> str:
        templates = self._templates.get(genre, self._templates[StoryGenre.FANTASY])
        scenes = []
        for _ in range(beats):
            template = self._rng.choice(templates)
            scene = template
            for key, values in self._settings.items():
                if "{" + key + "}" in scene:
                    scene = scene.replace("{" + key + "}", self._rng.choice(values))
            scenes.append(scene)
        return " ".join(scenes)

    def generate_characters(self, count: int = 2) -> List[str]:
        return self._rng.sample(self._settings["hero"], min(count, len(self._settings["hero"])))

    def get_stats(self) -> Dict[str, Any]:
        return {"genres": len(self._templates), "settings": len(self._settings)}

def run() -> None:
    print("Story Generator test")
    e = StoryGenerator(seed=42)
    print("  Fantasy: " + e.generate_story(StoryGenre.FANTASY, 2))
    print("  Sci-Fi: " + e.generate_story(StoryGenre.SCIENCE_FICTION, 2))
    print("  Mystery: " + e.generate_story(StoryGenre.MYSTERY, 2))
    print("  Characters: " + str(e.generate_characters(3)))
    print("  Stats: " + str(e.get_stats()))
    print("Story Generator test complete.")

if __name__ == "__main__":
    run()
