from textual.message import Message
from textual.screen import Screen


__all__ = ["Scene", "Tick"]


class Tick(Message):
    def __init__(self, dt: float) -> None:
        super().__init__()
        self.dt = dt


class Scene(Screen):
    pass