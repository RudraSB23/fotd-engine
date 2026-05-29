# core/scene_manager.py

from typing import Optional

from core.scene import Scene


__all__ = ["SceneManager"]


class SceneManager:
    def __init__(self) -> None:
        self._stack: list[Scene] = []

    def push(self, scene: Scene) -> None:
        if self._stack:
            self._stack[-1].on_exit()
        self._stack.append(scene)
        scene.on_enter()

    def pop(self) -> None:
        if not self._stack:
            return
        self._stack[-1].on_exit()
        self._stack.pop()
        if self._stack:
            self._stack[-1].on_resume()

    def replace(self, scene: Scene) -> None:
        if self._stack:
            self._stack[-1].on_exit()
            self._stack.pop()
        self._stack.append(scene)
        scene.on_enter()

    def update(self, dt: float) -> None:
        if self._stack:
            self._stack[-1].update(dt)

    def draw(self) -> None:
        if self._stack:
            self._stack[-1].draw()

    @property
    def current(self) -> Optional[Scene]:
        return self._stack[-1] if self._stack else None

    @property
    def is_empty(self) -> bool:
        return not self._stack