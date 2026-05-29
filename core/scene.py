# core/scene.py

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.scene_manager import SceneManager


__all__ = ["Scene"]


class Scene(ABC):
    def __init__(self, manager: "SceneManager") -> None:
        self.manager = manager

    @abstractmethod
    def on_enter(self) -> None:
        ...

    @abstractmethod
    def on_exit(self) -> None:
        ...

    @abstractmethod
    def update(self, dt: float) -> None:
        ...

    @abstractmethod
    def draw(self) -> None:
        ...

    def on_resume(self) -> None:
        pass