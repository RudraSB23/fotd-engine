# ui/screens/onboarding.py

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.widgets import Label, Markdown, Static

from core.ascii import load_ascii_snippet
from core.scene import Scene

TITLE_ART = load_ascii_snippet("engine_logo")

SECTIONS: list[tuple[str, str, str]] = [
    (
        "Overview",
        "Stack, quick start, dependencies",
        """\
## FOTD Engine

A Python console game engine built on **Textual** (TUI) and **pygame-ce** (audio).
Handles the game loop, scene stack, input bindings, save/load, dialogue, and audio
so you can focus on writing your game.

### Stack

| Dependency | Version | Role |
|---|---|---|
| Python | 3.14+ | Runtime |
| Textual | ≥ 8.2.7 | TUI framework — layout, input, async event loop |
| pygame-ce | ≥ 2.5.7 | Audio — BGM streaming + SFX channels |

### Quick Start

```bash
uv sync
uv run main.py
```

```python
from core import Game, Scene, load_styles
from core.audio import init_audio
from textual.app import ComposeResult
from textual.widgets import Label

class MyScene(Scene):
    def compose(self) -> ComposeResult:
        yield Label("hello, world")

class MyGame(Game):
    CSS_PATH = load_styles()
    def on_mount(self) -> None:
        super().on_mount()
        init_audio()
        self.push_scene(MyScene())

MyGame().run()
```
""",
    ),
    (
        "Game",
        "App subclass, tick loop, FPS",
        """\
## `Game`

Subclass `Game` instead of Textual's `App` directly.

```python
from core import Game, load_styles

class MyGame(Game):
    CSS_PATH = load_styles()

    def on_mount(self) -> None:
        super().on_mount()       # required — starts tick loop
        self.push_scene(MyScene())

MyGame(target_fps=60).run()
```

### What it does

- Inherits from both `SceneManager` and Textual's `App`
- Calls `set_interval(1 / target_fps, _tick)` on mount
- Each tick computes `dt` via `time.monotonic()`, clamped to **0.1 s** max
- First frame `dt` is `1 / target_fps` (never zero)
- Broadcasts `Tick(dt)` to the active screen every frame

### Constructor

| Argument | Type | Default | Notes |
|---|---|---|---|
| `target_fps` | `int` | `30` | Target frames per second |
""",
    ),
    (
        "Scene",
        "Screens, navigation, lifecycle",
        """\
## `Scene`

Base class for every screen. Extends Textual's `Screen` — full widget
tree, CSS, and event system available.

```python
from core import Scene, Tick
from textual.app import ComposeResult
from textual.widgets import Label

class MyScene(Scene):
    def compose(self) -> ComposeResult:
        yield Label("running")

    def on_mount(self) -> None:
        pass  # called when scene becomes active

    def on_unmount(self) -> None:
        pass  # called when scene is removed

    def on_resume(self) -> None:
        pass  # called after pop_scene() re-activates this scene

    def on_tick(self, message: Tick) -> None:
        # message.dt — seconds since last frame, max 0.1
        pass
```

Access the `Game` instance from any scene via `self.app`.

### Scene Navigation

| Method | Behaviour |
|---|---|
| `self.app.push_scene(scene)` | Push onto stack; previous stays mounted |
| `self.app.pop_scene()` | Remove top; calls `on_resume()` on new top |
| `self.app.replace_scene(scene)` | Swap current scene, no history kept |
| `self.app.current_scene` | Returns active `Screen` or `None` |
| `self.app.is_empty` | `True` if the screen stack is empty |
""",
    ),
    (
        "GameState",
        "Save, load, JSON persistence",
        """\
## `GameState`

Persistence base class. Subclass it to define save data.

```python
from core import GameState
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

@dataclass
class State(GameState):
    save_path: ClassVar[Path] = Path("saves/game.json")
    player_name: str = ""
    health: int = 100
    flags: dict[str, bool] = field(default_factory=dict)
```

### API

| Call | Returns | Notes |
|---|---|---|
| `State.load()` | `State` | Falls back to defaults on missing / bad file |
| `state.save()` | `None` | Writes JSON; creates parent dirs automatically |
| `state.reset()` | `None` | Re-initialises all fields to defaults in-place |
| `state.exists()` | `bool` | `True` if the save file is on disk |

### Details

- Serialises with `dataclasses.asdict()` → plain JSON
- `load()` reconstructs via `cls(**data)`
- `save_path` defaults to `saves/save.json` — override per subclass
- No versioning or checksum — add manually if needed
""",
    ),
    (
        "InputManager",
        "Key bindings, action mapping",
        """\
## `InputManager`

Decouples logical actions from raw key names.

```python
from core import init_input_manager, get_input_manager

init_input_manager()           # call once in Game.on_mount
im = get_input_manager()       # retrieve singleton anywhere

im.bind("confirm", "enter", "space")
im.unbind("cancel")

im.get_action("j")             # → "move_down"
im.get_keys("move_up")         # → ["up", "k"]
im.is_bound("confirm")         # → True

im.to_textual_bindings("confirm")
# → [("enter", "confirm", "Confirm"), ...]
```

### Default Bindings

| Action | Keys |
|---|---|
| `confirm` | `enter` |
| `cancel` | `escape` |
| `move_up` | `up`, `k` |
| `move_down` | `down`, `j` |
| `move_left` | `left`, `h` |
| `move_right` | `right`, `l` |
""",
    ),
    (
        "Audio",
        "BGM streaming, SFX channels",
        """\
## Audio

Powered by pygame-ce mixer. All functions **fail silently** on missing files.
Paths resolve relative to `assets/audio/`.

### Setup

```python
from core.audio import init_audio, quit_audio

init_audio()    # call once in Game.on_mount
quit_audio()    # call on app exit if needed
```

### BGM — one track at a time

```python
from core.audio import (
    async_play_bgm, play_bgm,
    stop_bgm, pause_bgm, resume_bgm,
    set_bgm_volume, is_bgm_playing,
)

await async_play_bgm("theme.mp3", loops=-1, fade_ms=1000)
play_bgm("theme.mp3", loops=-1, volume=0.7)

stop_bgm(fade_ms=500)
pause_bgm()
resume_bgm()
set_bgm_volume(0.5)
is_bgm_playing()   # → bool
```

### SFX — 8 channels, cached after first load

```python
from core.audio import (
    async_play_sfx, play_sfx,
    stop_sfx, stop_all_sfx, preload_sfx,
)

preload_sfx("confirm.mp3", "cancel.mp3")

play_sfx("confirm.mp3", volume=0.8)
play_sfx("hit.mp3", channel=3)
await async_play_sfx("ambient.mp3")

stop_sfx("confirm.mp3")
stop_all_sfx()
```
""",
    ),
    (
        "Dialogue",
        "Typewriter, choices, message boxes",
        """\
## Dialogue

### `DialogueLine`

| Field | Type | Default | Notes |
|---|---|---|---|
| `text` | `str` | — | Escape punctuation with `\\\\` to suppress its pause |
| `speaker` | `str` | `""` | Shown above the line |
| `color` | `str` | `"white"` | Rich colour string |
| `typing_speed` | `float` | `0.04` | Seconds per character |
| `pause_scale` | `float` | `1.0` | Multiplier on punctuation pauses |

**Pause durations:** `,` `;` `:` → 0.25 s · `.` `!` `?` → 0.50 s · `…` → 0.80 s

### `DialogueBox`

```python
from ui.dialogue import DialogueBox, DialogueLine

lines = [
    DialogueLine("Hello, traveller."),
    DialogueLine("Fast.", typing_speed=0.02, pause_scale=0.5),
]
box = DialogueBox(lines, skip_key="enter")
await stage.mount(box)
await box.play()
await box.remove()
```

Posts `DialogueFinished` when all lines complete.

### `ChoiceMenu`

```python
from ui.dialogue import ChoiceMenu

menu = ChoiceMenu("What next?", ["Continue", "Quit"])
await stage.mount(menu)
menu.focus()
# posts ChoiceSelected(index, text) or ChoiceCancelled
```

Navigate `↑ ↓` / `j k` · confirm `Enter` · cancel `Escape`

### `MessageBox`

```python
from ui.dialogue import MessageBox

msg = MessageBox(
    ["All systems nominal.", ("Warning: no save found.", "bold yellow")],
    title="Status",
)
await stage.mount(msg)
msg.focus()
# any key posts MessageBoxDismissed
```
""",
    ),
    (
        "Messages",
        "Event bus, built-in message types",
        """\
## Messages

Post with `self.post_message(...)` or `self.app.post_message(...)`.
Handle with `on_<snake_case_message_name>`.

| Message | Posted by | Carries |
|---|---|---|
| `LogoFinished` | `LogoScreen` | — |
| `BGMRequested` | Any widget | `filename`, `fade_ms` |
| `BGMStopped` | Audio system | — |
| `SceneTransition` | Any widget | `scene_id` |
| `ScreenPopped` | Any screen | — |
| `GameStarted` | Game logic | — |
| `GameOver` | Game logic | `reason` |
| `SceneChanged` | SceneManager | `scene_id` |
| `SceneBack` | SceneManager | — |
| `ActionTriggered` | Input system | `action`, `key` |
| `StateSaved` | Save logic | `slot` |
| `DialogueFinished` | `DialogueBox` | — |
| `ChoiceSelected` | `ChoiceMenu` / `MessageBox` | `index`, `text` |
| `ChoiceCancelled` | `ChoiceMenu` / `MessageBox` | — |
| `MessageBoxDismissed` | `MessageBox` | — |

### Example

```python
from ui.messages import SceneTransition

self.app.post_message(SceneTransition(scene_id="level_1"))

def on_scene_transition(self, msg: SceneTransition) -> None:
    if msg.scene_id == "level_1":
        self.replace_scene(Level1Scene())
```
""",
    ),
    (
        "ASCII & Styles",
        "Art loader, CSS tokens, logo animator",
        """\
## ASCII Art

```python
from core.ascii import load_ascii, load_ascii_snippet, ASCII_SNIPPETS

art = load_ascii("title.txt")
ASCII_SNIPPETS["engine_logo"] = art
art = load_ascii_snippet("engine_logo")
```

Returns `""` silently on missing files.

---

## Styles

Drop any `.tcss` file under `ui/styles/` — `load_styles()` discovers
them all automatically.

```python
class MyGame(Game):
    CSS_PATH = load_styles()
```

| Token | Role |
|---|---|
| `$background` | App background |
| `$surface` | Elevated surface |
| `$text` | Primary text |
| `$text-muted` | Secondary / dimmed text |
| `$text-disabled` | Faint / disabled |
| `$success` | Green accent |
| `$error` | Red accent |
| `$warning` | Yellow / orange accent |
| `$secondary` | Secondary accent colour |

---

## Logo Animator

Async ASCII intro: **reveal → hold → decay**.

```python
from ui.animations import LogoAnimator

animator = LogoAnimator(lines, update_cb=my_static.update)
await animator.run()
animator.skip()   # skip to cleared state
```

Tune `REVEAL_STEP_FACTOR`, `HOLD_SECONDS`, `DECAY_STEP_FACTOR`
in `ui/animations/logo.py`.
""",
    ),
    (
        "Full Example",
        "Complete game scene walkthrough",
        """\
## Full Example

### `main.py`

```python
from core import Game, load_styles
from core.audio import init_audio
from core.input import init_input_manager
from ui.messages import LogoFinished
from ui.screens import LogoScreen, OnboardingScreen

class MyGame(Game):
    CSS_PATH = load_styles()

    def on_mount(self) -> None:
        super().on_mount()
        init_audio()
        init_input_manager()
        self.push_scene(LogoScreen())

    def on_logo_finished(self, _: LogoFinished) -> None:
        self.replace_scene(OnboardingScreen())

MyGame(target_fps=60).run()
```

### A complete scene

```python
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label

from core import GameState, Scene, Tick
from core.audio import async_play_bgm
from ui.dialogue import DialogueBox, DialogueLine

@dataclass
class SaveData(GameState):
    save_path: ClassVar[Path] = Path("saves/save.json")
    score: int = 0
    visited_intro: bool = False

class GameScene(Scene):
    BINDINGS = [("q", "quit_scene", "Quit")]

    def compose(self) -> ComposeResult:
        with Vertical(id="shell"):
            yield Label("score: 0", id="score")
            yield Vertical(id="stage")

    def on_mount(self) -> None:
        self._state = SaveData.load()
        asyncio.create_task(self._setup())

    async def _setup(self) -> None:
        await async_play_bgm("theme.mp3", loops=-1, fade_ms=800)
        if not self._state.visited_intro:
            await self._run_intro()
            self._state.visited_intro = True
            self._state.save()

    async def _run_intro(self) -> None:
        stage = self.query_one("#stage", Vertical)
        box = DialogueBox(
            [DialogueLine("Welcome."), DialogueLine("Your journey begins.")],
            skip_key="enter",
        )
        await stage.mount(box)
        await box.play()
        await box.remove()

    def on_tick(self, msg: Tick) -> None:
        pass

    def action_quit_scene(self) -> None:
        self.app.pop_scene()
```
""",
    ),
]


