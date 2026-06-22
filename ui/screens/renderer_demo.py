import asyncio

from textual.widgets import Label, Static

from core.renderer import Renderer, VideoLayer
from core.scene import Scene

__all__ = ["RendererDemoScreen"]


class RendererDemoScreen(Scene):
    def compose(self) -> None:
        try:
            import cv2  # noqa: F401

            yield Static(id="canvas", markup=False, expand=True)
        except ImportError:
            yield Label(
                "OpenCV (opencv-python) is not installed.\n"
                "Install it with: pip install opencv-python",
                id="error",
            )

    def on_mount(self) -> None:
        try:
            import cv2  # noqa: F401
        except ImportError:
            return

        w, h = self.app.size
        canvas = self.query_one("#canvas", Static)
        self._renderer = Renderer(w, h, canvas.update, fps=12)
        self._renderer.add_layer(VideoLayer("assets/demo.mp4", loop=True, z_order=0))
        asyncio.create_task(self._renderer.run())

    def on_unmount(self) -> None:
        if hasattr(self, "_renderer"):
            self._renderer.stop()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()