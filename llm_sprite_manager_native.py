"""Sprite Manager — animation, frames, batching, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import time

@dataclass
class Sprite:
    sprite_id: str
    x: float = 0.0
    y: float = 0.0
    width: float = 32.0
    height: float = 32.0
    visible: bool = True
    opacity: float = 1.0

@dataclass
class Animation:
    anim_id: str
    frames: List[Tuple[int, int, int, int]]  # frame rects
    duration: float
    loop: bool = True

class SpriteManager:
    def __init__(self, max_sprites: int = 1000):
        self.max_sprites = max_sprites
        self.sprites: Dict[str, Sprite] = {}
        self.animations: Dict[str, Animation] = {}
        self.active_anims: Dict[str, Dict] = {}  # sprite_id -> {anim_id, start_time, frame_idx}

    def add_sprite(self, sprite: Sprite):
        self.sprites[sprite.sprite_id] = sprite

    def remove_sprite(self, sprite_id: str):
        self.sprites.pop(sprite_id, None)
        self.active_anims.pop(sprite_id, None)

    def move(self, sprite_id: str, dx: float, dy: float):
        s = self.sprites.get(sprite_id)
        if s:
            s.x += dx
            s.y += dy

    def play_animation(self, sprite_id: str, anim_id: str):
        if anim_id in self.animations and sprite_id in self.sprites:
            self.active_anims[sprite_id] = {"anim_id": anim_id, "start": time.time(), "frame": 0}

    def update(self, dt: float):
        now = time.time()
        for sprite_id, anim_data in list(self.active_anims.items()):
            anim = self.animations.get(anim_data["anim_id"])
            if not anim:
                continue
            elapsed = now - anim_data["start"]
            frame_idx = int((elapsed / anim.duration) * len(anim.frames))
            if frame_idx >= len(anim.frames):
                if anim.loop:
                    anim_data["start"] = now
                    frame_idx = 0
                else:
                    self.active_anims.pop(sprite_id, None)
                    continue
            anim_data["frame"] = frame_idx

    def get_visible(self) -> List[Sprite]:
        return [s for s in self.sprites.values() if s.visible]

    def stats(self) -> Dict:
        return {"sprites": len(self.sprites), "animations": len(self.animations), "active_anims": len(self.active_anims)}

def run():
    mgr = SpriteManager()
    s = Sprite("hero", 100, 100, 32, 32)
    mgr.add_sprite(s)
    mgr.add_sprite(Sprite("enemy", 200, 200, 32, 32))
    mgr.move("hero", 5, -3)
    print(mgr.sprites["hero"])
    print(mgr.stats())

if __name__ == "__main__":
    run()
