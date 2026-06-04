"""Game Loop Engine — update, render, fixed timestep, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum, auto
import time

class GameLoop:
    def __init__(self, target_fps: int = 60, fixed_dt: float = 0.016):
        self.target_fps = target_fps
        self.fixed_dt = fixed_dt
        self.running = False
        self.update_handlers: List[Callable] = []
        self.render_handlers: List[Callable] = []
        self.frame_count = 0
        self.elapsed_time = 0.0
        self.accumulator = 0.0
        self.current_time = 0.0

    def on_update(self, handler: Callable):
        self.update_handlers.append(handler)

    def on_render(self, handler: Callable):
        self.render_handlers.append(handler)

    def run(self, max_frames: int = 100):
        self.running = True
        self.current_time = time.time()
        while self.running and self.frame_count < max_frames:
            new_time = time.time()
            frame_time = new_time - self.current_time
            self.current_time = new_time
            self.accumulator += frame_time
            while self.accumulator >= self.fixed_dt:
                for h in self.update_handlers:
                    h(self.fixed_dt)
                self.accumulator -= self.fixed_dt
            alpha = self.accumulator / self.fixed_dt
            for h in self.render_handlers:
                h(alpha)
            self.frame_count += 1
            self.elapsed_time += frame_time
            sleep_time = max(0, 1.0 / self.target_fps - frame_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
        self.running = False

    def stop(self):
        self.running = False

    def stats(self) -> Dict:
        return {"frames": self.frame_count, "elapsed": self.elapsed_time, "fps": self.frame_count / self.elapsed_time if self.elapsed_time > 0 else 0}

def run():
    loop = GameLoop(60, 0.016)
    def update(dt):
        pass
    def render(alpha):
        pass
    loop.on_update(update)
    loop.on_render(render)
    loop.run(10)
    print(loop.stats())

if __name__ == "__main__":
    run()
