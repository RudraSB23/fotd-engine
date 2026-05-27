from textual.screen import Screen

from ui.screens.logo import LogoScreen
from ui.screens.test import TestScreen

_screens: dict[str, type[Screen]] = {
    "LogoScreen": LogoScreen,
    "TestScreen": TestScreen,
}

__all__ = [
    "LogoScreen",
    "TestScreen",
]
