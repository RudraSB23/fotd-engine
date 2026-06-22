# core/renderer.py
#
# The compositing render pipeline for fotd-engine.
#
# Three main concepts:
#
#   FrameBuffer  — the fixed-size character grid that all layers draw into.
#
#   RenderLayer  — abstract base; anything that can draw one frame worth of
#                  content into a FrameBuffer.  Two built-in implementations:
#
#       VideoLayer   — streams ASCII frames live from a video file via
#                      opencv-python.  Decoding happens in a thread executor
#                      so Textual's event loop is never blocked.  opencv is an
#                      optional dep; a clear ImportError is raised on first use
#                      if it is missing.
#
#       SpriteLayer  — the game-rendering layer.  Entities call submit() each
#                      tick with their current sprite and position; SpriteLayer
#                      blits them all.  Always returns True from render_into
#                      (never exhausts).
#
#   Renderer     — owns the FrameBuffer, manages a z-ordered list of layers,
#                  and outputs composed frames to a callback (typically a
#                  Textual Static.update).  Operates in two modes:
#
#       run()  — autonomous async loop at a target FPS.
#                Use this for video playback / cutscenes.
#
#       tick() — renders exactly one frame, no timing logic.
#                Call this from Scene.on_tick() for live game rendering.

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from rich.style import Style
from rich.text import Text

__all__ = [
    "FrameBuffer",
    "RenderLayer",
    "VideoLayer",
    "SpriteLayer",
    "Renderer",
]

# ---------------------------------------------------------------------------
# Optional opencv import — only VideoLayer needs it
# ---------------------------------------------------------------------------

try:
    import cv2 as _cv2

    _CV2_AVAILABLE = True
except ImportError:
    _cv2 = None  # type: ignore[assignment]
    _CV2_AVAILABLE = False

# ASCII brightness ramp: space (dark) → @ (bright), 92 distinct characters.
# Swap out for a shorter ramp (e.g. " .:-=+*#@") for a chunkier look.
_RAMP = (
    " `.-':_,^=;><+!rc*/z?sLTv)J7(|Fi{C}fI31tlu[neoZ5Yxjya]"
    "2ESwqkP6h9d4VpOGbUAKXHm8RD#$Bg0MNWQ%&@"
)


# ---------------------------------------------------------------------------
# FrameBuffer
# ---------------------------------------------------------------------------