class HubScreen(Scene):
    """Section selection hub. Navigate with ↑↓/jk, enter to open, q to quit."""

    BINDINGS = [
        ("down,j", "cursor_down", "Down"),
        ("up,k", "cursor_up", "Up"),
        ("enter", "select", "Open"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._cursor: int = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="hub-shell"):
            with Horizontal(id="hub-topbar"):
                yield Label("  FOTD ENGINE", id="hub-engine-label")
                yield Label("engine documentation  ", id="hub-topbar-right")
            with Center(id="hub-logo-wrap"):
                yield Static(TITLE_ART or "", id="hub-logo")
            with Vertical(id="hub-grid"):
                for i, (title, desc, _) in enumerate(SECTIONS):
                    yield Horizontal(
                        Label(f"{i + 1:02d}", classes="hub-num"),
                        Label(title, classes="hub-title"),
                        Label(desc, classes="hub-desc"),
                        id=f"hub-row-{i}",
                        classes="hub-row",
                    )
            with Center(id="hub-navbar"):
                yield Label(
                    "  ↑/k  up    ↓/j  down    enter  open    q  quit  ",
                    id="hub-hint",
                )

    def on_mount(self) -> None:
        self._highlight()

    def _highlight(self) -> None:
        for i in range(len(SECTIONS)):
            row = self.query_one(f"#hub-row-{i}", Horizontal)
            row.set_class(i == self._cursor, "hub-row--active")

    def action_cursor_down(self) -> None:
        if self._cursor < len(SECTIONS) - 1:
            self._cursor += 1
            self._highlight()

    def action_cursor_up(self) -> None:
        if self._cursor > 0:
            self._cursor -= 1
            self._highlight()

    def action_select(self) -> None:
        self.app.push_scene(DetailScreen(self._cursor))

    def action_quit(self) -> None:
        self.app.exit()

    def render(self) -> str:
        return ""


class DetailScreen(Scene):
    """Single-section detail view. ←/h prev, →/l next, esc/q back to hub."""

    BINDINGS = [
        ("right,l", "next", "Next"),
        ("left,h", "prev", "Prev"),
        ("escape,q", "back", "Hub"),
    ]

    def __init__(self, index: int, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._page = index

    def compose(self) -> ComposeResult:
        with Vertical(id="ob-shell"):
            with Horizontal(id="ob-topbar"):
                yield Label("", id="ob-section-title")
                yield Label("", id="ob-counter")
            with Center(id="ob-content-wrap"):
                yield Markdown("", id="ob-content")
            with Center(id="ob-navbar"):
                yield Label(
                    "  ←/h  prev    →/l  next    esc  hub  ",
                    id="ob-hint",
                )

    def on_mount(self) -> None:
        self._render_page()

    def _render_page(self) -> None:
        title, _, body = SECTIONS[self._page]
        self.query_one("#ob-section-title", Label).update(f"  {title}")
        self.query_one("#ob-counter", Label).update(
            f"{self._page + 1} / {len(SECTIONS)}  "
        )
        self.query_one("#ob-content", Markdown).update(body)

    def action_next(self) -> None:
        if self._page < len(SECTIONS) - 1:
            self._page += 1
            self._render_page()

    def action_prev(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._render_page()

    def action_back(self) -> None:
        self.app.pop_scene()

    def render(self) -> str:
        return ""


OnboardingScreen = HubScreen
