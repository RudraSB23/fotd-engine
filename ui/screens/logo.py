# ui/screens/logo_screen.py

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.widgets import Static

from core import load_ascii
from core.scene import Scene
from ui.animations import LogoAnimator
from ui.messages import LogoFinished


class LogoScreen(Scene):
    BINDINGS = [("enter", "skip", "Skip")]

    def compose(self) -> ComposeResult:
        with Vertical(id="logo-shell"):
            yield Static("", id="logo-static")

    def on_mount(self) -> None:
        raw = load_ascii("fotd.txt")
        lines = raw.splitlines()
        widget = self.query_one("#logo-static", Static)
        self._animator = LogoAnimator(lines, update_cb=widget.update)
        asyncio.create_task(self._run_logo(self._animator))

    async def _run_logo(self, animator: LogoAnimator) -> None:
        await animator.run()
        self.app.post_message(LogoFinished())

    def action_skip(self) -> None:
        self._animator.skip()
