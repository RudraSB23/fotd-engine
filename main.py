from core import Game, load_styles
from core.audio import init_audio
from ui.messages import LogoFinished
from ui.screens import LogoScreen, OnboardingScreen


class Main(Game):
    CSS_PATH = load_styles()

    def on_mount(self) -> None:
        super().on_mount()  # ← starts the tick timer
        init_audio()
        self.push_scene(LogoScreen())

    def on_logo_finished(self, _message: LogoFinished) -> None:
        self.push_scene(OnboardingScreen())


if __name__ == "__main__":
    app = Main()
    app.run()
