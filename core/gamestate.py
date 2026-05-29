# core/game_state.py

import dataclasses
import json
from pathlib import Path
from typing import ClassVar, Self

__all__ = ["GameState"]


@dataclasses.dataclass
class GameState:
    save_path: ClassVar[Path] = Path("saves/save.json")

    def save(self) -> None:
        path = type(self).save_path
        path.parent.mkdir(parents=True, exist_ok=True)
        data = dataclasses.asdict(self)
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls) -> Self:
        path = cls.save_path
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(**data)
        except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"[game_state] failed to load from '{path}': {e}")
            return cls()

    def reset(self) -> None:
        for field in dataclasses.fields(self):
            if field.default is not dataclasses.MISSING:
                setattr(self, field.name, field.default)
            elif field.default_factory is not dataclasses.MISSING:
                setattr(self, field.name, field.default_factory())

    def exists(self) -> bool:
        return type(self).save_path.is_file()
