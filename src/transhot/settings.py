import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SETTINGS_DIR = Path.cwd() / "config"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"


@dataclass(frozen=True)
class AppSettings:
    openai_api_key: str = ""


class SettingsStore:
    def __init__(self, settings_path: Path = SETTINGS_PATH) -> None:
        self._settings_path = settings_path

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    def ensure_exists(self) -> None:
        if self._settings_path.exists():
            return

        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.save(AppSettings())

    def load(self) -> AppSettings:
        self.ensure_exists()
        with self._settings_path.open("r", encoding="utf-8") as file:
            data: dict[str, Any] = json.load(file)
        return AppSettings(openai_api_key=str(data.get("openai_api_key", "")))

    def save(self, settings: AppSettings) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"openai_api_key": settings.openai_api_key}
        with self._settings_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
            file.write("\n")


def get_openai_api_key() -> str:
    return SettingsStore().load().openai_api_key.strip()
