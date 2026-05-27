# core/state.py

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

__all__ = [
    "GameState",
    "StateManager",
    "init_state_manager",
    "get_state_manager",
]

_ROOT = Path(__file__).parent.parent
SAVES_DIR = _ROOT / "saves"

_manager: Optional["StateManager"] = None


@dataclass
class GameState:
    player_name: str = ""
    hp: int = 100
    max_hp: int = 100
    flags: dict[str, bool] = field(default_factory=dict)
    inventory: list[str] = field(default_factory=list)
    current_scene: str = ""
    playtime_seconds: float = 0.0


def init_state_manager() -> "StateManager":
    global _manager
    if _manager is not None:
        return _manager
    _manager = StateManager()
    _manager.reset()
    return _manager


def get_state_manager() -> Optional["StateManager"]:
    return _manager


class StateManager:
    def __init__(self) -> None:
        self._state = GameState()

    def get(self) -> GameState:
        return self._state

    def reset(self) -> None:
        self._state = GameState()

    def set_flag(self, flag: str, value: bool = True) -> None:
        self._state.flags[flag] = value

    def has_flag(self, flag: str) -> bool:
        return self._state.flags.get(flag, False)

    def add_item(self, item: str) -> None:
        self._state.inventory.append(item)

    def remove_item(self, item: str) -> None:
        if item in self._state.inventory:
            self._state.inventory.remove(item)
        else:
            print(f"[state] remove_item: '{item}' not in inventory")

    def has_item(self, item: str) -> bool:
        return item in self._state.inventory

    def save(self, slot: int = 0) -> None:
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        path = SAVES_DIR / f"slot_{slot}.json"
        data = asdict(self._state)
        with open(str(path), "w") as f:
            json.dump(data, f)

    def load(self, slot: int = 0) -> bool:
        path = SAVES_DIR / f"slot_{slot}.json"
        if not path.exists():
            print(f"[state] load: slot {slot} not found")
            return False
        try:
            with open(str(path), "r") as f:
                data = json.load(f)
            self._state = GameState(
                player_name=data.get("player_name", ""),
                hp=data.get("hp", 100),
                max_hp=data.get("max_hp", 100),
                flags=data.get("flags", {}),
                inventory=data.get("inventory", []),
                current_scene=data.get("current_scene", ""),
                playtime_seconds=data.get("playtime_seconds", 0.0),
            )
            return True
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"[state] load: corrupt save in slot {slot} — {e}")
            return False

    def list_saves(self) -> list[int]:
        if not SAVES_DIR.exists():
            return []
        slots: list[int] = []
        for p in SAVES_DIR.iterdir():
            if p.suffix == ".json" and p.stem.startswith("slot_"):
                try:
                    slots.append(int(p.stem.split("_")[1]))
                except IndexError, ValueError:
                    pass
        return sorted(slots)
