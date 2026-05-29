# core/game.py

import time

from core.scene import Scene
from core.scene_manager import SceneManager


__all__ = ["Game"]

MAX_DT = 0.1


class Game:
    def __init__(self, target_fps: int = 30) -> None:
        self.scene_manager = SceneManager()
        self.target_fps = target_fps
        self._running = False

    def run(self) -> None:
        self._running = True
        dt = 1.0 / self.target_fps

        while self._running:
            frame_start = time.perf_counter()

            self.scene_manager.update(min(dt, MAX_DT))
            self.scene_manager.draw()

            if self.scene_manager.is_empty:
                self._running = False
                break

            elapsed = time.perf_counter() - frame_start
            budget = 1.0 / self.target_fps - elapsed
            if budget > 0:
                time.sleep(budget)

            dt = time.perf_counter() - frame_start

    def stop(self) -> None:
        self._running = False

    def push_scene(self, scene: Scene) -> None:
        self.scene_manager.push(scene)