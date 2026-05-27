# core/dialogue.py

import asyncio
from dataclasses import dataclass
from typing import Optional, Union

from rich.text import Text
from textual.app import ComposeResult
from textual.events import Key
from textual.widget import Widget
from textual.widgets import Static

PUNCTUATION_PAUSES: dict[str, float] = {
    ",": 0.25,
    ";": 0.25,
    ":": 0.25,
    ".": 0.5,
    "!": 0.5,
    "?": 0.5,
    "…": 0.8,
}

PAUSE_ESCAPE = "\\"

__all__ = [
    "DialogueLine",
    "DialogueBox",
    "ChoiceMenu",
    "MessageBox",
]


@dataclass
class DialogueLine:
    text: str
    speaker: str = ""
    color: str = "white"
    typing_speed: float = 0.04
    pause_scale: float = 1.0


class DialogueBox(Widget):
    def __init__(self, lines: list[DialogueLine], *, skip_key: str = "enter") -> None:
        super().__init__()
        self._lines = lines
        self._skip_key = skip_key
        self._skip_requested = False

    def compose(self) -> ComposeResult:
        yield Static("", classes="dialogue-speaker")
        yield Static("", classes="dialogue-text")

    def on_key(self, event: Key) -> None:
        if event.key == self._skip_key:
            self._skip_requested = True

    async def play(self) -> None:
        from ui.messages import DialogueFinished

        speaker_widget = self.query_one(".dialogue-speaker", Static)
        text_widget = self.query_one(".dialogue-text", Static)

        for line in self._lines:
            speaker_widget.update(line.speaker)
            text_widget.update("")
            self._skip_requested = False

            no_pause_indices: set[int] = set()
            clean_chars: list[str] = []
            i = 0
            while i < len(line.text):
                if (
                    line.text[i] == PAUSE_ESCAPE
                    and i + 1 < len(line.text)
                    and line.text[i + 1] in PUNCTUATION_PAUSES
                ):
                    clean_chars.append(line.text[i + 1])
                    no_pause_indices.add(len(clean_chars) - 1)
                    i += 2
                else:
                    clean_chars.append(line.text[i])
                    i += 1
            clean_text = "".join(clean_chars)

            revealed = ""
            for idx, char in enumerate(clean_chars):
                if self._skip_requested:
                    text_widget.update(clean_text)
                    break
                revealed += char
                text_widget.update(revealed)
                pause = PUNCTUATION_PAUSES.get(char)
                if pause is not None and idx not in no_pause_indices:
                    await asyncio.sleep(pause * line.pause_scale)
                else:
                    await asyncio.sleep(line.typing_speed)

            await asyncio.sleep(0.2)

        self.post_message(DialogueFinished())


class ChoiceMenu(Widget):
    can_focus = True

    def __init__(self, prompt: str, choices: list[str]) -> None:
        super().__init__()
        self._prompt = prompt
        self._choices = choices
        self._selected = 0

    def compose(self) -> ComposeResult:
        yield Static(self._prompt, classes="choice-prompt")
        for choice in self._choices:
            yield Static(choice, classes="choice-item")

    def on_mount(self) -> None:
        self._update_selection()
        self.focus()

    def _update_selection(self) -> None:
        items = list(self.query(".choice-item"))
        for i, item in enumerate(items):
            if i == self._selected:
                item.add_class("choice-selected")
            else:
                item.remove_class("choice-selected")

    def key_up(self) -> None:
        if self._selected > 0:
            self._selected -= 1
            self._update_selection()

    def key_k(self) -> None:
        self.key_up()

    def key_down(self) -> None:
        if self._selected < len(self._choices) - 1:
            self._selected += 1
            self._update_selection()

    def key_j(self) -> None:
        self.key_down()

    def key_enter(self) -> None:
        from ui.messages import ChoiceSelected

        self.post_message(ChoiceSelected(self._selected, self._choices[self._selected]))

    def key_escape(self) -> None:
        from ui.messages import ChoiceCancelled

        self.post_message(ChoiceCancelled())


class MessageBox(Widget):
    can_focus = True

    def __init__(
        self,
        lines: list[Union[str, tuple[str, str]]],
        *,
        title: str = "",
        choices: Optional[list[str]] = None,
    ) -> None:
        super().__init__()
        self._lines = lines
        self._choices = choices
        self._selected = 0
        self.border_title = title

    def compose(self) -> ComposeResult:
        content = Text()
        for line in self._lines:
            if isinstance(line, str):
                content.append(line + "\n")
            else:
                content.append(line[0] + "\n", style=line[1])
        yield Static(content, classes="message-box-content")
        if self._choices:
            for choice in self._choices:
                yield Static(choice, classes="choice-item")

    def on_mount(self) -> None:
        if self._choices:
            self._update_selection()
        self.focus()

    def _update_selection(self) -> None:
        items = list(self.query(".choice-item"))
        for i, item in enumerate(items):
            if i == self._selected:
                item.add_class("choice-selected")
            else:
                item.remove_class("choice-selected")

    def on_key(self, event: Key) -> None:
        if not self._choices:
            from ui.messages import MessageBoxDismissed

            self.post_message(MessageBoxDismissed())

    def key_up(self) -> None:
        if self._choices and self._selected > 0:
            self._selected -= 1
            self._update_selection()

    def key_k(self) -> None:
        self.key_up()

    def key_down(self) -> None:
        if self._choices and self._selected < len(self._choices) - 1:
            self._selected += 1
            self._update_selection()

    def key_j(self) -> None:
        self.key_down()

    def key_enter(self) -> None:
        if self._choices:
            from ui.messages import ChoiceSelected

            self.post_message(
                ChoiceSelected(self._selected, self._choices[self._selected])
            )

    def key_escape(self) -> None:
        if self._choices:
            from ui.messages import ChoiceCancelled

            self.post_message(ChoiceCancelled())
