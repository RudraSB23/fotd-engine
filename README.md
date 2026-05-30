# FOTD Engine

This is a python console game engine that i built for my python games cus using curses for a whole ahh game is not a very good idea (if you plan to use this then please just vibe code it atp). it uses some random ahh libraries like pygame-ce (ce cus default didnt work on my pc rip) for audio and textual for the tui and stuff. Everything below this text is written by ai so pls dont judge i aint sitting around writing readme files all day.

---

## Stack

| Dependency | Version | Role |
|---|---|---|
| Python | 3.14+ | Runtime |
| Textual | ≥8.2.7 | TUI framework  (layout, input, async event loop) |
| pygame-ce | ≥2.5.7 | Audio (BGM streaming + SFX channels) |

---

## Project Structure

```
fotd-engine/
├── core/               # Engine internals
│   ├── game.py         # Main app + tick loop
│   ├── scene.py        # Scene base class + Tick message
│   ├── scene_manager.py# Screen stack mixin
│   ├── game_state.py   # JSON save/load base class
│   ├── input.py        # Keybinding registry
│   ├── audio.py        # BGM + SFX via pygame-ce
│   ├── ascii.py        # ASCII art loader
│   └── styles_handler.py # Auto-discovers .tcss files
├── ui/
│   ├── screens/        # Game screens (Scene subclasses)
│   ├── animations/     # Async animation helpers
│   ├── styles/         # Textual CSS (.tcss) files
│   ├── dialogue.py     # Dialogue engine widgets
│   └── messages.py     # All app-wide Message types
├── assets/
│   ├── ascii/          # ASCII art text files
│   └── audio/          # BGM (.mp3) and SFX (.mp3) files
├── saves/              # Runtime save files (gitignored)
└── main.py             # Entry point
```

---

## Core Engine (`core/`)

### `game.py` — `Game(App)`

The entry point for every game. Subclass `Game` instead of `App`.

- Inherits from both `SceneManager` and Textual's `App`
- Starts a fixed-interval tick loop on mount via `set_interval(1 / target_fps, _tick)`
- Each tick computes delta time (`dt`) using `time.monotonic()`, clamped to `0.1s` max to prevent spiral-of-death on lag spikes
- First frame `dt` is `1 / target_fps` (not zero)
- Posts a `Tick(dt)` message to the active screen every frame
- `target_fps` defaults to 30, configurable via constructor

```python
class MyGame(Game):
    def on_mount(self) -> None:
        super().on_mount()  # required — starts the tick timer
        self.push_scene(MenuScene())

MyGame(target_fps=60).run()
```

---

### `scene.py` — `Scene(Screen)` + `Tick`

Base class for all game screens.

- Extends `textual.screen.Screen` — full Textual widget tree, CSS, and event system available
- App is always accessible via `self.app`
- `on_mount()` — called when the scene becomes active (override for setup)
- `on_unmount()` — called when the scene is removed
- `on_resume()` — optional, called by `SceneManager.pop_scene()` when this scene becomes active again after the scene above it was popped
- `compose()` — declarative layout (standard Textual)

**`Tick` message** — posted to the active screen every frame by `Game._tick()`:

```python
class Tick(Message):
    dt: float  # seconds since last frame, max 0.1
```

Handle per-frame logic by defining `on_tick` in your scene:

```python
class GameScene(Scene):
    def on_tick(self, message: Tick) -> None:
        self.player.update(message.dt)
```

---

### `scene_manager.py` — `SceneManager` mixin

Thin wrapper around Textual's screen stack. Mixed into `Game`.

| Method | Behaviour |
|---|---|
| `push_scene(scene)` | Pushes scene onto stack, previous scene stays mounted underneath |
| `pop_scene()` | Removes top scene, calls `on_resume()` on the new top if it exists |
| `replace_scene(scene)` | Replaces current scene without keeping the old one in stack |
| `current_scene` | Returns the active `Screen`, or `None` |
| `is_empty` | `True` if the screen stack is empty |

---

### `game_state.py` — `GameState`

Persistence base class. Subclass it to define your game's save data.

- Built on `dataclasses.dataclass`
- `save_path: ClassVar[Path]` — defaults to `saves/save.json`, override per subclass
- `save()` — serialises all fields via `dataclasses.asdict()`, writes JSON, creates parent dirs automatically
- `load()` — classmethod, reads JSON and reconstructs via `cls(**data)`. Falls back to `cls()` on missing/malformed file
- `reset()` — re-initialises the instance to default field values in-place
- `exists()` — returns `True` if the save file exists on disk
- Format: plain JSON, no versioning, no checksum

```python
@dataclass
class MyState(GameState):
    save_path: ClassVar[Path] = Path("saves/my_game.json")
    player_name: str = ""
    health: int = 100
    flags: dict[str, bool] = field(default_factory=dict)

state = MyState.load()
state.health = 80
state.save()
```

---

### `input.py` — `InputManager`

A keybinding registry that maps logical action names to key strings.

