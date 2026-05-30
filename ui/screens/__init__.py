from core.scene import Scene
from ui.screens.logo import LogoScreen
from ui.screens.onboarding import OnboardingScreen

_screens: dict[str, type[Scene]] = {
    "LogoScreen": LogoScreen,
    "OnboardingScreen": OnboardingScreen,
}

__all__ = [
    "LogoScreen",
    "OnboardingScreen",
]
