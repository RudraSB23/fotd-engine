# ui/messages.py
from textual.message import Message


class LogoFinished(Message):
    """Posted by LogoScreen when the logo animation completes."""


# --- Audio ---
class BGMRequested(Message):
    """Request a BGM track change from anywhere in the UI."""

    def __init__(self, filename: str, fade_ms: int = 1000) -> None:
        super().__init__()
        self.filename = filename
        self.fade_ms = fade_ms


class BGMStopped(Message):
    """Posted when BGM is stopped/faded out."""


# --- Scene/Screen transitions ---
class SceneTransition(Message):
    """Request a screen push/swap from a child widget."""

    def __init__(self, scene_id: str) -> None:
        super().__init__()
        self.scene_id = scene_id


class ScreenPopped(Message):
    """Posted when a screen is done and pops itself."""


# --- Game state ---
class GameStarted(Message):
    """Posted when the player starts a new game."""


class GameOver(Message):
    """Posted when the player dies / game ends."""

    def __init__(self, reason: str = "") -> None:
        super().__init__()
        self.reason = reason


class SceneChanged(Message):
    """Posted after a successful scene transition via the SceneManager."""

    def __init__(self, scene_id: str) -> None:
        super().__init__()
        self.scene_id = scene_id


class SceneBack(Message):
    """Posted after the SceneManager pops a screen via back()."""
