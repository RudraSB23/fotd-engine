from typing import Optional

from textual.screen import Screen

from core.scene import Scene


__all__ = ["SceneManager"]


class SceneManager:
    def push_scene(self, scene: Scene) -> None:
        self.push_screen(scene)

    def pop_scene(self) -> None:
        self.pop_screen()
        screen = self.screen
        if hasattr(screen, "on_resume"):
            screen.on_resume()

    def replace_scene(self, scene: Scene) -> None:
        self.switch_screen(scene)

    @property
    def current_scene(self) -> Optional[Screen]:
        return self.screen

    @property
    def is_empty(self) -> bool:
        return len(self.screen_stack) == 0