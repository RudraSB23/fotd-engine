# ui/animations/video.py
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Callable

from rich.text import Text

__all__ = ["AsciiVideoAnimator"]


class AsciiVideoAnimator:
    """
    Plays a pre-computed ASCII frame sequence into a Static widget.

    Mirrors LogoAnimator: instantiate, pass update_cb, await run().
    Call skip() or pause()/resume() from outside (e.g. key bindings).
    Posts no messages — the caller (VideoScreen) handles that.
    """

    def __init__(
        self,
        frames: list[list[str]],
        fps: float,
        update_cb: Callable[[Text], None],
        *,
        loop: bool = False,
    ) -> None:
        self._frames = frames
        self._frame_duration = 1.0 / max(fps, 0.1)
        self._update_cb = update_cb
        self._loop = loop
        self._skip_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # start unpaused

    # ------------------------------------------------------------------
    # Control API (call from key bindings / outside)
    # ------------------------------------------------------------------

    def skip(self) -> None:
        self._skip_event.set()

    def pause(self) -> None:
        self._pause_event.clear()

    def resume(self) -> None:
        self._pause_event.set()

    def toggle_pause(self) -> None:
        if self._pause_event.is_set():
            self.pause()
        else:
            self.resume()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        update_cb: Callable[[Text], None],
        **kwargs,
    ) -> "AsciiVideoAnimator":
        """Load from a .frames JSON file (produced by tools/video_to_ascii.py)."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["frames"], float(data["fps"]), update_cb, **kwargs)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    async def run(self) -> None:
        while True:
            for frame in self._frames:
                if self._skip_event.is_set():
                    return
                # Block here while paused
                await self._pause_event.wait()
                if self._skip_event.is_set():
                    return
                self._update_cb(self._build_text(frame))
                if await self._sleep(self._frame_duration):
                    return  # skipped during frame display
            if not self._loop:
                break

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _build_text(frame: list[str]) -> Text:
        text = Text(no_wrap=True)
        for i, row in enumerate(frame):
            text.append(row)
            if i < len(frame) - 1:
                text.append("\n")
        return text

    async def _sleep(self, seconds: float) -> bool:
        """Returns True if skipped before timeout."""
        try:
            await asyncio.wait_for(self._skip_event.wait(), timeout=seconds)
            return True
        except asyncio.TimeoutError:
            return False
