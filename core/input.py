# core/input.py

from typing import Optional

__all__ = [
    "InputManager",
    "init_input_manager",
    "get_input_manager",
]

_manager: Optional["InputManager"] = None

_DEFAULT_BINDINGS: dict[str, list[str]] = {
    "confirm": ["enter"],
    "cancel": ["escape"],
    "move_up": ["up", "k"],
    "move_down": ["down", "j"],
    "move_left": ["left", "h"],
    "move_right": ["right", "l"],
}


def init_input_manager() -> "InputManager":
    global _manager
    if _manager is not None:
        return _manager
    _manager = InputManager()
    _manager.load_defaults()
    return _manager


def get_input_manager() -> Optional["InputManager"]:
    return _manager


class InputManager:

    def __init__(self) -> None:
        self._bindings: dict[str, list[str]] = {}
        self._key_map: dict[str, str] = {}

    def _rebuild_key_map(self) -> None:
        self._key_map.clear()
        for action, keys in self._bindings.items():
            for key in keys:
                self._key_map[key] = action

    def bind(self, action: str, *keys: str) -> None:
        self._bindings[action] = list(keys)
        self._rebuild_key_map()

    def unbind(self, action: str) -> None:
        if action not in self._bindings:
            print(f"[input] unbind: unknown action '{action}'")
            return
        del self._bindings[action]
        self._rebuild_key_map()

    def get_keys(self, action: str) -> list[str]:
        return list(self._bindings.get(action, []))

    def get_action(self, key: str) -> Optional[str]:
        return self._key_map.get(key)

    def is_bound(self, action: str) -> bool:
        return action in self._bindings and len(self._bindings[action]) > 0

    def load_defaults(self) -> None:
        for action, keys in _DEFAULT_BINDINGS.items():
            self._bindings[action] = list(keys)
        self._rebuild_key_map()

    def to_textual_bindings(self, action: str) -> list[tuple[str, str, str]]:
        keys = self._bindings.get(action)
        if keys is None:
            print(f"[input] to_textual_bindings: unknown action '{action}'")
            return []
        return [(key, action, action.replace("_", " ").title()) for key in keys]