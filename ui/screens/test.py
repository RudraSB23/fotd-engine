# ui/screens/test_screen.py

import asyncio

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label

from core.audio import (
    async_play_bgm,
    play_sfx,
    preload_sfx,
    stop_all_sfx,
    stop_bgm,
)

SFX_BUTTONS = [
    ("fail", "Fail", "error"),
    ("glitch", "Glitch", "default"),
    ("success", "Success", "success"),
    ("vhs_static", "VHS Static", "default"),
]


class TestScreen(Screen):
    BINDINGS = [
        ("q", "quit_screen", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="test-shell"):
            yield Label("Audio Test Screen", id="test-header")
            with Horizontal(id="sfx-row"):
                for sfx_id, label, variant in SFX_BUTTONS:
                    yield Button(label, id=f"sfx-{sfx_id}", variant=variant)
            yield Button("Stop All SFX", id="stop-all", variant="warning")
            yield Button("Stop BGM & Quit", id="quit-btn", variant="primary")

    def on_mount(self) -> None:
        preload_sfx(*(f"{name}.mp3" for name, _, _ in SFX_BUTTONS))
        asyncio.create_task(self._start_bgm())

    async def _start_bgm(self) -> None:
        await async_play_bgm("melancholia.mp3", loops=-1, fade_ms=1000)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button
        if btn.id == "quit-btn":
            stop_bgm(fade_ms=300)
            self.app.pop_screen()
        elif btn.id == "stop-all":
            stop_all_sfx()
        elif btn.id and btn.id.startswith("sfx-"):
            sfx_name = btn.id.removeprefix("sfx-")
            play_sfx(f"{sfx_name}.mp3", volume=0.8)

    def action_quit_screen(self) -> None:
        stop_bgm(fade_ms=300)
        self.app.pop_screen()
