# ui/screens/video.py
#
# VideoScreen — a full-scene cutscene player backed by core.Renderer.
#
# Push this scene onto the stack to play an ASCII video.
# It posts VideoFinished when playback ends or is skipped, so the caller
# can decide what to do next (pop_scene, replace_scene, etc.).
#
# Usage:
#
#     from ui.screens.video import VideoScreen
#     from ui.messages import VideoFinished
#
#     # Inside any Scene or Game method:
#     self.app.push_scene(VideoScreen("assets/video/intro.mp4", fps=12.0))
#
#     def on_video_finished(self, _: VideoFinished) -> None:
#         self.app.pop_scene()

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.containers import Center
from textual.widgets import Static

from core.renderer import Renderer, VideoLayer
from core.scene import Scene
from ui.messages import VideoFinished

__all__ = ["VideoScreen"]


class VideoScreen(Scene):
    """
    Full-scene ASCII video player.

    Args:
        path:   Path to the video file (any format opencv supports).
        fps:    Playback frame rate.  12 is a good default for ASCII.
        loop:   Loop the video indefinitely until skipped.
        width:  Override output width  (defaults to terminal width).
        height: Override output height (defaults to terminal height).
    """

    BINDINGS = [
        ("space", "toggle_pause", "Pause"),
        ("enter,escape", "skip", "Skip"),
    ]

    def __init__(
        self,
        path: str,
        *,
        fps: float = 12.0,
        loop: bool = False,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        super().__init__()
        self._path = path
        self._fps = fps
        self._loop = loop
        self._override_w = width
        self._override_h = height
        self._renderer: Renderer | None = None

    def compose(self) -> ComposeResult:
        with Center():
            yield Static("", id="video-display")

    def on_mount(self) -> None:
        size = self.app.size
        w = self._override_w or size.width
        h = self._override_h or size.height

        widget = self.query_one("#video-display", Static)
        self._renderer = Renderer(w, h, update_cb=widget.update, fps=self._fps)
        self._renderer.add_layer(
            VideoLayer(
                self._path,
                target_fps=self._fps,
                loop=self._loop,
                z_order=0,
            )
        )
        asyncio.create_task(self._play())

    async def _play(self) -> None:
        assert self._renderer is not None
        await self._renderer.run()
        self.app.post_message(VideoFinished())

    def action_skip(self) -> None:
        if self._renderer:
            self._renderer.skip()

    def action_toggle_pause(self) -> None:
        if self._renderer:
            self._renderer.toggle_pause()
