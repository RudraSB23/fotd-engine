# FOTD Engine

A personal terminal game engine built on [Textual](https://github.com/Textualize/textual) and pygame-ce.

## Architecture

| Module | Purpose |
|---|---|
| `core/game.py` | `Game(App)` — entry point, owns the tick loop |
| `core/scene.py` | `Scene(Screen)` — base class for all screens; `Tick(dt)` message for per-frame logic |
| `core/scene_manager.py` | `SceneManager` mixin — `push_scene`, `pop_scene`, `replace_scene` |
| `core/game_state.py` | `GameState` — JSON save/load base class, subclass to define state |
| `core/input.py` | `InputManager` — keybinding registry with Textual integration |
| `core/audio.py` | BGM + SFX via pygame-ce, async-safe helpers |

## Usage

```python
from core import Game, Scene, GameState
from textual.app import ComposeResult
from textual.widgets import Label

class MyGame(Game):
    def on_mount(self) -> None:
        super().on_mount()
        self.push_scene(MenuScene())

class MenuScene(Scene):
    def compose(self) -> ComposeResult:
        yield Label("Hello, world.")

MyGame().run()
```

## Stack

- Python 3.14+
- [Textual](https://github.com/Textualize/textual) — TUI framework
- [pygame-ce](https://github.com/pygame-community/pygame-ce) — audio
