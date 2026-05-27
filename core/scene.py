# core/scene.py

from typing import Optional

from textual.screen import Screen

__all__ = [
    "SceneManager",
    "init_scene_manager",
    "get_scene_manager",
]

_manager: Optional["SceneManager"] = None


def init_scene_manager(app) -> "SceneManager":
    global _manager
    if _manager is not None:
        return _manager
    _manager = SceneManager(app)
    return _manager


def get_scene_manager() -> Optional["SceneManager"]:
    return _manager


class SceneManager:

    def __init__(self, app) -> None:
        self._app = app

    def go_to(self, scene_id: str, **kwargs) -> None:
        from ui.screens import _screens
        from ui.messages import SceneChanged
        from core.audio import play_bgm

        screen_cls = _screens.get(scene_id)
        if screen_cls is None:
            print(f"[scene] unknown scene_id: '{scene_id}'")
            return

        screen = screen_cls(**kwargs)

        bgm = getattr(screen_cls, "BGM", None)
        if bgm is not None:
            play_bgm(bgm, fade_ms=800)

        self._app.push_screen(screen)
        self._app.post_message(SceneChanged(scene_id))

    def replace(self, scene_id: str, **kwargs) -> None:
        from ui.screens import _screens
        from ui.messages import SceneChanged
        from core.audio import play_bgm

        screen_cls = _screens.get(scene_id)
        if screen_cls is None:
            print(f"[scene] unknown scene_id: '{scene_id}'")
            return

        screen = screen_cls(**kwargs)

        bgm = getattr(screen_cls, "BGM", None)
        if bgm is not None:
            play_bgm(bgm, fade_ms=800)

        self._app.pop_screen()
        self._app.push_screen(screen)
        self._app.post_message(SceneChanged(scene_id))

    def back(self, fade_ms: int = 0) -> None:
        from ui.messages import SceneBack
        from core.audio import stop_bgm

        if fade_ms > 0:
            stop_bgm(fade_ms=fade_ms)

        self._app.pop_screen()
        self._app.post_message(SceneBack())

    @staticmethod
    def register(name: str, screen_cls: type[Screen]) -> None:
        from ui.screens import _screens

        _screens[name] = screen_cls