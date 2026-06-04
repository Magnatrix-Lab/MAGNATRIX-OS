"""Response Generator - Response template engine for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import random

class ResponseType(Enum):
    INFORMATIVE = auto(); EMPATHETIC = auto(); DIRECTIVE = auto(); CASUAL = auto()

@dataclass
class ResponseGenerator:
    templates: Dict[ResponseType, List[str]] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.templates:
            self.templates = {
                ResponseType.INFORMATIVE: ["Here is what I found: {data}", "The answer is: {data}", "Based on my knowledge: {data}"],
                ResponseType.EMPATHETIC: ["I understand how you feel about {data}", "That must be difficult regarding {data}", "I hear you on {data}"],
                ResponseType.DIRECTIVE: ["Please try {data}", "You should consider {data}", "I recommend {data}"],
                ResponseType.CASUAL: ["Cool! {data}", "Nice! {data}", "Got it! {data}"]
            }
    
    def generate(self, response_type: ResponseType, data: str) -> str:
        templates = self.templates.get(response_type, ["{data}"])
        template = random.choice(templates)
        return template.replace("{data}", data)
    
    def stats(self) -> dict:
        return {"response_types": len(self.templates), "total_templates": sum(len(v) for v in self.templates.values())}

def run():
    rg = ResponseGenerator()
    for rt in [ResponseType.INFORMATIVE, ResponseType.CASUAL]:
        print(f"{rt.name}: {rg.generate(rt, 'test result')}")
    print("Stats:", rg.stats())

if __name__ == "__main__": run()
