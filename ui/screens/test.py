# ui/screens/test_screen.py

import asyncio

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, TabbedContent, TabPane

from core.audio import (
    async_play_bgm,
    play_sfx,
    preload_sfx,
    stop_all_sfx,
    stop_bgm,
)
from ui.dialogue import ChoiceMenu, DialogueBox, DialogueLine, MessageBox
from ui.messages import (
    ChoiceCancelled,
    ChoiceSelected,
    MessageBoxDismissed,
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
        with TabbedContent():
            with TabPane("Audio", id="tab-audio"):
                with Vertical(id="test-shell"):
                    yield Label("Audio Test Screen", id="test-header")
                    with Horizontal(id="sfx-row"):
                        for sfx_id, label, variant in SFX_BUTTONS:
                            yield Button(label, id=f"sfx-{sfx_id}", variant=variant)
                    yield Button("Stop All SFX", id="stop-all", variant="warning")
                    yield Button("Stop BGM & Quit", id="quit-btn", variant="primary")
            with TabPane("Dialogue", id="tab-dialogue"):
                with Vertical(id="dialogue-shell"):
                    yield Label("Dialogue Engine Test", id="dialogue-header")
                    yield Button("Run Dialogue Test", id="run-dialogue-test", variant="primary")
                    yield Vertical(id="dialogue-stage")

    def on_mount(self) -> None:
        self._choice_future: asyncio.Future[int] | None = None
        self._dismiss_future: asyncio.Future[None] | None = None
        try:
            preload_sfx(*(f"{name}.mp3" for name, _, _ in SFX_BUTTONS))
        except Exception:
            pass
        try:
            asyncio.create_task(self._start_bgm())
        except Exception:
            pass

    async def _start_bgm(self) -> None:
        try:
            await async_play_bgm("melancholia.mp3", loops=-1, fade_ms=1000)
        except Exception:
            pass

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
        elif btn.id == "run-dialogue-test":
            btn.disabled = True
            asyncio.create_task(self._run_dialogue_test())

    def on_choice_selected(self, message: ChoiceSelected) -> None:
        if self._choice_future is not None and not self._choice_future.done():
            self._choice_future.set_result(message.index)

    def on_choice_cancelled(self, message: ChoiceCancelled) -> None:
        if self._choice_future is not None and not self._choice_future.done():
            self._choice_future.set_result(-1)

    def on_message_box_dismissed(self, message: MessageBoxDismissed) -> None:
        if self._dismiss_future is not None and not self._dismiss_future.done():
            self._dismiss_future.set_result(None)

    async def _run_dialogue_test(self) -> None:
        stage = self.query_one("#dialogue-stage", Vertical)

        lines = [
            DialogueLine("Hello, traveller. Welcome to the engine."),
            DialogueLine("Quick. Sharp. Snappy.", pause_scale=0.5),
            DialogueLine("No, really, it works.", pause_scale=0.0),
            DialogueLine("This... line... is... slow...", typing_speed=0.08),
        ]

        box = DialogueBox(lines, skip_key="enter")
        await stage.mount(box)
        await box.play()
        await box.remove()

        menu = ChoiceMenu("What do you want to test next?", ["Test MessageBox", "End Test"])
        self._choice_future = asyncio.get_event_loop().create_future()
        await stage.mount(menu)
        index = await self._choice_future
        self._choice_future = None
        await menu.remove()

        if index == 0:
            msg = MessageBox(
                ["Welcome to FOTD Engine.", ("This line is colored.", "bold green")],
                title="Engine Info",
            )
            self._dismiss_future = asyncio.get_event_loop().create_future()
            await stage.mount(msg)
            await self._dismiss_future
            self._dismiss_future = None
            await msg.remove()

        result = Label("All dialogue tests passed.")
        await stage.mount(result)

        btn = self.query_one("#run-dialogue-test", Button)
        btn.disabled = False

    def action_quit_screen(self) -> None:
        stop_bgm(fade_ms=300)
        self.app.pop_screen()