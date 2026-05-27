# ui/animations/logo.py

from __future__ import annotations

import asyncio
import random
import time
from typing import Callable, Dict, Iterable, List, Optional, Set

from rich.text import Text

GLITCH_CHARS = (
    r"!@#$%^&*()_+-=[]{}|;:',.<>?/~`\\"
    r"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    r"abcdefghijklmnopqrstuvwxyz"
    r"0123456789"
)
GLITCH_COLORS = ["red", "green", "yellow", "cyan", "magenta", "blue", "bright_white"]
FINAL_COLOR = "bright_white"

REVEAL_STEP_FACTOR = 15
DECAY_STEP_FACTOR = 12

REVEAL_GLITCH_FRAME = 0.05
REVEAL_FINAL_FRAME = 0.04

HOLD_SECONDS = 1.2
HOLD_GLITCH_FRAME = 0.04

DECAY_GLITCH_FRAME = 0.04
DECAY_FINAL_FRAME = 0.05

HOLD_BEFORE_CLEAR = 1
HOLD_AFTER_CLEAR = 1


Cell = Dict[str, object]


class LogoAnimator:
    def __init__(self, lines: Iterable[str], update_cb: Callable[[Text], None]) -> None:
        raw_lines = list(lines)
        width = max((len(l) for l in raw_lines), default=0)
        self._lines: List[str] = [l.ljust(width) for l in raw_lines]
        self._update_cb = update_cb
        self._width = width
        self._skip_event = asyncio.Event()  # ← skip flag

        self._cells: List[Cell] = []
        for r, line in enumerate(self._lines):
            for c, ch in enumerate(line):
                if ch != " ":
                    self._cells.append({"r": r, "c": c, "char": ch, "state": 0})

    def skip(self) -> None:
        """Call this from outside (e.g. a key binding) to skip the animation."""
        self._skip_event.set()

    async def _sleep(self, seconds: float) -> bool:
        """Sleep for `seconds`, but return True immediately if skip is triggered."""
        try:
            await asyncio.wait_for(self._skip_event.wait(), timeout=seconds)
            return True  # skipped
        except asyncio.TimeoutError:
            return False  # normal timeout, keep going

    async def run(self) -> None:
        if not self._cells:
            return
        if await self._sleep(HOLD_BEFORE_CLEAR):
            return self._resolve_immediately()
        await self._phase_reveal()
        if self._skip_event.is_set():
            return self._resolve_immediately()
        await self._phase_hold()
        if self._skip_event.is_set():
            return self._resolve_immediately()
        await self._phase_decay()
        await self._sleep(HOLD_AFTER_CLEAR)  # skip during post-clear hold is fine too

    def _resolve_immediately(self) -> None:
        """If skipped mid-animation, clear all cells and emit a blank frame."""
        for cell in self._cells:
            cell["state"] = 4
        self._refresh(glitch_mask=set())

    def _build_frame(self, glitch_mask: Optional[Set[int]] = None) -> Text:
        glitch_mask = glitch_mask or set()
        text = Text(no_wrap=True)
        height = len(self._lines)
        buffer = [[" "] * self._width for _ in range(height)]

        for idx, cell in enumerate(self._cells):
            r, c, ch, state = cell["r"], cell["c"], cell["char"], cell["state"]
            if state in (0, 4):
                continue
            if idx in glitch_mask or state in (1, 3):
                buffer[r][c] = (
                    random.choice(GLITCH_CHARS),
                    random.choice(GLITCH_COLORS),
                )
            elif state == 2:
                buffer[r][c] = (ch, FINAL_COLOR)

        for r, row in enumerate(buffer):
            for item in row:
                if isinstance(item, tuple):
                    text.append(item[0], style=item[1])
                else:
                    text.append(item)
            if r < height - 1:
                text.append("\n")

        return text

    def _refresh(self, glitch_mask: Optional[Set[int]] = None) -> None:
        self._update_cb(self._build_frame(glitch_mask))

    async def _phase_reveal(self) -> None:
        indices = list(range(len(self._cells)))
        random.shuffle(indices)
        step = max(1, len(indices) // REVEAL_STEP_FACTOR)

        i = 0
        while i < len(indices):
            if self._skip_event.is_set():
                return
            batch_end = min(i + step, len(indices))
            for j in range(i, batch_end):
                self._cells[indices[j]]["state"] = 1
            i = batch_end
            glitch_mask = {k for k, c in enumerate(self._cells) if c["state"] == 1}
            self._refresh(glitch_mask)
            await self._sleep(REVEAL_GLITCH_FRAME)

        i = 0
        while i < len(indices):
            if self._skip_event.is_set():
                return
            batch_end = min(i + step, len(indices))
            for j in range(i, batch_end):
                self._cells[indices[j]]["state"] = 2
            i = batch_end
            glitch_mask = {k for k, c in enumerate(self._cells) if c["state"] == 1}
            self._refresh(glitch_mask)
            await self._sleep(REVEAL_FINAL_FRAME)

        self._refresh(glitch_mask=set())

    async def _phase_hold(self) -> None:
        deadline = time.time() + HOLD_SECONDS
        while time.time() < deadline:
            if self._skip_event.is_set():
                return
            self._refresh(glitch_mask=set())
            await self._sleep(HOLD_GLITCH_FRAME)

    async def _phase_decay(self) -> None:
        indices = list(range(len(self._cells)))
        random.shuffle(indices)
        step = max(1, len(indices) // DECAY_STEP_FACTOR)

        i = 0
        while i < len(indices):
            if self._skip_event.is_set():
                return
            batch_end = min(i + step, len(indices))
            for j in range(i, batch_end):
                if self._cells[indices[j]]["state"] in (1, 2):
                    self._cells[indices[j]]["state"] = 3
            i = batch_end
            glitch_mask = {k for k, c in enumerate(self._cells) if c["state"] == 3}
            self._refresh(glitch_mask)
            await self._sleep(DECAY_GLITCH_FRAME)

        i = 0
        while i < len(indices):
            if self._skip_event.is_set():
                return
            batch_end = min(i + step, len(indices))
            for j in range(i, batch_end):
                if self._cells[indices[j]]["state"] == 3:
                    self._cells[indices[j]]["state"] = 4
            i = batch_end
            glitch_mask = {k for k, c in enumerate(self._cells) if c["state"] == 3}
            self._refresh(glitch_mask)
            await self._sleep(DECAY_FINAL_FRAME)

        self._refresh(glitch_mask=set())
