# ui/widgets/canvas.py
#
# SceneCanvas — a Textual Static subclass backed by the core Renderer.
#
# It exposes the same blit/set_cell/clear API as a plain buffer but wires
# everything through Renderer + SpriteLayer so a game scene never touches
# Rich Text directly.
#
# Two flush modes:
#
#   auto_flush=True  — the widget calls renderer.tick() on every Tick message.
#                      Set this when the Scene manages all draw calls from
#                      on_tick and wants zero boilerplate in the widget.
#
#   auto_flush=False — the scene calls await canvas.flush() manually, giving
#                      full control over when the frame is committed.

from __future__ import annotations

from textual.widgets import Static

from core.renderer import Renderer, SpriteLayer
from core.scene import Tick

__all__ = ["SceneCanvas"]


class SceneCanvas(Static):
    """
    A fixed-size character-grid widget driven by the core Renderer.

    Use it as a drop-in drawing surface inside any Scene:

        class MyScene(Scene):
            def compose(self) -> ComposeResult:
                yield SceneCanvas(80, 24, id="map", auto_flush=True)

            async def on_tick(self, msg: Tick) -> None:
                canvas = self.query_one("#map", SceneCanvas)
                canvas.clear()
                canvas.blit(WALL_SPRITE, 0, 0)
                canvas.blit(PLAYER_SPRITE, self._px, self._py,
                            style="bold green")
                # auto_flush=True → renderer.tick() is called automatically
                # by the widget's own on_tick handler.

    For manual control set auto_flush=False and call ``await canvas.flush()``
    yourself at the end of your on_tick.
    """

    def __init__(
        self,
        width: int,
        height: int,
        *,
        auto_flush: bool = False,
        **kwargs,
    ) -> None:
        super().__init__("", **kwargs)
        self._canvas_w = width
        self._canvas_h = height
        self._auto_flush = auto_flush

        # Created in on_mount once the widget exists and can be passed to update
        self._renderer: Renderer | None = None
        self._sprites: SpriteLayer | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._sprites = SpriteLayer(z_order=0)
        self._renderer = Renderer(
            self._canvas_w,
            self._canvas_h,
            update_cb=self.update,
            fps=30.0,
        )
        self._renderer.add_layer(self._sprites)

    # ------------------------------------------------------------------
    # Drawing API (delegates to FrameBuffer / SpriteLayer)
    # ------------------------------------------------------------------

    def clear(self, fill: str = " ") -> None:
        """Clear the buffer (does NOT flush — call flush() or rely on auto_flush)."""
        if self._renderer:
            self._renderer.buf.clear(fill)

    def set_cell(self, x: int, y: int, char: str, style: str | None = None) -> None:
        """Set a single cell directly in the FrameBuffer."""
        if self._renderer:
            self._renderer.buf.set_cell(x, y, char, style)

    def blit(
        self,
        sprite: list[str],
        x: int,
        y: int,
        *,
        style: str | None = None,
        transparent: bool = True,
    ) -> None:
        """
        Queue a sprite blit via SpriteLayer.

        The blit is committed to the FrameBuffer on the next flush/tick.
        """
        if self._sprites:
            self._sprites.submit(sprite, x, y, style=style, transparent=transparent)

    async def flush(self) -> None:
        """Composite all queued draw calls and push the frame to Textual."""
        if self._renderer:
            await self._renderer.tick()

    # ------------------------------------------------------------------
    # Auto-flush on Tick
    # ------------------------------------------------------------------

    async def on_tick(self, _: Tick) -> None:
        if self._auto_flush and self._renderer:
            await self._renderer.tick()