- Default bindings: `confirm → enter`, `cancel → escape`, `move_up → up/k`, `move_down → down/j`, `move_left → left/h`, `move_right → right/l`
- `bind(action, *keys)` — set keys for an action
- `unbind(action)` — remove an action's binding
- `get_action(key)` — resolve a raw key string to an action name
- `get_keys(action)` — get all keys bound to an action
- `is_bound(action)` — check if an action has at least one key
- `to_textual_bindings(action)` — returns `list[tuple[str, str, str]]` in Textual's `BINDINGS` format
- `init_input_manager()` — initialise the singleton with defaults
- `get_input_manager()` — retrieve the singleton from anywhere

---

### `audio.py` — BGM + SFX

Audio system via pygame-ce mixer. Async-safe for Textual contexts.

**Initialisation:** `init_audio()` / `quit_audio()`

**BGM (streaming, one track at a time):**
- `play_bgm(filename, loops=-1, volume=0.7, fade_ms=0)`
- `stop_bgm(fade_ms=0)` / `pause_bgm()` / `resume_bgm()` / `set_bgm_volume(v)` / `is_bgm_playing()`

**SFX (8 simultaneous channels, cached after first load):**
- `play_sfx(filename, volume=1.0, channel=None)`
- `stop_sfx(filename)` / `stop_all_sfx()` / `preload_sfx(*filenames)`

**Async helpers:**
- `async_play_bgm(filename, **kwargs)` — disk I/O on executor, non-blocking
- `async_play_sfx(filename, **kwargs)` — loads on executor, plays on main thread

All audio files resolved relative to `assets/audio/`. All functions fail silently on missing files.

---

### `ascii.py` — ASCII Art Loader

- `load_ascii(filename)` — reads `assets/ascii/<filename>`, returns `""` on missing file
- `load_ascii_snippet(name)` — looks up from in-memory `ASCII_SNIPPETS` dict

---

### `styles_handler.py` — CSS Auto-discovery

- `load_styles()` — walks `ui/styles/` recursively, returns all `.tcss` file paths for use in `CSS_PATH`

---

## UI Layer (`ui/`)

### `dialogue.py` — Dialogue Engine

**`DialogueLine`** — data class for one line:
- `text` — supports `\` escape before punctuation to suppress its natural pause
- `speaker`, `color`, `typing_speed` (s/char, default 0.04), `pause_scale` (multiplier on punctuation pauses)
- Punctuation pauses: `,` `;` `:` → 0.25s · `.` `!` `?` → 0.5s · `…` → 0.8s

**`DialogueBox(Widget)`** — typewriter player:
- `await box.play()` — plays all lines, posts `DialogueFinished` when done
- Press `skip_key` (default Enter) mid-line to instantly reveal current line

**`ChoiceMenu(Widget)`** — keyboard-navigable choice list:
- Arrow keys / `j` `k` to navigate, Enter to confirm, Escape to cancel
- Posts `ChoiceSelected(index, text)` or `ChoiceCancelled`

**`MessageBox(Widget)`** — styled info box:
- Lines can be plain `str` or `(text, rich_style)` tuples
- Without choices: any key posts `MessageBoxDismissed`
- With choices: same as `ChoiceMenu`

---

### `messages.py` — App-wide Messages

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
| `ChoiceSelected` | `ChoiceMenu`, `MessageBox` | `index`, `text` |
| `ChoiceCancelled` | `ChoiceMenu`, `MessageBox` | — |
| `MessageBoxDismissed` | `MessageBox` | — |

---

### `animations/logo.py` — `LogoAnimator`

Async ASCII art intro animator with glitch effects.

- Three phases: **reveal** (cells glitch in randomly), **hold** (static display), **decay** (cells glitch out)
- Each non-space character is an independent cell cycling through states: hidden → glitching → revealed → glitching → gone
- Glitch characters drawn from symbols, letters, digits in random Rich colours; resolved characters render in `bright_white`
- `skip()` — skips to cleared state immediately, safe to call from any key binding
- All timing tunable via module-level constants: `REVEAL_STEP_FACTOR`, `HOLD_SECONDS`, `DECAY_STEP_FACTOR`, and per-phase frame delays

---

## Entry Point (`main.py`)

```python
class Main(Game):
    CSS_PATH = load_styles()

    def on_mount(self) -> None:
        super().on_mount()   # starts tick timer
        init_audio()
        self.push_scene(LogoScreen())

    def on_logo_finished(self, _message: LogoFinished) -> None:
        self.push_scene(TestScreen())

Main().run()
```

---

## Quick Start

```python
from core import Game, Scene, GameState
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from textual.app import ComposeResult
from textual.widgets import Label

@dataclass
class State(GameState):
    save_path: ClassVar[Path] = Path("saves/game.json")
    score: int = 0

class GameScene(Scene):
    def compose(self) -> ComposeResult:
        yield Label("Game running.")

    def on_tick(self, message) -> None:
        pass  # per-frame update logic here

class MyGame(Game):
    def on_mount(self) -> None:
        super().on_mount()
        self.push_scene(GameScene())

MyGame().run()
```

---

## Development

```bash
uv sync          # install dependencies
uv run main.py   # run the engine
```
