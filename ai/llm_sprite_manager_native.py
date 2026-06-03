"""LLM Sprite Manager — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

@dataclass
class Sprite:
    id: str
    x: float
    y: float
    width: float
    height: float
    visible: bool = True
    z_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class SpriteManager:
    def __init__(self) -> None:
        self._sprites: Dict[str, Sprite] = {}

    def add(self, sprite: Sprite) -> None:
        self._sprites[sprite.id] = sprite

    def remove(self, sprite_id: str) -> bool:
        return self._sprites.pop(sprite_id, None) is not None

    def get(self, sprite_id: str) -> Optional[Sprite]:
        return self._sprites.get(sprite_id)

    def move(self, sprite_id: str, dx: float, dy: float) -> bool:
        sprite = self._sprites.get(sprite_id)
        if sprite:
            sprite.x += dx
            sprite.y += dy
            return True
        return False

    def set_position(self, sprite_id: str, x: float, y: float) -> bool:
        sprite = self._sprites.get(sprite_id)
        if sprite:
            sprite.x = x
            sprite.y = y
            return True
        return False

    def get_visible(self) -> List[Sprite]:
        return sorted([s for s in self._sprites.values() if s.visible], key=lambda s: s.z_index)

    def get_at_position(self, x: float, y: float) -> List[Sprite]:
        return [s for s in self._sprites.values() if s.visible and s.x <= x <= s.x + s.width and s.y <= y <= s.y + s.height]

    def get_stats(self) -> Dict[str, Any]:
        return {"total": len(self._sprites), "visible": sum(1 for s in self._sprites.values() if s.visible)}

def run() -> None:
    print("Sprite Manager test")
    e = SpriteManager()
    e.add(Sprite("player", 10, 20, 32, 32, z_index=10))
    e.add(Sprite("enemy1", 100, 50, 32, 32, z_index=5))
    e.add(Sprite("bg", 0, 0, 800, 600, z_index=0))
    e.move("player", 5, 5)
    print("  Player pos: (" + str(e.get("player").x) + ", " + str(e.get("player").y) + ")")
    print("  At (15, 25): " + str([s.id for s in e.get_at_position(15, 25)]))
    print("  Stats: " + str(e.get_stats()))
    print("Sprite Manager test complete.")

if __name__ == "__main__":
    run()
