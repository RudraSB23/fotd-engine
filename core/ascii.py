# core/ascii.py

from pathlib import Path

ASSETS_DIR = Path("assets/ascii")


def load_ascii(filename: str) -> str:
    path = ASSETS_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


ASCII_SNIPPETS = {"engine_logo": load_ascii("logo.txt")}


def load_ascii_snippet(name: str) -> str:
    """Return a small ASCII snippet by name."""
    return ASCII_SNIPPETS.get(name, "")
