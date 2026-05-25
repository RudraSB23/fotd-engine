from core import load_styles
from ui.messages import LogoFinished
from ui.screens import LogoScreen
from textual.app import App


class Main(App):

    CSS_PATHS = load_styles()

    def __init__(self, dev_game: str | None = None) -> None:
        super().__init__()
        self._dev_game = dev_game

    def on_mount(self) -> None:
        self.push_screen(LogoScreen())

    def on_logo_finished(self, _message: LogoFinished) -> None:
        pass


if __name__ == "__main__":
    app = Main()
    app.run()