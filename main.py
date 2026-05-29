from core import Game, load_styles
from core.audio import init_audio
from ui.messages import LogoFinished
from ui.screens import LogoScreen, TestScreen


class Main(Game):
    CSS_PATH = load_styles()

    def on_mount(self) -> None:
        init_audio()
        self.push_scene(LogoScreen())

    def on_logo_finished(self, _message: LogoFinished) -> None:
        self.push_scene(TestScreen())


if __name__ == "__main__":
    app = Main()
    app.run()