class FrameBuffer:
    """
    A fixed-size (width × height) character grid.

    All RenderLayers draw into a shared FrameBuffer each frame.
    Renderer calls to_rich_text() to flush the finished frame to Textual.

    Each cell stores (char, rich_style_string | None).  None means "no style",
    which avoids building a Style object for every blank cell.
    """

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._cells: list[list[tuple[str, str | None]]] = [
            [(" ", None)] * width for _ in range(height)
        ]

    # ------------------------------------------------------------------
    # Drawing primitives
    # ------------------------------------------------------------------

    def clear(self, fill: str = " ") -> None:
        """Fill the entire buffer with one character (default: space)."""
        ch = fill[0] if fill else " "
        self._cells = [[(ch, None)] * self.width for _ in range(self.height)]

    def set_cell(self, x: int, y: int, char: str, style: str | None = None) -> None:
        """Set a single cell; silently clamps to buffer bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._cells[y][x] = (char[0], style)

    def blit(
        self,
        sprite: list[str],
        x: int,
        y: int,
        *,
        transparent: bool = True,
        style: str | None = None,
    ) -> None:
        """
        Stamp a multiline ASCII sprite at (x, y).

        transparent=True (default) skips space characters so the layer
        beneath shows through — essential for compositing.
        """
        for dy, row in enumerate(sprite):
            for dx, ch in enumerate(row):
                if transparent and ch == " ":
                    continue
                self.set_cell(x + dx, y + dy, ch, style)

    def fill_rows(self, rows: list[str], style: str | None = None) -> None:
        """
        Overwrite the buffer from a pre-built list of string rows.

        Used by VideoLayer to stamp a full ASCII video frame in one call.
        Rows are clipped to buffer dimensions if they don't match exactly.
        """
        for y, row in enumerate(rows[: self.height]):
            for x, ch in enumerate(row[: self.width]):
                self._cells[y][x] = (ch, style)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def to_rich_text(self) -> Text:
        """Build a Rich Text object from the current buffer state."""
        text = Text(no_wrap=True)
        for y, row in enumerate(self._cells):
            for ch, st in row:
                text.append(ch, style=Style.parse(st) if st else Style.null())
            if y < self.height - 1:
                text.append("\n")
        return text


# ---------------------------------------------------------------------------
# RenderLayer — abstract base
# ---------------------------------------------------------------------------


class RenderLayer(ABC):
    """
    Anything that can contribute one frame's worth of drawing to a FrameBuffer.

    Layers are composited in ascending z_order: 0 is the bottommost layer
    (background), higher numbers draw on top.  Typical usage:

        video_bg   = VideoLayer("bg.mp4",   z_order=0)
        tiles      = SpriteLayer(           z_order=1)
        entities   = SpriteLayer(           z_order=2)
        hud        = SpriteLayer(           z_order=3)
    """

    z_order: int = 0

    @abstractmethod
    async def render_into(self, buf: FrameBuffer) -> bool:
        """
        Draw into buf for the current frame.

        Returns True  → still has content; keep calling next frame.
        Returns False → exhausted (e.g. video ended); Renderer may stop.

        Persistent game layers (SpriteLayer) always return True.
        """
        ...

    def reset(self) -> None:
        """Reset to initial state (e.g. rewind a video to frame 0)."""


# ---------------------------------------------------------------------------
# VideoLayer
# ---------------------------------------------------------------------------


class VideoLayer(RenderLayer):
    """
    Streams ASCII frames live from a video file via opencv-python.

    Decoding is done in asyncio's default thread executor so it never blocks
    Textual's event loop.  The VideoCapture is opened lazily on the first
    render_into() call so the layer can be constructed before the Renderer
    knows its output dimensions.

    opencv-python is an optional dependency:
        pip install opencv-python
    A descriptive ImportError is raised on first use if it is missing.

    Args:
        path:        Path to the video file (any format opencv supports).
        width:       ASCII output columns.  Defaults to FrameBuffer.width.
        height:      ASCII output rows.    Defaults to FrameBuffer.height.
        target_fps:  How many frames per second to display.  Source frames
                     are skipped to hit this rate.  Default 12 fps — a sweet
                     spot for ASCII legibility vs file size.
        ramp:        ASCII brightness ramp string (dark → bright).
        loop:        If True, rewind and replay when the video ends.
        z_order:     Compositing order (see RenderLayer).
    """

    def __init__(
        self,
        path: str,
        *,
        width: int | None = None,
        height: int | None = None,
        target_fps: float = 12.0,
        ramp: str = _RAMP,
        loop: bool = False,
        z_order: int = 0,
    ) -> None:
        if not _CV2_AVAILABLE:
            raise ImportError(
                "VideoLayer requires opencv-python.\n"
                "Install it with:  pip install opencv-python\n"
                "It is intentionally kept as an optional dependency."
            )
        self.z_order = z_order
        self._path = path
        self._override_w = width
        self._override_h = height
        self._target_fps = target_fps
        self._ramp = ramp
        self._loop = loop

        # Lazy-initialised on first render_into() call
        self._cap: object | None = None
        self._render_w: int = 0
        self._render_h: int = 0
        self._skip: int = 1
        self._frame_idx: int = 0
        self._exhausted: bool = False

    # ------------------------------------------------------------------
    # Internal helpers (all run in thread executor — no async here)
    # ------------------------------------------------------------------

    def _open(self, buf: FrameBuffer) -> None:
        self._render_w = self._override_w or buf.width
        self._render_h = self._override_h or buf.height
        self._cap = _cv2.VideoCapture(self._path)
        src_fps: float = self._cap.get(_cv2.CAP_PROP_FPS) or 24.0
        self._skip = max(1, round(src_fps / self._target_fps))
        self._frame_idx = 0
        self._exhausted = False

    def _decode_next(self) -> list[str] | None:
        """
        Blocking: advance the VideoCapture until the next display frame
        (honouring the source→target fps skip ratio), convert it to ASCII
        rows, and return them.  Returns None when the video is finished.
        """
        ramp, rlen = self._ramp, len(self._ramp)
        while True:
            ok, frame = self._cap.read()
            if not ok:
                return None
            idx = self._frame_idx
            self._frame_idx += 1
            if idx % self._skip != 0:
                continue
            small = _cv2.resize(frame, (self._render_w, self._render_h))
            gray = _cv2.cvtColor(small, _cv2.COLOR_BGR2GRAY)
            return [
                "".join(ramp[min(int(p / 256 * rlen), rlen - 1)] for p in row)
                for row in gray
            ]

    # ------------------------------------------------------------------
    # RenderLayer interface
    # ------------------------------------------------------------------

    async def render_into(self, buf: FrameBuffer) -> bool:
        if self._exhausted:
            return False

        # Open the capture lazily (needs buf dims)
        if self._cap is None:
            self._open(buf)

        rows: list[str] | None = await asyncio.get_event_loop().run_in_executor(
            None, self._decode_next
        )

        if rows is None:
            if self._loop:
                self.reset()  # rewind
                self._open(buf)  # re-open
                rows = await asyncio.get_event_loop().run_in_executor(
                    None, self._decode_next
                )
                if rows is None:  # empty video edge-case
                    self._exhausted = True
                    return False
            else:
                self._exhausted = True
                return False

        buf.fill_rows(rows)
        return True

    def reset(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._exhausted = False

    def __del__(self) -> None:
        if getattr(self, "_cap", None) is not None:
            try:
                self._cap.release()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# SpriteLayer
# ---------------------------------------------------------------------------


@dataclass
class _DrawCall:
    sprite: list[str]
    x: int
    y: int
    style: str | None
    transparent: bool


class SpriteLayer(RenderLayer):
    """
    A persistent compositing layer for ASCII sprites and tiles.

    This is the primary game-rendering layer.  Game entities call submit()
    each tick with their current sprite and position; at render time,
    SpriteLayer blits everything in submission order.

    SpriteLayer never exhausts — render_into() always returns True.

    Typical usage inside a Scene:

        class MyScene(Scene):
            def compose(self) -> ComposeResult:
                yield Static("", id="canvas")

            def on_mount(self) -> None:
                widget = self.query_one("#canvas", Static)
                self._sprites = SpriteLayer(z_order=1)
                self._renderer = Renderer(80, 24, widget.update, fps=30)
                self._renderer.add_layer(self._sprites)

            async def on_tick(self, msg: Tick) -> None:
                self._sprites.submit(PLAYER_SPRITE, self._px, self._py,
                                     style="bold green")
                await self._renderer.tick()
    """

    def __init__(self, *, z_order: int = 0) -> None:
        self.z_order = z_order
        self._queue: list[_DrawCall] = []

    def submit(
        self,
        sprite: list[str],
        x: int,
        y: int,
        *,
        style: str | None = None,
        transparent: bool = True,
    ) -> None:
        """Queue a sprite blit for the current frame."""
        self._queue.append(_DrawCall(sprite, x, y, style, transparent))

    async def render_into(self, buf: FrameBuffer) -> bool:
        for dc in self._queue:
            buf.blit(dc.sprite, dc.x, dc.y, style=dc.style, transparent=dc.transparent)
        self._queue.clear()
        return True  # game layers never exhaust


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class Renderer:
    """
    The compositing render pipeline.

    Owns a FrameBuffer, manages z-ordered RenderLayers, and outputs composed
    frames via a callback (typically Textual's Static.update).

    Two operating modes:

    Autonomous — run()
        Drives its own async loop at ``fps`` frames per second.  Use this for
        video playback and cutscenes.  Stops when all layers are exhausted or
        skip() / stop() is called.  Await it inside an asyncio.create_task().

    Tick-driven — tick()
        Renders exactly one frame with no timing logic.  Call it from
        Scene.on_tick() for live game rendering; your game loop provides the
        timing via the Tick(dt) message.

    Args:
        width:      FrameBuffer width  (characters per row).
        height:     FrameBuffer height (rows).
        update_cb:  Called with a Rich Text after every composed frame.
                    Typically ``my_static_widget.update``.
        fps:        Target frames per second for autonomous run() mode.
                    Ignored in tick-driven mode.
    """

    def __init__(
        self,
        width: int,
        height: int,
        update_cb: Callable[[Text], None],
        *,
        fps: float = 30.0,
    ) -> None:
        self.buf = FrameBuffer(width, height)
        self._update_cb = update_cb
        self._frame_duration = 1.0 / max(fps, 0.1)
        self._layers: list[RenderLayer] = []
        self._running: bool = False
        self._skip_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # not paused at start

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    def add_layer(self, layer: RenderLayer) -> None:
        """Add a layer; the list is kept sorted by z_order."""
        self._layers.append(layer)
        self._layers.sort(key=lambda l: l.z_order)

    def remove_layer(self, layer: RenderLayer) -> None:
        self._layers = [l for l in self._layers if l is not layer]

    def clear_layers(self) -> None:
        """Remove all layers, calling reset() on each."""
        for layer in self._layers:
            layer.reset()
        self._layers.clear()

    # ------------------------------------------------------------------
    # Control API
    # ------------------------------------------------------------------

    def skip(self) -> None:
        """Signal the run() loop to exit on the next iteration."""
        self._skip_event.set()

    def stop(self) -> None:
        """Alias for skip() — clearer intent in game-rendering contexts."""
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

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Tick-driven mode (game rendering)
    # ------------------------------------------------------------------

    async def tick(self) -> None:
        """
        Composite and flush exactly one frame.

        Call from ``async def on_tick(self, msg: Tick)`` in a Scene.
        All timing is managed by the engine's Tick loop — this method
        just draws and outputs.
        """
        self.buf.clear()
        for layer in self._layers:
            await layer.render_into(self.buf)
        self._update_cb(self.buf.to_rich_text())

    # ------------------------------------------------------------------
    # Autonomous mode (video / cutscenes)
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """
        Drive the render loop autonomously at the configured FPS.

        Exits when:
        - All layers return False from render_into() (natural end).
        - skip() or stop() is called.

        Pair with asyncio.create_task() and use post_message(VideoFinished())
        in the task's continuation to signal the rest of the app.

        Example:
            asyncio.create_task(self._play())

            async def _play(self) -> None:
                await self._renderer.run()
                self.app.post_message(VideoFinished())
        """
        self._running = True
        self._skip_event.clear()

        try:
            while not self._skip_event.is_set():
                # Respect pause
                await self._pause_event.wait()
                if self._skip_event.is_set():
                    break

                # Composite all layers
                self.buf.clear()
                any_alive = False
                for layer in self._layers:
                    if await layer.render_into(self.buf):
                        any_alive = True

                self._update_cb(self.buf.to_rich_text())

                if not any_alive:
                    break  # all layers naturally exhausted

                # Hold for the remainder of this frame interval, or exit early
                try:
                    await asyncio.wait_for(
                        self._skip_event.wait(), timeout=self._frame_duration
                    )
                    break  # skip() was called during the wait
                except asyncio.TimeoutError:
                    pass  # normal — advance to next frame
        finally:
            self._running = False
