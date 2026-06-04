"""Story Builder - Structured narrative generation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto
import random

class StoryBeat(Enum):
    SETUP = auto(); CONFLICT = auto(); RISING = auto(); CLIMAX = auto(); RESOLUTION = auto()

@dataclass
class StoryBuilder:
    beats: Dict[StoryBeat, List[str]] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.beats:
            self.beats = {
                StoryBeat.SETUP: ["Once upon a time...", "In a distant land...", "Long ago..."],
                StoryBeat.CONFLICT: ["But then trouble came...", "Suddenly, everything changed...", "A problem appeared..."],
                StoryBeat.RISING: ["Things got worse...", "The challenge grew...", "Danger mounted..."],
                StoryBeat.CLIMAX: ["In the final moment...", "At the peak of danger...", "The decisive battle came..."],
                StoryBeat.RESOLUTION: ["And everything was fine.", "They lived happily ever after.", "Peace returned."]
            }
    
    def generate(self) -> str:
        story = []
        for beat in [StoryBeat.SETUP, StoryBeat.CONFLICT, StoryBeat.RISING, StoryBeat.CLIMAX, StoryBeat.RESOLUTION]:
            story.append(random.choice(self.beats.get(beat, [""])))
        return " ".join(story)
    
    def stats(self) -> dict:
        return {"beats": len(self.beats), "total_templates": sum(len(v) for v in self.beats.values())}

def run():
    sb = StoryBuilder()
    print("Story:", sb.generate())
    print("Stats:", sb.stats())

if __name__ == "__main__": run()
