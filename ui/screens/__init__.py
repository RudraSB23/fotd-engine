from core.scene import Scene

from ui.screens.logo import LogoScreen
from ui.screens.test import TestScreen

_screens: dict[str, type[Scene]] = {
    "LogoScreen": LogoScreen,
    "TestScreen": TestScreen,
}

__all__ = [
    "LogoScreen",
    "TestScreen",
]
