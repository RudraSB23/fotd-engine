from textual.screen import Screen

from ui.screens.logo_screen import LogoScreen
from ui.screens.test_screen import TestScreen

_screens: dict[str, type[Screen]] = {
    "LogoScreen": LogoScreen,
    "TestScreen": TestScreen,
}

__all__ = [
    "LogoScreen",
    "TestScreen",
]
