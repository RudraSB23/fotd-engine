from core import load_styles
from ui.messages import LogoFinished
from ui.screens import LogoScreen
from textual.app import App
from time import sleep


class Main(App):

    CSS_PATH = load_styles()

    def __init__(self) -> None:
        super().__init__()

    def on_mount(self) -> None:
        self.push_screen(LogoScreen())

    def on_logo_finished(self, _message: LogoFinished) -> None:
        pass


if __name__ == "__main__":
    app = Main()
    app.run()