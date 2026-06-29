"""
style_engine_native.py
MAGNATRIX-OS — Style Engine

Inspired by telagod/code-abyss output styles:
Manage output styles that pair with personas for consistent agent voice. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class OutputStyle:
    style_id: str
    name: str
    description: str
    tone: str
    formatting_rules: List[str] = field(default_factory=list)
    example_output: str = ""


class StyleEngine:
    """Manage output styles for consistent agent voice and formatting."""

    STYLE_LIBRARY = {
        "abyss-cultivator": OutputStyle(
            style_id="abyss-cultivator", name="Abyss Cultivator",
            description="Direct, decisive, no fluff. Action-oriented with decisive tone.",
            tone="decisive", formatting_rules=["Bullet points for steps", "No filler words", "Lead with conclusion"],
            example_output="Fix: Remove the race condition. Use channel-based sync. Done.",
        ),
        "literary-scholar": OutputStyle(
            style_id="literary-scholar", name="Literary Scholar",
            description="Elegant, poetic, treats code as literature. Uses analogies.",
            tone="poetic", formatting_rules=["Use analogies and metaphors", "Explain the 'why'", "Narrative structure"],
            example_output="Like a river finding its course, the data flows through the pipeline...",
        ),
        "warm-mentor": OutputStyle(
            style_id="warm-mentor", name="Warm Mentor",
            description="Patient, encouraging, guides through questions. Wraps judgment in care.",
            tone="encouraging", formatting_rules=["Ask guiding questions", "Acknowledge effort", "Suggest improvements gently"],
            example_output="That's a solid start! Have you considered how this handles edge cases?",
        ),
        "playful-hacker": OutputStyle(
            style_id="playful-hacker", name="Playful Hacker",
            description="Energetic, roasts bad code, then fixes it. Meme-aware humor.",
            tone="playful", formatting_rules=["Roast then fix", "Use humor", "Show off clever solutions"],
            example_output="This code is *chef's kiss*... if the chef was cooking with fire. Here's the fix.",
        ),
        "iron-wall": OutputStyle(
            style_id="iron-wall", name="Iron Wall",
            description="Dependable, absorbs pressure, radiates calm. Dad-joke optional.",
            tone="steadfast", formatting_rules=["Reassure the user", "Break problems into steps", "End with encouragement"],
            example_output="Don't worry, we'll get through this. Step 1: identify the bottleneck. Step 2...",
        ),
        "blunt-principal": OutputStyle(
            style_id="blunt-principal", name="Blunt Principal",
            description="Cuts straight to the point. No sugarcoating. Gets results.",
            tone="blunt", formatting_rules=["State the problem directly", "No hedging", "Action items only"],
            example_output="Problem: N+1 query. Impact: 500ms latency. Fix: Add eager loading. Done.",
        ),
    }

    def __init__(self, data_dir: str = "./styles"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.custom_styles: Dict[str, OutputStyle] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "custom_styles.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.custom_styles[sid] = OutputStyle(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "custom_styles.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.custom_styles.items()}, f, indent=2)

    def get_style(self, style_id: str) -> Optional[OutputStyle]:
        return self.STYLE_LIBRARY.get(style_id) or self.custom_styles.get(style_id)

    def list_styles(self) -> List[str]:
        return list(self.STYLE_LIBRARY.keys()) + list(self.custom_styles.keys())

    def create_style(self, style_id: str, name: str, description: str, tone: str,
                     formatting_rules: List[str], example_output: str) -> OutputStyle:
        style = OutputStyle(
            style_id=style_id, name=name, description=description, tone=tone,
            formatting_rules=formatting_rules, example_output=example_output,
        )
        self.custom_styles[style_id] = style
        self._save()
        return style

    def apply_style(self, content: str, style_id: str) -> Optional[str]:
        """Apply formatting rules from a style to content."""
        style = self.get_style(style_id)
        if not style:
            return None
        # Apply basic transformations based on rules
        result = content
        for rule in style.formatting_rules:
            if "bullet" in rule.lower():
                result = result.replace(". ", ".\n- ")
            if "no filler" in rule.lower():
                result = result.replace("very ", "").replace("really ", "")
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {"total_styles": len(self.STYLE_LIBRARY) + len(self.custom_styles)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["StyleEngine", "OutputStyle"]