import time

from textual.app import App

from core.audio import quit_audio
from core.scene import Tick
from core.scene_manager import SceneManager

__all__ = ["Game"]

MAX_DT = 0.1


class Game(SceneManager, App):
    def __init__(self, target_fps: int = 30) -> None:
        App.__init__(self)
        self._target_fps = target_fps
        self._last_time: float = 0.0

    def on_mount(self) -> None:
        self.set_interval(1 / self._target_fps, self._tick)

    def on_unmount(self) -> None:
        quit_audio()

    async def _tick(self) -> None:
        now = time.monotonic()
        if self._last_time == 0.0:
            dt = 1.0 / self._target_fps
        else:
            dt = min(now - self._last_time, MAX_DT)
        self._last_time = now
        self.screen.post_message(Tick(dt))
